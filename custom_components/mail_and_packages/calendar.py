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
    """Parse a YYYY-MM-DD(...) or DD.MM.YYYY string into a date, or None.

    DHL's Briefankündigung API returns dates as "DD.MM.YYYY" (German
    order), not ISO -- fromisoformat alone silently failed on every real
    letter date, so this calendar never showed any (live-verified
    2026-07-18). Try the German format first, then fall back to ISO for
    any other source (e.g. a future YYYY-MM-DD field).
    """
    if not raw:
        return None
    raw = str(raw).strip()
    try:
        day, month, year = raw.split(".")
        return datetime.date(int(year), int(month), int(day))
    except (ValueError, TypeError):
        pass
    try:
        return datetime.date.fromisoformat(raw[:10])
    except (ValueError, TypeError):
        return None


def _as_dt(value: datetime.date | datetime.datetime) -> datetime.datetime:
    """Normalize a CalendarEvent's start/end (date OR datetime) for comparison.

    DHL letters/Amazon produce all-day events (plain `date`), package ETAs
    produce timed events (`datetime`) -- comparing the two directly raises
    "'>' not supported between instances of 'datetime.datetime' and
    'datetime.date'" (live-verified 2026-07-18: the calendar's `event`
    property and `async_get_events` both did this, so the entity silently
    showed no next-event data at all despite _build_events() producing
    real events).
    """
    if isinstance(value, datetime.datetime):
        return value
    return dt_util.start_of_local_day(value)


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

        # Tracked packages (universal scanner + 17track) with an official
        # estimated-delivery time -- one timed event per shipment instead
        # of an all-day block, since 17track gives an actual "by" time.
        for detail in data.get("universal_tracking_details", []) or []:
            eta_raw = detail.get("estimated_delivery")
            if not eta_raw or detail.get("status") == "Delivered":
                continue
            try:
                eta = dt_util.parse_datetime(eta_raw)
            except (ValueError, TypeError):
                eta = None
            if not eta:
                continue
            carrier = str(detail.get("carrier") or "").upper()
            number = detail.get("number", "")
            events.append(
                CalendarEvent(
                    summary=f"{carrier} {number}".strip() or "Package delivery",
                    start=eta,
                    end=eta + datetime.timedelta(minutes=30),
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
        now = dt_util.now()
        upcoming = sorted(
            (e for e in self._build_events() if _as_dt(e.end) > now),
            key=lambda e: _as_dt(e.start),
        )
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return events within the requested window."""
        return [
            e
            for e in self._build_events()
            if _as_dt(e.start) < end_date and _as_dt(e.end) > start_date
        ]
