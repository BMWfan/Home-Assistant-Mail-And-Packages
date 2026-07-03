"""Calendar platform for Mail and Packages.

Exposes expected deliveries as calendar events: DHL Briefankündigung letters on
their announced delivery date, and an all-day "Amazon packages expected" entry
for today when Amazon reports packages arriving. The calendar is empty when
there is nothing announced -- that is normal.
"""

from __future__ import annotations

import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import MailAndPackagesConfigEntry
from .const import DOMAIN, VERSION


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MailAndPackagesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the expected-deliveries calendar."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([MailDeliveryCalendar(entry, coordinator)])


def _parse_date(raw) -> datetime.date | None:
    """Parse a YYYY-MM-DD(...) string into a date, or return None."""
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(str(raw)[:10])
    except (ValueError, TypeError):
        return None


class MailDeliveryCalendar(CoordinatorEntity, CalendarEntity):
    """A calendar of announced/expected deliveries."""

    _attr_icon = "mdi:calendar-badge"

    def __init__(self, config: MailAndPackagesConfigEntry, coordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._host = config.data[CONF_HOST]
        self._entry_id = config.entry_id
        self._attr_name = f"{self._host} Expected Deliveries"
        self._attr_unique_id = f"calendar_{self._host}_deliveries_{self._entry_id}"

    @property
    def device_info(self) -> dict:
        """Return device information about the mailbox."""
        return {
            "connections": {(DOMAIN, self._entry_id)},
            "name": self._host,
            "manufacturer": "IMAP E-Mail",
            "sw_version": VERSION,
        }

    def _build_events(self) -> list[CalendarEvent]:
        """Build all-day CalendarEvents from the current coordinator data."""
        data = self.coordinator.data or {}
        events: list[CalendarEvent] = []

        # DHL Briefankündigung letters, on their announced delivery date.
        for letter in data.get("dhl_brief_letters", []) or []:
            day = _parse_date(letter.get("date"))
            if day:
                events.append(
                    CalendarEvent(
                        summary="DHL Brief",
                        start=day,
                        end=day + datetime.timedelta(days=1),
                    )
                )

        # Amazon packages arriving today.
        amazon = data.get("amazon_packages")
        if isinstance(amazon, int) and amazon > 0:
            today = dt_util.now().date()
            events.append(
                CalendarEvent(
                    summary=f"{amazon} Amazon package(s)",
                    start=today,
                    end=today + datetime.timedelta(days=1),
                )
            )

        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        today = dt_util.now().date()
        upcoming = sorted(
            (e for e in self._build_events() if e.end > today),
            key=lambda e: e.start,
        )
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return events within the requested window."""
        start = start_date.date()
        end = end_date.date()
        return [e for e in self._build_events() if e.start < end and e.end > start]
