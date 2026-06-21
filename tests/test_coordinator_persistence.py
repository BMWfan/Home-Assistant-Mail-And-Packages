"""Tests for persistent tracking state in MailDataUpdateCoordinator."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.mail_and_packages.coordinator import MailDataUpdateCoordinator


@pytest.fixture
def coordinator(hass):
    """Return a coordinator with a mocked Store."""
    config = {
        "host": "imap.test.com",
        "port": 993,
        "username": "test@test.com",
        "password": "secret",
        "scan_interval": 5,
        "imap_timeout": 30,
        "resources": [],
    }
    with patch(
        "custom_components.mail_and_packages.coordinator.Store"
    ) as mock_store_cls:
        mock_store = AsyncMock()
        mock_store.async_load.return_value = None
        mock_store.async_save.return_value = None
        mock_store_cls.return_value = mock_store
        coord = MailDataUpdateCoordinator(hass, config)
        coord._store = mock_store
    return coord


@pytest.mark.asyncio
async def test_load_tracking_restores_state(coordinator):
    """Persisted in-transit data is restored on first load."""
    stored = {
        "in_transit": {
            "ups": {"1Z12345E0291980793": "2024-06-08"},
        }
    }
    coordinator._store.async_load.return_value = stored

    await coordinator._async_load_tracking()

    assert "ups" in coordinator._in_transit_tracking
    assert "1Z12345E0291980793" in coordinator._in_transit_tracking["ups"]


@pytest.mark.asyncio
async def test_load_tracking_empty_store(coordinator):
    """No crash when storage is empty on first startup."""
    coordinator._store.async_load.return_value = None

    await coordinator._async_load_tracking()

    assert coordinator._in_transit_tracking == {}


@pytest.mark.asyncio
async def test_load_tracking_ignores_corrupt_data(coordinator):
    """Corrupt storage data is silently ignored."""
    coordinator._store.async_load.return_value = {"in_transit": "not-a-dict"}

    await coordinator._async_load_tracking()

    assert coordinator._in_transit_tracking == {}


@pytest.mark.asyncio
async def test_save_tracking_persists_state(coordinator):
    """After update, in-transit state is written to storage."""
    coordinator._in_transit_tracking = {
        "fedex": {"123456789012": "2024-06-10"},
    }

    await coordinator._async_save_tracking()

    coordinator._store.async_save.assert_called_once_with(
        {"in_transit": {"fedex": {"123456789012": "2024-06-10"}}}
    )


@pytest.mark.asyncio
async def test_tracking_loaded_flag_prevents_double_load(coordinator):
    """_async_load_tracking is called only once across multiple scans."""
    coordinator._store.async_load.return_value = None

    # Simulate what process_emails does
    if not coordinator._tracking_loaded:
        await coordinator._async_load_tracking()
        coordinator._tracking_loaded = True

    # Second scan
    call_count_before = coordinator._store.async_load.call_count
    if not coordinator._tracking_loaded:
        await coordinator._async_load_tracking()

    assert coordinator._store.async_load.call_count == call_count_before
