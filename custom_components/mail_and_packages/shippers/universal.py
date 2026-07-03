"""Universal email tracking number scanner."""

from __future__ import annotations

import email
import logging
import re
from typing import Any

from aioimaplib import IMAP4_SSL

from custom_components.mail_and_packages.const import (
    ATTR_COUNT,
    ATTR_TRACKING,
    CONF_17TRACK_API_KEY,
)
from custom_components.mail_and_packages.tracking.seventeen_track import (
    SeventeenTrackClient,
)
from custom_components.mail_and_packages.utils.cache import EmailCache
from custom_components.mail_and_packages.utils.imap import (
    email_fetch_batch,
    email_search_since,
)

from .base import Shipper

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPE = "universal_packages"

FETCH_BATCH_SIZE = 25
"""Messages per batched FETCH round-trip during the universal scan.

Full RFC822 bodies can be large (HTML marketing mail), so this stays
moderate -- the point is cutting per-message round-trips, not maximizing
batch size.
"""

# Patterns ordered from most specific to least specific.
# Tuples: (carrier_name, pattern, requires_context_keyword)
# requires_context=True means the match is only accepted if a delivery-related
# keyword appears within 200 characters to reduce false positives.
ORDERED_PATTERNS: list[tuple[str, str, bool]] = [
    ("ups", r"\b1Z[0-9A-Z]{16}\b", False),
    ("usps", r"\b9[2345]\d{15,26}\b", False),
    ("royal_mail", r"\b[A-Za-z]{2}[0-9]{9}GB\b", False),
    ("auspost", r"\b[A-Za-z]{2}[0-9]{9}AU\b", False),
    ("intelcom", r"\b(?:NSPRSO[0-9]{10}|AMZNL[0-9]{12})\b", False),
    ("bonshaw", r"\bBNI[0-9]{9}\b", False),
    ("post_nl", r"\b3S[A-Z0-9]{10,18}\b", False),
    # DHL Germany parcel numbers are GS1-based and start with 00 3404
    # (observed live: real DHL shipments were being mislabeled "fedex" via
    # the generic 20-digit pattern below, which is checked later).
    ("dhl", r"\b003404[0-9]{14}\b", True),
    # Unlike the other direct-format patterns above, "H" + 15 alphanumeric
    # chars has no distinguishing structure of its own -- it can match any
    # base64-ish fragment (tracking pixels, encoded URL params, hashes) in
    # HTML mail. Require the same delivery-keyword context the bare-digit
    # patterns below use, or this matches far too often.
    ("evri", r"\bH[0-9A-Z]{15}\b", True),
    ("post_at", r"\b[0-9]{22}\b", True),
    ("dpd", r"\b[0-9]{14}\b", True),
    ("fedex", r"\b(?:[0-9]{12}|[0-9]{15}|[0-9]{20})\b", True),
    ("gls", r"\b[0-9]{11,12}\b", True),
]

# \bnummer\b / \bnuméro\b are anchored: as bare substrings they'd match
# inside any "Kundennummer"/"Bestellnummer"/"numéro de commande" -- i.e.
# an order or customer reference, not a delivery context -- in almost
# every German/French commerce email, defeating the context check
# entirely for the bare-digit patterns (dpd/gls/fedex/post_at/evri) above.
_CONTEXT_RE = re.compile(
    r"tracking|sendungsnummer|paketnummer|parcel.?number|waybill|"
    r"shipment|delivery|package|\bnummer\b|colis|paket|envoi|livraison|"
    r"\bnuméro\b|lieferung|verfolgung|seguimiento|colissimo",
    re.IGNORECASE,
)

_CONTEXT_WINDOW = 200

# Carriers whose bare-digit pattern is too generic for the shared delivery-
# keyword context alone to be distinctive (an 11-12 digit number next to any
# "paket"/"delivery" mention is common in nearly any commerce email, not
# just this carrier's). These also require the carrier's own brand name
# nearby. Live report: 43+ "GLS delivering" packages from ordinary shop
# mail that only generically mentioned a package, never GLS specifically.
_BRAND_CONTEXT_RE: dict[str, re.Pattern[str]] = {
    "gls": re.compile(r"\bgls\b", re.IGNORECASE),
    # FedEx numbers are bare 12/15/20-digit runs -- indistinguishable from any
    # long order/invoice/reference number in commerce mail. A generic delivery
    # keyword nearby is not enough (live false positive: "869999999999997",
    # a near-all-nines number 17track returns NotFound for). Real FedEx mail
    # always names "FedEx", so require the brand near the number.
    "fedex": re.compile(r"\bfedex\b", re.IGNORECASE),
    # DPD parcel numbers are bare 14-digit runs -- same problem. Live false
    # positive: "58303696535936" from a BANDWERK marketing newsletter (a
    # campaign/pixel ID in the HTML, 17track NotFound). Real DPD mail names
    # "DPD" or links to a dpd.de tracking URL near the number (the raw HTML,
    # incl. link hrefs, is what we scan), so require the brand nearby.
    "dpd": re.compile(r"\bdpd\b", re.IGNORECASE),
}

# Maps the carrier name from ORDERED_PATTERNS to the sensor prefix used by
# existing carrier sensors (e.g. "ups" → ups_delivering / ups_delivered).
# None = no dedicated sensor exists; number stays in universal_packages only.
_CARRIER_TO_SENSOR_PREFIX: dict[str, str | None] = {
    "ups": "ups",
    "usps": "usps",
    "fedex": "fedex",
    "gls": "gls",
    "dhl": "dhl",
    # DPD has multiple regional variants (de/fr/uk/nl/pl) – can't tell from
    # number format alone, so we leave it in the universal count.
    "dpd": None,
    # No dedicated sensors for these carriers:
    "royal_mail": None,
    "auspost": None,
    "intelcom": None,
    "bonshaw": None,
    "post_nl": None,
    "post_at": None,
    "evri": None,  # sensor prefix is "hermes" in existing sensors
}

# Maps 17track event codes to the _tracking_details suffix used by
# _apply_tracking_state in the coordinator.
_STATUS_TO_SUFFIX: dict[int, str] = {
    10: "_delivering",  # In Transit
    30: "_exception",  # Delivery Alert
    35: "_exception",  # Undelivered
    40: "_delivered",  # Delivered
    50: "_exception",  # Alert
    # 0 = Unknown (new package, pending first 17track fetch) → treat as delivering
}


class UniversalTrackingShipper(Shipper):
    """Scan all recent emails for tracking numbers regardless of sender."""

    @property
    def name(self) -> str:
        """Return the internal name of the shipper."""
        return "universal"

    @classmethod
    def handles_sensor(cls, sensor_type: str) -> bool:
        """Return True only for the universal_packages sensor."""
        return sensor_type == SENSOR_TYPE

    async def process(
        self,
        account: IMAP4_SSL,
        date: str,
        sensor_type: str,
        cache: EmailCache | None = None,
        since_date: str | None = None,
    ) -> dict[str, Any]:
        """Scan all emails since since_date for tracking numbers."""
        search_date = since_date or date

        _LOGGER.debug("Universal scan: searching all emails since %s", search_date)

        try:
            email_ids = await email_search_since(account, search_date)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Universal tracking scan search failed: %s", err)
            return {ATTR_COUNT: 0, ATTR_TRACKING: []}

        if not email_ids:
            _LOGGER.debug("Universal scan: no emails found")
            return {ATTR_COUNT: 0, ATTR_TRACKING: []}

        _LOGGER.debug("Universal scan: scanning %d emails", len(email_ids))

        # Maps tracking_number -> carrier_name; insertion order = discovery order
        found: dict[str, str] = {}

        # Batched download: fetching each email individually costs one IMAP
        # round-trip per message, which blows the scan time budget on wider
        # day windows (observed live: 215 messages over a 10-day window was
        # enough to exceed it on its own). email_fetch_batch downloads a
        # whole chunk per round-trip; the response mixes FETCH boundary
        # lines with the message literals, but boundary lines parse as
        # header-less empty messages and extract nothing, so feeding every
        # bytes part through the same extraction loop is safe.
        for i in range(0, len(email_ids), FETCH_BATCH_SIZE):
            chunk = email_ids[i : i + FETCH_BATCH_SIZE]
            try:
                if cache:
                    data = (await cache.fetch_batch(chunk))[1]
                else:
                    data = (await email_fetch_batch(account, chunk))[1]
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Error batch-fetching emails %s: %s", chunk, err)
                continue
            for part in data:
                if not isinstance(part, (bytes, bytearray)):
                    continue
                try:
                    msg = email.message_from_bytes(part)
                    text = self._extract_text(msg)
                    subject = str(msg.get("subject") or "")
                    _extract_tracking_numbers(subject + "\n" + text, found)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Error scanning email part: %s", err)

        tracking_list = list(found.keys())
        _LOGGER.debug(
            "Universal scan found %d tracking number(s): %s",
            len(tracking_list),
            tracking_list,
        )

        tracking_details = await self._enrich_with_17track(tracking_list, found)
        return {
            ATTR_COUNT: len(tracking_list),
            ATTR_TRACKING: tracking_list,
            "tracking_details": tracking_details,
        }

    async def process_batch(
        self,
        account: IMAP4_SSL,
        date: str,
        sensors: list[str],
        cache: EmailCache,
        since_date: str | None = None,
    ) -> dict[str, Any]:
        """Process batch – delegates to process() and routes results into carrier sensors."""
        result = await self.process(account, date, SENSOR_TYPE, cache, since_date)
        tracking_details: list[dict[str, Any]] = result.pop("tracking_details", [])

        # 17track rejected these numbers outright (status_code -1): not a valid
        # tracking number for ANY carrier. Drop them entirely -- no routing, no
        # list, no count. This is the definitive false-positive filter (caught
        # the BANDWERK marketing-mail phantom "58303696535936"). NotFound (0,
        # accepted-but-no-data-yet) is intentionally kept so a freshly shipped
        # parcel still shows before 17track has fetched its first event.
        # (Absent status_code -> no 17track key configured -> keep as-is.)
        tracking_details = [
            item for item in tracking_details if item.get("status_code") != -1
        ]

        # Build _tracking_details so the coordinator's _apply_tracking_state
        # feeds found numbers directly into existing carrier sensors (ups_delivering
        # etc.) with full F2 persistence and deduplication.
        coordinator_tracking: dict[str, list[str]] = {}
        for item in tracking_details:
            prefix = _CARRIER_TO_SENSOR_PREFIX.get(item["carrier"])
            if prefix is None:
                continue
            suffix = _STATUS_TO_SUFFIX.get(item.get("status_code", 0), "_delivering")
            key = f"{prefix}{suffix}"
            coordinator_tracking.setdefault(key, []).append(item["number"])

        # Delivered shipments (17track status 40) are still routed above so the
        # coordinator clears them from its in-transit state, but they drop out of
        # the universal count/list immediately instead of lingering until their
        # source email ages out of the scan window.
        active_details = [
            item for item in tracking_details if item.get("status_code") != 40
        ]
        result[SENSOR_TYPE] = len(active_details)
        result["universal_tracking_details"] = active_details
        if coordinator_tracking:
            result["_tracking_details"] = coordinator_tracking
            # When 17track is the status source, publish under a separate key so
            # the coordinator can use it exclusively and ignore email-based status.
            if self.config.get(CONF_17TRACK_API_KEY):
                result["_17track_details"] = coordinator_tracking
        result["_17track_auth_failed"] = getattr(
            self, "_seventeen_auth_failed", False
        )
        return result

    async def _enrich_with_17track(
        self,
        tracking_list: list[str],
        found: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Query 17track for status if configured; always returns a details list."""
        base_details = [{"number": n, "carrier": found[n]} for n in tracking_list]
        api_key = self.config.get(CONF_17TRACK_API_KEY, "")
        if not api_key or not tracking_list:
            return base_details

        client = SeventeenTrackClient(self.hass, api_key)
        await client.register(tracking_list)
        status_map = await client.get_status_batch(tracking_list)
        # Surfaced to the coordinator (via process_batch) so a bad/expired
        # 17track API key becomes a repair issue.
        self._seventeen_auth_failed = client.auth_failed

        enriched = []
        for item in base_details:
            detail = dict(item)
            detail.update(status_map.get(item["number"], {}))
            enriched.append(detail)
        return enriched

    @staticmethod
    def _extract_text(msg: email.message.Message) -> str:
        """Return all text/plain and text/html body parts joined."""
        parts: list[str] = []
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode("utf-8", "ignore"))
        return "\n".join(parts)


def _extract_tracking_numbers(text: str, found: dict[str, str]) -> None:
    """Apply ORDERED_PATTERNS to text and populate found dict."""
    claimed: set[str] = set()  # numbers already assigned in this email

    for carrier, pattern, requires_context in ORDERED_PATTERNS:
        for match in re.finditer(pattern, text):
            num = match.group(0)
            if num in found or num in claimed:
                continue
            if requires_context and not _has_context(text, match.start()):
                continue
            brand_re = _BRAND_CONTEXT_RE.get(carrier)
            if brand_re and not _has_context(text, match.start(), pattern=brand_re):
                continue
            found[num] = carrier
            claimed.add(num)


def _has_context(text: str, pos: int, pattern: re.Pattern[str] | None = None) -> bool:
    """Return True if `pattern` (default: any delivery keyword) is nearby."""
    start = max(0, pos - _CONTEXT_WINDOW)
    end = min(len(text), pos + _CONTEXT_WINDOW)
    window = text[start:end]
    return bool((pattern or _CONTEXT_RE).search(window))
