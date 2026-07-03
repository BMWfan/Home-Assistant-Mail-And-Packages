"""Event platform for Mail and Packages.

Fires a Home Assistant event entity when the delivered / in-transit package
totals increase, so automations can react to "a package was delivered" or "a
new package is on the way" without polling sensor deltas themselves.
"""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MailAndPackagesConfigEntry
from .const import DOMAIN, VERSION

EVENT_DELIVERED = "package_delivered"
EVENT_IN_TRANSIT = "new_package_in_transit"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MailAndPackagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the delivery event entity."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([MailDeliveryEvent(entry, coordinator)])


class MailDeliveryEvent(CoordinatorEntity, EventEntity):
    """Fires when the delivered / in-transit package totals go up."""

    _attr_icon = "mdi:package-variant-closed-check"
    _attr_event_types = [EVENT_DELIVERED, EVENT_IN_TRANSIT]

    def __init__(self, config: MailAndPackagesConfigEntry, coordinator) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator)
        self._host = config.data[CONF_HOST]
        self._entry_id = config.entry_id
        self._attr_name = f"{self._host} Delivery Event"
        self._attr_unique_id = f"event_{self._host}_delivery_{self._entry_id}"
        self._prev_delivered: int | None = None
        self._prev_transit: int | None = None

    @property
    def device_info(self) -> dict:
        """Return device information about the mailbox."""
        return {
            "connections": {(DOMAIN, self._entry_id)},
            "name": self._host,
            "manufacturer": "IMAP E-Mail",
            "sw_version": VERSION,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Compare against the previous scan and fire on increases."""
        data = self.coordinator.data or {}
        delivered = data.get("zpackages_delivered")
        transit = data.get("zpackages_transit")

        # Only fire once we have a baseline (avoids a spurious event on the very
        # first scan / after a restart).
        if (
            isinstance(delivered, int)
            and isinstance(self._prev_delivered, int)
            and delivered > self._prev_delivered
        ):
            self._trigger_event(
                EVENT_DELIVERED,
                {"total": delivered, "new": delivered - self._prev_delivered},
            )
        if (
            isinstance(transit, int)
            and isinstance(self._prev_transit, int)
            and transit > self._prev_transit
        ):
            self._trigger_event(
                EVENT_IN_TRANSIT,
                {"total": transit, "new": transit - self._prev_transit},
            )

        if isinstance(delivered, int):
            self._prev_delivered = delivered
        if isinstance(transit, int):
            self._prev_transit = transit

        super()._handle_coordinator_update()
