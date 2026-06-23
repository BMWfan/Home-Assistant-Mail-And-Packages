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
    email_fetch,
    email_search_since,
)

from .base import Shipper

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPE = "universal_packages"

# Patterns ordered from most specific to least specific.
# Tuples: (carrier_name, pattern, requires_context_keyword)
# requires_context=True means the match is only accepted if a delivery-related
# keyword appears within 200 characters to reduce false positives.
ORDERED_PATTERNS: list[tuple[str, str, bool]] = [
    ("ups", r"1Z[0-9A-Z]{16}", False),
    ("usps", r"9[2345]\d{15,26}", False),
    ("royal_mail", r"[A-Za-z]{2}[0-9]{9}GB", False),
    ("auspost", r"[A-Za-z]{2}[0-9]{9}AU\b", False),
    ("intelcom", r"(?:NSPRSO[0-9]{10}|AMZNL[0-9]{12})", False),
    ("bonshaw", r"BNI[0-9]{9}", False),
    ("post_nl", r"3S[A-Z0-9]{10,18}", False),
    ("evri", r"H[0-9A-Z]{15}", False),
    ("post_at", r"\b[0-9]{22}\b", True),
    ("dpd", r"\b[0-9]{14}\b", True),
    ("fedex", r"\b(?:[0-9]{12}|[0-9]{15}|[0-9]{20})\b", True),
    ("gls", r"\b[0-9]{11,12}\b", True),
]

_CONTEXT_RE = re.compile(
    r"tracking|sendungsnummer|paketnummer|parcel.?number|waybill|"
    r"shipment|delivery|package|nummer|colis|paket|envoi|livraison|"
    r"numéro|lieferung|verfolgung|seguimiento|colissimo",
    re.IGNORECASE,
)

_CONTEXT_WINDOW = 200


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

        for eid in email_ids:
            try:
                await self._scan_email(eid, account, cache, found)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Error scanning email %s: %s", eid, err)

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
        """Process batch – delegates to process() for the universal sensor."""
        result = await self.process(account, date, SENSOR_TYPE, cache, since_date)
        result[SENSOR_TYPE] = result[ATTR_COUNT]
        result["universal_tracking_details"] = result.pop("tracking_details", [])
        return result

    async def _enrich_with_17track(
        self,
        tracking_list: list[str],
        found: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Optionally query 17track for status; always returns a details list."""
        base_details = [{"number": n, "carrier": found[n]} for n in tracking_list]
        api_key = self.config.get(CONF_17TRACK_API_KEY, "")
        if not api_key or not tracking_list:
            return base_details

        client = SeventeenTrackClient(self.hass, api_key)
        await client.register(tracking_list)
        status_map = await client.get_status_batch(tracking_list)

        enriched = []
        for item in base_details:
            detail = dict(item)
            detail.update(status_map.get(item["number"], {}))
            enriched.append(detail)
        return enriched

    async def _scan_email(
        self,
        eid: bytes,
        account: IMAP4_SSL,
        cache: EmailCache | None,
        found: dict[str, str],
    ) -> None:
        """Fetch one email and extract all tracking numbers from it."""
        if cache:
            data = (await cache.fetch(eid, "(RFC822)"))[1]
        else:
            data = (await email_fetch(account, eid, "(RFC822)"))[1]

        for part in data:
            if not isinstance(part, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(part)
            text = self._extract_text(msg)
            subject = str(msg.get("subject") or "")
            full_text = subject + "\n" + text
            _extract_tracking_numbers(full_text, found)

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
            found[num] = carrier
            claimed.add(num)


def _has_context(text: str, pos: int) -> bool:
    """Return True if a delivery keyword appears within the context window."""
    start = max(0, pos - _CONTEXT_WINDOW)
    end = min(len(text), pos + _CONTEXT_WINDOW)
    return bool(_CONTEXT_RE.search(text[start:end]))
