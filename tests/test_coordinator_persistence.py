"""Tests for persistent tracking state in MailDataUpdateCoordinator."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.mail_and_packages.const import (
    AMAZON_DELIVERED_ORDERS,
    AMAZON_ORDER_TRACKING,
)
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
        {
            "in_transit": {"fedex": {"123456789012": "2024-06-10"}},
            "history": [],
            "history_backfilled": False,
            "manual": {},
        }
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


@pytest.mark.asyncio
async def test_delivered_tracking_creates_history_record(coordinator):
    """Delivered tracking numbers are appended to history instead of disappearing."""
    coordinator._in_transit_tracking["ups"] = {"1Z123": "2026-07-01"}
    data = {}

    coordinator._apply_tracking_state(data, {"ups_delivered": ["1Z123"]}, "2026-07-12")

    assert coordinator._history == [
        {
            "carrier": "ups",
            "number": "1Z123",
            "delivered": "2026-07-12",
            "first_seen": "2026-07-01",
            "history": [],
        }
    ]
    assert "1Z123" not in coordinator._in_transit_tracking.get("ups", {})


@pytest.mark.asyncio
async def test_history_survives_save_and_load(coordinator):
    """History records persist across a save/load cycle through the Store."""
    coordinator._history = [
        {
            "carrier": "ups",
            "number": "1Z123",
            "delivered": "2026-07-12",
            "first_seen": "2026-07-01",
        }
    ]
    saved_payload = {}

    async def fake_save(payload):
        saved_payload.update(payload)

    coordinator._store.async_save.side_effect = fake_save
    await coordinator._async_save_tracking()

    coordinator._store.async_load.return_value = saved_payload
    coordinator._history = []
    await coordinator._async_load_tracking()

    assert coordinator._history == [
        {
            "carrier": "ups",
            "number": "1Z123",
            "delivered": "2026-07-12",
            "first_seen": "2026-07-01",
        }
    ]


@pytest.mark.asyncio
async def test_history_prunes_entries_older_than_90_days(coordinator):
    """Entries older than HISTORY_RETENTION_DAYS are removed when finalized."""
    coordinator._history = [
        {
            "carrier": "ups",
            "number": "OLD",
            "delivered": "2026-01-01",  # more than 90 days before 2026-07-12
            "first_seen": None,
        },
        {
            "carrier": "ups",
            "number": "NEW",
            "delivered": "2026-06-01",  # within 90 days of 2026-07-12
            "first_seen": None,
        },
    ]
    data = {}

    coordinator._finalize_history(data, "2026-07-12")

    numbers = [record["number"] for record in coordinator._history]
    assert "OLD" not in numbers
    assert "NEW" in numbers
    assert data["packages_history"] == len(coordinator._history)
    assert data["packages_history_details"] == coordinator._history


@pytest.mark.asyncio
async def test_history_sorted_newest_first_on_finalize(coordinator):
    """Finalized history is sorted with the most recent delivery first."""
    coordinator._history = [
        {
            "carrier": "ups",
            "number": "A",
            "delivered": "2026-06-01",
            "first_seen": None,
        },
        {
            "carrier": "ups",
            "number": "B",
            "delivered": "2026-07-01",
            "first_seen": None,
        },
    ]
    data = {}

    coordinator._finalize_history(data, "2026-07-12")

    assert [r["number"] for r in coordinator._history] == ["B", "A"]


@pytest.mark.asyncio
async def test_amazon_delivered_history_dedup(coordinator):
    """Same Amazon order id is not appended twice across repeated scans."""
    data = {
        AMAZON_DELIVERED_ORDERS: ["123-4567890-1234567"],
        AMAZON_ORDER_TRACKING: {"123-4567890-1234567": "TBA123456789"},
    }

    coordinator._record_amazon_delivered_history(data, "2026-07-12")
    coordinator._record_amazon_delivered_history(data, "2026-07-12")

    amazon_records = [r for r in coordinator._history if r["carrier"] == "amazon"]
    assert len(amazon_records) == 1
    assert amazon_records[0] == {
        "carrier": "amazon",
        "number": "TBA123456789",
        "order": "123-4567890-1234567",
        "delivered": "2026-07-12",
        "first_seen": None,
    }


@pytest.mark.asyncio
async def test_backfill_history_creates_record_from_delivered_entry(coordinator):
    """First-run backfill picks up an already-delivered universal_tracking_details entry."""
    data = {
        "universal_tracking_details": [
            {
                "carrier": "ups",
                "number": "1Z999",
                "status": "Delivered",
                "status_code": 40,
                "last_update": "2026-07-10T08:00:00",
            }
        ]
    }

    coordinator._backfill_history(data, "2026-07-12")

    assert coordinator._history == [
        {
            "carrier": "ups",
            "number": "1Z999",
            "delivered": "2026-07-10",
            "first_seen": None,
            "history": [],
        }
    ]
    assert coordinator._history_backfilled is True


@pytest.mark.asyncio
async def test_backfill_history_runs_only_once_no_duplicate(coordinator):
    """Second run (or a second call) does not duplicate the backfilled record."""
    data = {
        "universal_tracking_details": [
            {
                "carrier": "ups",
                "number": "1Z999",
                "status": "Delivered",
                "status_code": 40,
                "last_update": "2026-07-10T08:00:00",
            }
        ]
    }

    coordinator._backfill_history(data, "2026-07-12")
    coordinator._backfill_history(data, "2026-07-12")

    assert len(coordinator._history) == 1

    # Flag persists across a save/load cycle through the Store.
    saved_payload = {}

    async def fake_save(payload):
        saved_payload.update(payload)

    coordinator._store.async_save.side_effect = fake_save
    await coordinator._async_save_tracking()

    coordinator._store.async_load.return_value = saved_payload
    coordinator._history_backfilled = False
    await coordinator._async_load_tracking()

    assert coordinator._history_backfilled is True

    # Even with the flag reset to simulate a second scan attempt, a later
    # call after reloading (flag True) must not add another record.
    coordinator._backfill_history(data, "2026-07-12")
    assert len(coordinator._history) == 1


@pytest.mark.asyncio
async def test_backfill_history_ignores_non_delivered_entries(coordinator):
    """Entries that are not status 'Delivered' are not backfilled."""
    data = {
        "universal_tracking_details": [
            {
                "carrier": "fedex",
                "number": "999888777",
                "status": "InTransit",
                "status_code": 10,
                "last_update": "2026-07-10T08:00:00",
            }
        ]
    }

    coordinator._backfill_history(data, "2026-07-12")

    assert coordinator._history == []
    assert coordinator._history_backfilled is True
