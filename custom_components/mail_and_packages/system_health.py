"""System Health for Mail and Packages.

Shows a small health panel under Settings > System > Repairs/System information:
how many accounts are configured, whether the last scan succeeded, and when the
mailbox was last scanned.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register the system health callback."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return integration health information."""
    entries = hass.config_entries.async_entries(DOMAIN)
    info: dict[str, Any] = {"configured_accounts": len(entries)}

    coordinator = None
    for entry in entries:
        runtime = getattr(entry, "runtime_data", None)
        coordinator = getattr(runtime, "coordinator", None)
        if coordinator is not None:
            break

    if coordinator is not None:
        info["last_scan_ok"] = bool(getattr(coordinator, "last_update_success", False))
        data = getattr(coordinator, "data", None) or {}
        last_updated = data.get("mail_updated")
        if last_updated:
            info["last_scan"] = last_updated

    return info
