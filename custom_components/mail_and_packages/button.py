"""Button platform for Mail and Packages -- trigger an immediate scan."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MailAndPackagesConfigEntry
from .const import DOMAIN, VERSION


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MailAndPackagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the scan-now button."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([MailScanNowButton(entry, coordinator)])


class MailScanNowButton(CoordinatorEntity, ButtonEntity):
    """A button that triggers an immediate mailbox scan."""

    _attr_icon = "mdi:email-sync-outline"

    def __init__(self, config: MailAndPackagesConfigEntry, coordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._host = config.data[CONF_HOST]
        self._entry_id = config.entry_id
        self._attr_name = f"{self._host} Scan Now"
        self._attr_unique_id = f"button_{self._host}_scan_now_{self._entry_id}"

    @property
    def device_info(self) -> dict:
        """Return device information about the mailbox."""
        return {
            "connections": {(DOMAIN, self._entry_id)},
            "name": self._host,
            "manufacturer": "IMAP E-Mail",
            "sw_version": VERSION,
        }

    async def async_press(self) -> None:
        """Trigger an immediate coordinator refresh (mailbox scan)."""
        await self.coordinator.async_request_refresh()
