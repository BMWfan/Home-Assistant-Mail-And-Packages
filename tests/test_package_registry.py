"""Tests for PackageRegistry."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_registry():
    """Return a PackageRegistry with a mocked Store."""
    from custom_components.mail_and_packages.package_registry import PackageRegistry

    hass = MagicMock()
    with patch(
        "custom_components.mail_and_packages.package_registry.Store",
        autospec=True,
    ) as MockStore:
        instance = MockStore.return_value
        instance.async_load = AsyncMock(return_value=None)
        instance.async_save = AsyncMock(return_value=None)
        reg = PackageRegistry(hass, "test_entry_id")
        reg._store = instance
    return reg


# ---------------------------------------------------------------------------
# async_add_or_update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_new_package():
    reg = _make_registry()
    changed = await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    assert changed is True
    assert "1Z999AA10123456784" in reg._packages
    assert reg._packages["1Z999AA10123456784"]["status"] == "in_transit"
    assert reg._packages["1Z999AA10123456784"]["carrier"] == "ups"


@pytest.mark.asyncio
async def test_no_change_same_status():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    changed = await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    assert changed is False


@pytest.mark.asyncio
async def test_valid_forward_transition():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    changed = await reg.async_add_or_update("1Z999AA10123456784", "ups", "delivered")
    assert changed is True
    assert reg._packages["1Z999AA10123456784"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_invalid_backward_transition_ignored():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "delivered")
    changed = await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    assert changed is False
    assert reg._packages["1Z999AA10123456784"]["status"] == "delivered"


# ---------------------------------------------------------------------------
# async_mark_delivered / async_clear_package / async_clear_all_delivered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_delivered():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    ok = await reg.async_mark_delivered("1Z999AA10123456784")
    assert ok is True
    assert reg._packages["1Z999AA10123456784"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_mark_delivered_unknown_returns_false():
    reg = _make_registry()
    ok = await reg.async_mark_delivered("UNKNOWN123")
    assert ok is False


@pytest.mark.asyncio
async def test_clear_package():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")
    ok = await reg.async_clear_package("1Z999AA10123456784")
    assert ok is True
    assert "1Z999AA10123456784" not in reg._packages


@pytest.mark.asyncio
async def test_clear_all_delivered():
    reg = _make_registry()
    await reg.async_add_or_update("AA1", "ups", "delivered")
    await reg.async_add_or_update("AA2", "fedex", "delivered")
    await reg.async_add_or_update("AA3", "dhl", "in_transit")
    count = await reg.async_clear_all_delivered()
    assert count == 2
    assert "AA1" not in reg._packages
    assert "AA2" not in reg._packages
    assert "AA3" in reg._packages  # in_transit stays


# ---------------------------------------------------------------------------
# Properties: count_tracked, count_in_transit, count_delivered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_counts():
    reg = _make_registry()
    await reg.async_add_or_update("T1", "ups", "in_transit")
    await reg.async_add_or_update("T2", "fedex", "out_for_delivery")
    await reg.async_add_or_update("T3", "dhl", "delivered")
    await reg.async_add_or_update("T4", "usps", "detected")

    assert reg.count_tracked == 4
    assert reg.count_in_transit == 3   # detected + in_transit + out_for_delivery
    assert reg.count_delivered == 1


@pytest.mark.asyncio
async def test_cleared_not_in_active():
    reg = _make_registry()
    await reg.async_add_or_update("T1", "ups", "delivered")
    await reg.async_clear_package("T1")
    assert reg.count_tracked == 0
    assert reg.active_packages == []


# ---------------------------------------------------------------------------
# async_update_from_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_from_data_adds_in_transit():
    reg = _make_registry()
    data = {
        "ups_tracking": ["1Z999AA10123456784"],
        "ups_delivered": 0,
    }
    await reg.async_update_from_data(data)
    assert "1Z999AA10123456784" in reg._packages
    assert reg._packages["1Z999AA10123456784"]["status"] == "in_transit"


@pytest.mark.asyncio
async def test_update_from_data_auto_delivers():
    reg = _make_registry()
    # Package was in_transit
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")

    # Now delivering list is empty but delivered count > 0
    data = {
        "ups_tracking": [],  # no longer in delivering emails
        "ups_delivered": 1,
    }
    await reg.async_update_from_data(data)
    assert reg._packages["1Z999AA10123456784"]["status"] == "delivered"


@pytest.mark.asyncio
async def test_update_from_data_no_auto_deliver_if_still_delivering():
    reg = _make_registry()
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "in_transit")

    # Package is still in delivering list → don't mark delivered
    data = {
        "ups_tracking": ["1Z999AA10123456784"],
        "ups_delivered": 1,
    }
    await reg.async_update_from_data(data)
    assert reg._packages["1Z999AA10123456784"]["status"] == "in_transit"


@pytest.mark.asyncio
async def test_update_from_data_universal_tracking_adds_detected():
    reg = _make_registry()
    data = {
        "universal_tracking_detail": [
            {"number": "1Z999AA10123456784", "carrier": "ups"},
        ]
    }
    await reg.async_update_from_data(data)
    assert "1Z999AA10123456784" in reg._packages
    assert reg._packages["1Z999AA10123456784"]["status"] == "detected"


@pytest.mark.asyncio
async def test_update_from_data_does_not_downgrade_status():
    reg = _make_registry()
    # Already delivered
    await reg.async_add_or_update("1Z999AA10123456784", "ups", "delivered")

    # Scanner sees it again in universal tracking
    data = {
        "universal_tracking_detail": [
            {"number": "1Z999AA10123456784", "carrier": "ups"},
        ]
    }
    await reg.async_update_from_data(data)
    # Status must not regress
    assert reg._packages["1Z999AA10123456784"]["status"] == "delivered"


# ---------------------------------------------------------------------------
# async_load: restores saved data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_restores_packages():
    from custom_components.mail_and_packages.package_registry import PackageRegistry

    saved = {
        "1Z999AA10123456784": {
            "tracking_number": "1Z999AA10123456784",
            "carrier": "ups",
            "status": "in_transit",
            "first_seen": "2024-01-15T10:00:00+00:00",
            "last_updated": "2024-01-15T10:00:00+00:00",
        }
    }

    hass = MagicMock()
    with patch(
        "custom_components.mail_and_packages.package_registry.Store",
        autospec=True,
    ) as MockStore:
        instance = MockStore.return_value
        instance.async_load = AsyncMock(return_value=saved)
        instance.async_save = AsyncMock(return_value=None)
        reg = PackageRegistry(hass, "test_entry")
        reg._store = instance

    await reg.async_load()
    assert reg.count_tracked == 1
    assert reg._packages["1Z999AA10123456784"]["status"] == "in_transit"
