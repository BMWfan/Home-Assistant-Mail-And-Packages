"""Persistent package lifecycle registry for Mail and Packages."""
from __future__ import annotations

import logging
from datetime import timezone
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    PACKAGE_STATUS_CLEARED,
    PACKAGE_STATUS_DELIVERED,
    PACKAGE_STATUS_DETECTED,
    PACKAGE_STATUS_IN_TRANSIT,
    PACKAGE_STATUS_TRANSITIONS,
    SHIPPERS,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PackageRegistry:
    """Tracks packages across HA restarts using HA's persistent storage.

    Storage key: mail_and_packages.<entry_id>.packages
    Data format: {tracking_number: {tracking_number, carrier, status,
                                     first_seen, last_updated}}
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.packages",
        )
        self._packages: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    async def async_load(self) -> None:
        """Load persisted data from storage."""
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._packages = stored
        _LOGGER.debug("Package registry loaded: %d packages", len(self._packages))

    async def async_save(self) -> None:
        """Persist current state to storage."""
        await self._store.async_save(self._packages)

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def _can_transition(self, from_status: str, to_status: str) -> bool:
        return to_status in PACKAGE_STATUS_TRANSITIONS.get(from_status, set())

    # ------------------------------------------------------------------
    # Write operations (all call async_save at the end)
    # ------------------------------------------------------------------

    async def async_add_or_update(
        self, tracking_number: str, carrier: str, new_status: str
    ) -> bool:
        """Add a new package or advance its status. Returns True if changed."""
        existing = self._packages.get(tracking_number)
        if existing is None:
            self._packages[tracking_number] = {
                "tracking_number": tracking_number,
                "carrier": carrier,
                "status": new_status,
                "first_seen": _now_iso(),
                "last_updated": _now_iso(),
            }
            _LOGGER.debug("Registry: new package %s (%s) → %s", tracking_number, carrier, new_status)
            await self.async_save()
            return True

        current_status = existing["status"]
        if current_status == new_status:
            return False
        if not self._can_transition(current_status, new_status):
            _LOGGER.debug(
                "Registry: invalid transition %s → %s for %s (ignored)",
                current_status, new_status, tracking_number,
            )
            return False

        existing["status"] = new_status
        existing["last_updated"] = _now_iso()
        _LOGGER.debug("Registry: %s %s → %s", tracking_number, current_status, new_status)
        await self.async_save()
        return True

    async def async_mark_delivered(self, tracking_number: str) -> bool:
        """Mark a specific package as delivered. Returns True if found."""
        if tracking_number not in self._packages:
            _LOGGER.warning("Registry: mark_delivered — unknown tracking number %s", tracking_number)
            return False
        return await self.async_add_or_update(
            tracking_number,
            self._packages[tracking_number]["carrier"],
            PACKAGE_STATUS_DELIVERED,
        )

    async def async_clear_package(self, tracking_number: str) -> bool:
        """Remove a package from active tracking. Returns True if found."""
        if tracking_number not in self._packages:
            return False
        del self._packages[tracking_number]
        await self.async_save()
        _LOGGER.debug("Registry: cleared %s", tracking_number)
        return True

    async def async_clear_all_delivered(self) -> int:
        """Remove all delivered packages. Returns count cleared."""
        to_clear = [
            k for k, v in self._packages.items()
            if v["status"] == PACKAGE_STATUS_DELIVERED
        ]
        for key in to_clear:
            del self._packages[key]
        if to_clear:
            await self.async_save()
        _LOGGER.debug("Registry: cleared %d delivered packages", len(to_clear))
        return len(to_clear)

    # ------------------------------------------------------------------
    # Automatic update from coordinator scan data
    # ------------------------------------------------------------------

    async def async_update_from_data(self, data: dict[str, Any]) -> None:
        """Merge a fresh email scan result into the registry.

        Logic:
        - {carrier}_tracking lists → add/keep as in_transit
        - universal_tracking_detail hits → add as detected (if new)
        - When {carrier}_delivered > 0: mark in_transit packages for that
          carrier that are NOT in the current delivering list as delivered.
        """
        changed = False

        # Collect all currently-delivering tracking numbers per carrier
        delivering_now: dict[str, set] = {}  # carrier → set of tracking numbers
        for shipper in SHIPPERS:
            key = f"{shipper}_tracking"
            numbers = data.get(key, [])
            if isinstance(numbers, list) and numbers:
                delivering_now[shipper] = set(numbers)
                for num in numbers:
                    updated = await self.async_add_or_update(num, shipper, PACKAGE_STATUS_IN_TRANSIT)
                    changed = changed or updated

        # Universal scanner hits → detected status (if not already known)
        for hit in data.get("universal_tracking_detail", []):
            num = hit.get("number")
            carrier = hit.get("carrier", "unknown")
            if num and num not in self._packages:
                updated = await self.async_add_or_update(num, carrier, PACKAGE_STATUS_DETECTED)
                changed = changed or updated

        # Auto-deliver: package was in_transit but no longer in delivering emails
        for shipper in SHIPPERS:
            delivered_count = data.get(f"{shipper}_delivered", 0)
            if not delivered_count:
                continue
            current_delivering = delivering_now.get(shipper, set())
            for num, pkg in list(self._packages.items()):
                if (
                    pkg["carrier"] == shipper
                    and pkg["status"] == PACKAGE_STATUS_IN_TRANSIT
                    and num not in current_delivering
                ):
                    updated = await self.async_add_or_update(num, shipper, PACKAGE_STATUS_DELIVERED)
                    changed = changed or updated

        if changed:
            _LOGGER.debug("Registry: updated from scan data")

    # ------------------------------------------------------------------
    # Read-only properties used by sensor entities
    # ------------------------------------------------------------------

    @property
    def active_packages(self) -> list[dict]:
        """All packages not yet cleared."""
        return [
            p for p in self._packages.values()
            if p["status"] != PACKAGE_STATUS_CLEARED
        ]

    @property
    def count_tracked(self) -> int:
        """Total active packages."""
        return len(self.active_packages)

    @property
    def count_in_transit(self) -> int:
        """Packages detected or in transit (not yet delivered/cleared)."""
        return sum(
            1 for p in self.active_packages
            if p["status"] not in {PACKAGE_STATUS_DELIVERED, PACKAGE_STATUS_CLEARED}
        )

    @property
    def count_delivered(self) -> int:
        """Packages marked as delivered (not yet cleared)."""
        return sum(
            1 for p in self.active_packages
            if p["status"] == PACKAGE_STATUS_DELIVERED
        )
