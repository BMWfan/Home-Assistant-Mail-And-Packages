"""17track.net API client for shipment status lookups."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.17track.net/track/v2.2"

_BATCH_LIMIT = 40
"""Max tracking numbers per API request (17track rejects larger batches
with code -18010014 -- observed live with a 186-number request)."""

# 17track signals a bad/expired API key with HTTP 401/403 or one of these
# top-level business codes. Anything here means the key must be fixed, so the
# coordinator raises a repair issue rather than retrying forever.
_AUTH_ERROR_STATUS = (401, 403)
_AUTH_ERROR_CODES = {-18010011, -18010012, -18010013}

# v2.2 returns latest_status.status as a string; map it onto the numeric
# codes the rest of this integration keys on (see universal._STATUS_TO_SUFFIX).
_V2_STATUS_TO_CODE: dict[str, int] = {
    "NotFound": 0,
    "InfoReceived": 10,
    "InTransit": 10,
    "AvailableForPickup": 10,
    "OutForDelivery": 10,
    "Expired": 20,
    "DeliveryFailure": 35,
    "Delivered": 40,
    "Exception": 50,
}

# 17track's own resolved-carrier numeric ids (from track_info.tracking.
# providers[0].provider.key), mapped to this integration's internal carrier
# names -- only the ids we've verified live so far via
# https://res.17track.net/asset/carrier/info/apicarrier.all.json. Extend as
# more carrier-resolution mismatches turn up; an unmapped id is left as
# None so the caller falls back to its own text-based classification.
_RESOLVED_CARRIER_NAMES: dict[int, str] = {
    100007: "dpd",
    100031: "evri",  # "Hermes (DE)" in 17track's carrier list
}


class SeventeenTrackClient:
    """Async client for the 17track.net shipment tracking API."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        """Initialize with a Home Assistant instance and API key."""
        self._hass = hass
        self._headers = {
            "17token": api_key,
            "Content-Type": "application/json",
        }
        self.auth_failed = False

    async def register(
        self,
        tracking_numbers: list[str],
        carrier_hints: dict[str, int] | None = None,
    ) -> None:
        """Register tracking numbers with 17track before the first status query.

        17track is idempotent: re-registering an already-known number is safe.
        Only net-new registrations count against the monthly quota.

        `carrier_hints` (number -> 17track numeric carrier id, from
        https://res.17track.net/asset/carrier/info/apicarrier.all.json)
        lets a caller force which courier 17track validates a number
        against when auto-detection can't tell -- e.g. bare 14-digit
        numbers are ambiguous between DPD (DE, id 100007) and Hermes (DE,
        id 100031); live-verified 2026-07-18 that 17track's unhinted
        auto-detect rejects a real Hermes number of that format outright.
        """
        if not tracking_numbers:
            return
        carrier_hints = carrier_hints or {}
        session = async_get_clientsession(self._hass)
        for i in range(0, len(tracking_numbers), _BATCH_LIMIT):
            chunk = tracking_numbers[i : i + _BATCH_LIMIT]
            payload = [
                {"number": n, **({"carrier": carrier_hints[n]} if n in carrier_hints else {})}
                for n in chunk
            ]
            try:
                async with session.post(
                    f"{_API_BASE}/register",
                    json=payload,
                    headers=self._headers,
                ) as resp:
                    if resp.status in _AUTH_ERROR_STATUS:
                        self.auth_failed = True
                        return
                    resp.raise_for_status()
                    if (await resp.json()).get("code") in _AUTH_ERROR_CODES:
                        self.auth_failed = True
                        return
                _LOGGER.debug("17track: registered %d tracking number(s)", len(chunk))
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("17track register failed: %s", err)

    async def get_status_batch(  # noqa: C901
        self,
        tracking_numbers: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Return status dicts keyed by tracking number.

        Newly registered numbers may return status_code=0 ("Unknown") until
        17track has fetched the carrier data, which usually takes one scan cycle.
        """
        if not tracking_numbers:
            return {}
        session = async_get_clientsession(self._hass)
        results: dict[str, dict[str, Any]] = {}

        for i in range(0, len(tracking_numbers), _BATCH_LIMIT):
            chunk = tracking_numbers[i : i + _BATCH_LIMIT]
            payload = [{"number": n} for n in chunk]
            try:
                async with session.post(
                    f"{_API_BASE}/gettrackinfo",
                    json=payload,
                    headers=self._headers,
                ) as resp:
                    if resp.status in _AUTH_ERROR_STATUS:
                        self.auth_failed = True
                        return results
                    resp.raise_for_status()
                    data = await resp.json()
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("17track gettrackinfo failed: %s", err)
                continue

            if data.get("code") in _AUTH_ERROR_CODES:
                self.auth_failed = True
                return results
            if data.get("code") != 0:
                _LOGGER.error("17track API error: code=%s", data.get("code"))
                continue

            for item in data.get("data", {}).get("accepted", []):
                number = item.get("number", "")
                if not number:
                    continue
                track_info = item.get("track_info") or {}
                status_str = (track_info.get("latest_status") or {}).get(
                    "status", ""
                ) or "Unknown"
                latest_event = track_info.get("latest_event") or {}
                # Live-verified 2026-07-18: 17track's v2 response carries an
                # official estimated-delivery timestamp under
                # time_metrics.estimated_delivery_date.to (a "by" deadline,
                # not a from/to window -- "from" was None on every live
                # shipment observed). Surface it so the card can show an
                # actual delivery time instead of just a relative "X ago".
                eta = ((track_info.get("time_metrics") or {}).get(
                    "estimated_delivery_date"
                ) or {}).get("to")
                # Live-verified 2026-07-18: track_info.tracking.providers[0]
                # .provider carries 17track's OWN resolved carrier (numeric
                # "key" + "name") -- ground truth, independent of whichever
                # carrier we guessed from email text or hinted at register()
                # time. Prefer this over our own regex-based classification
                # whenever it maps to a carrier we know (see
                # _RESOLVED_CARRIER_NAMES) -- our text classification can be
                # wrong (bare 14-digit DPD/Hermes-DE collision, no brand
                # name in the email at all), 17track's own carrier database
                # match is authoritative.
                providers = (track_info.get("tracking") or {}).get("providers") or []
                provider_key = (
                    (providers[0].get("provider") or {}).get("key")
                    if providers
                    else None
                )
                _LOGGER.debug(
                    "17track raw providers for %s: %s", number, providers
                )
                # Full event history (for a per-shipment timeline UI) lives
                # alongside latest_event on the resolved provider -- same
                # per-event shape (description/location/time_iso) as
                # latest_event itself.
                raw_events = (providers[0].get("events") if providers else None) or []
                history = [
                    {
                        "time": e.get("time_iso", ""),
                        "description": e.get("description", ""),
                        "location": e.get("location") or "",
                    }
                    for e in raw_events
                ]
                results[number] = {
                    "status": status_str,
                    "status_code": _V2_STATUS_TO_CODE.get(status_str, 0),
                    "last_event": latest_event.get("description", ""),
                    "last_location": latest_event.get("location") or "",
                    "last_update": latest_event.get("time_iso", ""),
                    "estimated_delivery": eta or "",
                    "resolved_carrier": _RESOLVED_CARRIER_NAMES.get(provider_key),
                    "history": history,
                }

            for item in data.get("data", {}).get("rejected", []):
                number = item.get("number", "")
                if number:
                    results[number] = {"status": "Unknown", "status_code": -1}

        return results
