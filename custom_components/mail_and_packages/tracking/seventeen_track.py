"""17track.net API client for shipment status lookups."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.17track.net/track/v2.2"

_STATUS_MAP: dict[int, str] = {
    0: "Unknown",
    10: "In Transit",
    20: "Expired",
    30: "Delivery Alert",
    35: "Undelivered",
    40: "Delivered",
    50: "Alert",
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

    async def register(self, tracking_numbers: list[str]) -> None:
        """Register tracking numbers with 17track before the first status query.

        17track is idempotent: re-registering an already-known number is safe.
        Only net-new registrations count against the monthly quota.
        """
        if not tracking_numbers:
            return
        session = async_get_clientsession(self._hass)
        payload = [{"number": n} for n in tracking_numbers]
        try:
            async with session.post(
                f"{_API_BASE}/register",
                json=payload,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
            _LOGGER.debug(
                "17track: registered %d tracking number(s)", len(tracking_numbers)
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("17track register failed: %s", err)

    async def get_status_batch(
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
        payload = [{"number": n} for n in tracking_numbers]
        try:
            async with session.post(
                f"{_API_BASE}/gettrackinfo",
                json=payload,
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("17track gettrackinfo failed: %s", err)
            return {}

        if data.get("code") != 0:
            _LOGGER.error("17track API error: code=%s", data.get("code"))
            return {}

        results: dict[str, dict[str, Any]] = {}

        for item in data.get("data", {}).get("accepted", []):
            number = item.get("number", "")
            if not number:
                continue
            track = item.get("track") or {}
            event_code = track.get("e", 0)
            latest = track.get("z0") or {}
            results[number] = {
                "status": _STATUS_MAP.get(event_code, "Unknown"),
                "status_code": event_code,
                "last_event": latest.get("a", ""),
                "last_location": latest.get("z", ""),
                "last_update": latest.get("d", ""),
            }

        for item in data.get("data", {}).get("rejected", []):
            number = item.get("number", "")
            if number:
                results[number] = {"status": "Unknown", "status_code": -1}

        return results
