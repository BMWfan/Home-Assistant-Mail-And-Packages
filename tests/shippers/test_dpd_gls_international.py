"""Tests for DPD France, DPD UK and GLS France carrier support."""

from unittest.mock import patch

import pytest

from custom_components.mail_and_packages.const import ATTR_COUNT, ATTR_TRACKING
from custom_components.mail_and_packages.shippers.generic import GenericShipper


@pytest.mark.asyncio
async def test_dpd_fr_delivering(hass, mock_imap_dpd_fr_delivering):
    """Test DPD France delivering email parsing."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/dpd_fr/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_dpd_fr_delivering, "today", "dpd_fr_delivering"
        )

    assert result[ATTR_COUNT] == 1
    assert "05085100012345" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_dpd_fr_delivered(hass, mock_imap_dpd_fr_delivered):
    """Test DPD France delivered email parsing."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/dpd_fr/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_dpd_fr_delivered, "today", "dpd_fr_delivered"
        )

    assert result[ATTR_COUNT] == 1
    assert "05085100012345" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_dpd_uk_delivering(hass, mock_imap_dpd_uk_delivering):
    """Test DPD UK delivering email parsing."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/dpd_uk/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_dpd_uk_delivering, "today", "dpd_uk_delivering"
        )

    assert result[ATTR_COUNT] == 1
    assert "15085903012345" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_dpd_uk_delivered(hass, mock_imap_dpd_uk_delivered):
    """Test DPD UK delivered email parsing."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/dpd_uk/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_dpd_uk_delivered, "today", "dpd_uk_delivered"
        )

    assert result[ATTR_COUNT] == 1
    assert "15085903012345" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_gls_fr_delivering(hass, mock_imap_gls_fr_delivering):
    """Test GLS France delivering email parsed via existing gls_delivering sensor."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/gls/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_gls_fr_delivering, "today", "gls_delivering"
        )

    assert result[ATTR_COUNT] == 1
    assert "12345678901" in result[ATTR_TRACKING]


@pytest.mark.asyncio
async def test_gls_fr_delivered(hass, mock_imap_gls_fr_delivered):
    """Test GLS France delivered email parsed via existing gls_delivered sensor."""
    shipper = GenericShipper(
        hass, {"image_path": "test/path/gls/", "image_name": "test.jpg"}
    )

    with patch("custom_components.mail_and_packages.shippers.generic.Path.mkdir"):
        result = await shipper.process(
            mock_imap_gls_fr_delivered, "today", "gls_delivered"
        )

    assert result[ATTR_COUNT] == 1
    assert "12345678901" in result[ATTR_TRACKING]


def test_dpd_fr_handles_sensor():
    """Test GenericShipper recognizes DPD FR sensor types."""
    assert GenericShipper.handles_sensor("dpd_fr_delivering") is True
    assert GenericShipper.handles_sensor("dpd_fr_delivered") is True
    assert GenericShipper.handles_sensor("dpd_fr_packages") is True


def test_dpd_uk_handles_sensor():
    """Test GenericShipper recognizes DPD UK sensor types."""
    assert GenericShipper.handles_sensor("dpd_uk_delivering") is True
    assert GenericShipper.handles_sensor("dpd_uk_delivered") is True
    assert GenericShipper.handles_sensor("dpd_uk_packages") is True
