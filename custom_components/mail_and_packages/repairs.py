"""Repairs (Settings > Repairs) for Mail and Packages.

Surfaces recoverable auth problems as user-facing repair issues -- currently
the DHL Briefankündigung login expiring -- and provides a guided re-login flow,
so the user is prompted in the UI instead of having to dig through the logs or
re-run the whole config wizard.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_17TRACK_API_KEY, CONF_DHL_BRIEF_TOKENS, DOMAIN
from .shippers.dhl_briefankundigung import exchange_code, extract_code, get_auth_url

DHL_BRIEF_AUTH_ISSUE = "dhl_brief_auth_failed"
SEVENTEEN_TRACK_AUTH_ISSUE = "seventeen_track_auth_failed"


class DHLBriefReauthRepairFlow(RepairsFlow):
    """Guide the user through a fresh DHL Briefankündigung login."""

    def __init__(self, entry_id: str | None) -> None:
        """Initialize with the config entry to update once re-authenticated."""
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask for the DHL authorization code and exchange it for fresh tokens."""
        errors: dict[str, str] = {}
        # Use truthiness, not "is not None": HA can call the initial step with an
        # empty dict, which must show the form -- not run validation and flash an
        # error before the user has typed anything.
        if user_input:
            code = extract_code(user_input.get("dhl_brief_code", "").strip())
            if not code:
                errors["dhl_brief_code"] = "invalid_auth"
            else:
                try:
                    tokens = await exchange_code(self.hass, code)
                except Exception:  # noqa: BLE001
                    errors["dhl_brief_code"] = "invalid_auth"
                else:
                    entry = (
                        self.hass.config_entries.async_get_entry(self._entry_id)
                        if self._entry_id
                        else None
                    )
                    if entry is not None:
                        new_data = dict(entry.data)
                        new_data[CONF_DHL_BRIEF_TOKENS] = tokens
                        self.hass.config_entries.async_update_entry(
                            entry, data=new_data
                        )
                        await self.hass.config_entries.async_reload(entry.entry_id)
                    ir.async_delete_issue(self.hass, DOMAIN, DHL_BRIEF_AUTH_ISSUE)
                    return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("dhl_brief_code"): str}),
            description_placeholders={"auth_url": get_auth_url()},
            errors=errors,
        )


class SeventeenTrackKeyRepairFlow(RepairsFlow):
    """Let the user enter a fresh 17track.net API key."""

    def __init__(self, entry_id: str | None) -> None:
        """Initialize with the config entry to update."""
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Ask for a new 17track API key and store it."""
        errors: dict[str, str] = {}
        # Use truthiness, not "is not None": HA can call the initial step with an
        # empty dict, which must show the form -- not run validation and flash an
        # error before the user has typed anything.
        if user_input:
            key = (user_input.get(CONF_17TRACK_API_KEY) or "").strip()
            if not key:
                errors[CONF_17TRACK_API_KEY] = "invalid_auth"
            else:
                entry = (
                    self.hass.config_entries.async_get_entry(self._entry_id)
                    if self._entry_id
                    else None
                )
                if entry is not None:
                    new_data = dict(entry.data)
                    new_data[CONF_17TRACK_API_KEY] = key
                    self.hass.config_entries.async_update_entry(entry, data=new_data)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                ir.async_delete_issue(
                    self.hass, DOMAIN, SEVENTEEN_TRACK_AUTH_ISSUE
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_17TRACK_API_KEY): str}),
            errors=errors,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    """Create the repair flow for a raised issue."""
    entry_id = (data or {}).get("entry_id")
    if issue_id == SEVENTEEN_TRACK_AUTH_ISSUE:
        return SeventeenTrackKeyRepairFlow(entry_id)
    return DHLBriefReauthRepairFlow(entry_id)
