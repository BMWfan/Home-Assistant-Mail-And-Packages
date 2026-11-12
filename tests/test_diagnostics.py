"""Test the Mail and Packages diagnostics."""

from types import SimpleNamespace

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mail_and_packages.const import (
    CONF_AMAZON_FWDS,
    CONF_FORWARDED_EMAILS,
    DOMAIN,
)
from custom_components.mail_and_packages.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from tests.const import FAKE_CONFIG_DATA, FAKE_UPDATE_DATA_REDACTED


@pytest.mark.asyncio
async def test_config_entry_diagnostics(hass):
    """Test the config entry level diagnostics data dump."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    result = await async_get_config_entry_diagnostics(hass, entry)

    assert isinstance(result, dict)
    assert result["config"]["data"][CONF_HOST] == "imap.test.email"
    assert result["config"]["data"][CONF_PORT] == 993
    assert result["config"]["data"][CONF_PASSWORD] == "**REDACTED**"
    assert result["config"]["data"][CONF_USERNAME] == "**REDACTED**"
    assert result["config"]["data"][CONF_AMAZON_FWDS] == "**REDACTED**"


@pytest.mark.asyncio
async def test_device_diagnostics(hass, mock_update):
    """Test the device level diagnostics data dump."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_device_diagnostics(hass, entry, None)

    assert result == FAKE_UPDATE_DATA_REDACTED


@pytest.mark.asyncio
async def test_device_diagnostics_redacts_dynamic_tracking_and_order_fields(hass):
    """Tracking and order details must never leak into exported diagnostics."""
    data = {
        "dhl_tracking_number": "JD123456789",
        "amazon_order_id": "123-4567890-1234567",
        "amazon_order_status": "Out for delivery",
        CONF_FORWARDED_EMAILS: "private@example.test",
        "mail_count": 3,
        "status": "ok",
    }
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=SimpleNamespace(data=data))
    )

    result = await async_get_device_diagnostics(hass, entry, None)

    assert result["dhl_tracking_number"] == "**REDACTED**"
    assert result["amazon_order_id"] == "**REDACTED**"
    assert result["amazon_order_status"] == "**REDACTED**"
    assert result[CONF_FORWARDED_EMAILS] == "**REDACTED**"
    assert result["mail_count"] == 3
    assert result["status"] == "ok"
    assert data["dhl_tracking_number"] == "JD123456789"


@pytest.mark.asyncio
async def test_device_diagnostics_handles_empty_coordinator_data(hass):
    """An empty coordinator response produces safe empty diagnostics."""
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(coordinator=SimpleNamespace(data={}))
    )

    assert await async_get_device_diagnostics(hass, entry, None) == {}
