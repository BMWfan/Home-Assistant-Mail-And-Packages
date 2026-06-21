"""Tests for UniversalTrackingShipper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mail_and_packages.const import ATTR_COUNT, ATTR_TRACKING
from custom_components.mail_and_packages.shippers.universal import (
    UniversalTrackingShipper,
    _extract_tracking_numbers,
    _has_context,
)


def test_handles_sensor():
    """Test that only universal_packages is handled."""
    assert UniversalTrackingShipper.handles_sensor("universal_packages") is True
    assert UniversalTrackingShipper.handles_sensor("ups_delivered") is False
    assert UniversalTrackingShipper.handles_sensor("dpd_delivering") is False


def test_extract_ups_tracking():
    """UPS 1Z number is recognised without context."""
    found: dict[str, str] = {}
    _extract_tracking_numbers("Track your package: 1Z12345E0291980793", found)
    assert "1Z12345E0291980793" in found
    assert found["1Z12345E0291980793"] == "ups"


def test_extract_dpd_tracking_with_context():
    """14-digit DPD number is only recognised with a nearby keyword."""
    found: dict[str, str] = {}
    _extract_tracking_numbers("Sendungsnummer: 05085100012345", found)
    assert "05085100012345" in found
    assert found["05085100012345"] == "dpd"


def test_extract_dpd_no_context_rejected():
    """14-digit number without a delivery keyword is ignored."""
    found: dict[str, str] = {}
    _extract_tracking_numbers("Reference: 05085100012345 in year 2024", found)
    assert "05085100012345" not in found


def test_no_double_counting():
    """A number matched by a specific pattern is not matched again."""
    found: dict[str, str] = {}
    text = "UPS: 1Z12345E0291980793 and also some delivery: 05085100012345"
    _extract_tracking_numbers(text, found)
    # 1Z number must be ups, not overridden by a broader pattern
    assert found.get("1Z12345E0291980793") == "ups"


def test_has_context_true():
    """_has_context returns True when keyword is nearby."""
    text = "Please track your shipment using this number: 05085100012345"
    pos = text.index("05085100012345")
    assert _has_context(text, pos) is True


def test_has_context_false():
    """_has_context returns False when no keyword is in range."""
    text = "Invoice #05085100012345 for fiscal year 2024"
    pos = text.index("05085100012345")
    assert _has_context(text, pos) is False


@pytest.mark.asyncio
async def test_universal_ups_email(hass, mock_imap_universal_ups):
    """Test scanning a shop email with embedded UPS tracking number."""
    shipper = UniversalTrackingShipper(hass, {})

    with patch(
        "custom_components.mail_and_packages.shippers.universal.email_search_since",
        return_value=[b"1"],
    ):
        result = await shipper.process(
            mock_imap_universal_ups, "10-Jun-2024", "universal_packages"
        )

    assert result[ATTR_COUNT] == 1
    assert "1Z12345E0291980793" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_universal_dpd_email(hass, mock_imap_universal_dpd):
    """Test scanning a shop email with a DPD tracking number and Sendungsnummer context."""
    shipper = UniversalTrackingShipper(hass, {})

    with patch(
        "custom_components.mail_and_packages.shippers.universal.email_search_since",
        return_value=[b"1"],
    ):
        result = await shipper.process(
            mock_imap_universal_dpd, "10-Jun-2024", "universal_packages"
        )

    assert result[ATTR_COUNT] == 1
    assert "05085100012345" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_universal_no_emails(hass, mock_imap_universal_ups):
    """Test that empty search result returns zero count."""
    shipper = UniversalTrackingShipper(hass, {})

    with patch(
        "custom_components.mail_and_packages.shippers.universal.email_search_since",
        return_value=[],
    ):
        result = await shipper.process(
            mock_imap_universal_ups, "10-Jun-2024", "universal_packages"
        )

    assert result[ATTR_COUNT] == 0
    assert result[ATTR_TRACKING] == []


@pytest.mark.asyncio
async def test_universal_search_error(hass, mock_imap_universal_ups):
    """Test graceful handling when IMAP search fails."""
    shipper = UniversalTrackingShipper(hass, {})

    with patch(
        "custom_components.mail_and_packages.shippers.universal.email_search_since",
        side_effect=OSError("connection lost"),
    ):
        result = await shipper.process(
            mock_imap_universal_ups, "10-Jun-2024", "universal_packages"
        )

    assert result[ATTR_COUNT] == 0
    assert result[ATTR_TRACKING] == []


@pytest.mark.asyncio
async def test_process_batch(hass, mock_imap_universal_ups):
    """Test process_batch delegates to process() and sets sensor key."""
    shipper = UniversalTrackingShipper(hass, {})
    cache = MagicMock()

    with patch(
        "custom_components.mail_and_packages.shippers.universal.email_search_since",
        return_value=[b"1"],
    ):
        result = await shipper.process_batch(
            mock_imap_universal_ups,
            "10-Jun-2024",
            ["universal_packages"],
            cache,
        )

    assert "universal_packages" in result
    assert result["universal_packages"] == result[ATTR_COUNT]
