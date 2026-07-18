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

    async def register(self, tracking_numbers: list[str]) -> None:
        """Register tracking numbers with 17track before the first status query.

        17track is idempotent: re-registering an already-known number is safe.
        Only net-new registrations count against the monthly quota.
        """
        if not tracking_numbers:
            return
        session = async_get_clientsession(self._hass)
        for i in range(0, len(tracking_numbers), _BATCH_LIMIT):
            chunk = tracking_numbers[i : i + _BATCH_LIMIT]
            payload = [{"number": n} for n in chunk]
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
                # TEMP diagnostic: check if 17track exposes an estimated
                # delivery time window we're currently not surfacing.
                _LOGGER.debug(
                    "17track track_info keys for %s: %s | time_metrics=%r | "
                    "milestone=%r",
                    number,
                    list(track_info.keys()),
                    track_info.get("time_metrics"),
                    track_info.get("milestone"),
                )
                results[number] = {
                    "status": status_str,
                    "status_code": _V2_STATUS_TO_CODE.get(status_str, 0),
                    "last_event": latest_event.get("description", ""),
                    "last_location": latest_event.get("location") or "",
                    "last_update": latest_event.get("time_iso", ""),
                }

            for item in data.get("data", {}).get("rejected", []):
                number = item.get("number", "")
                if number:
                    results[number] = {"status": "Unknown", "status_code": -1}

        return results
