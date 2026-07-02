"""Tests for UniversalTrackingShipper."""

from unittest.mock import MagicMock, patch

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


def test_kundennummer_does_not_satisfy_context():
    """Bare 'nummer' must not match as a substring of 'Kundennummer' etc.

    Regression test: the context regex previously included a bare 'nummer'
    substring, which matches inside "Kundennummer"/"Bestellnummer"/
    "Rechnungsnummer" -- i.e. an order or customer reference, not a
    delivery context -- defeating the context check for nearly any German
    commerce email and producing false-positive "package" counts (observed
    live: 186 "tracking numbers" extracted from 90 emails in three days).
    """
    found: dict[str, str] = {}
    _extract_tracking_numbers(
        "Ihre Kundennummer: 28349311403. Vielen Dank fuer Ihre Bestellung.",
        found,
    )
    assert "28349311403" not in found

    found = {}
    _extract_tracking_numbers(
        "Ihre Rechnungsnummer lautet 28419851439 fuer den Auftrag vom 1. Juli.",
        found,
    )
    assert "28419851439" not in found


def test_genuine_gls_package_still_matches():
    """A real GLS delivery mention (contains 'Paket') still matches after tightening."""
    found: dict[str, str] = {}
    _extract_tracking_numbers(
        "Ihr Paket 28453901515 wurde durch GLS zugestellt.", found
    )
    assert found.get("28453901515") == "gls"


def test_gls_requires_brand_name_not_just_generic_package_mention():
    """An 11-12 digit number near 'Paket'/'delivery' alone is not enough for GLS.

    Regression test: GLS's bare 11-12-digit pattern only required a generic
    delivery keyword nearby, which almost any shop order confirmation
    satisfies via an unrelated customer/order number sitting near the word
    "Paket" -- observed live as 43+ "GLS delivering" packages the user never
    had. GLS's own brand name must also appear nearby.
    """
    found: dict[str, str] = {}
    _extract_tracking_numbers(
        "Ihre Bestellnummer 28349311403, Ihr Paket ist unterwegs.", found
    )
    assert "28349311403" not in found

    found = {}
    _extract_tracking_numbers(
        "GLS-Sendungsverfolgung: 28502379919 ist jetzt unterwegs.", found
    )
    assert found.get("28502379919") == "gls"


def test_dhl_germany_number_classified_as_dhl_not_fedex():
    """DHL Germany numbers (003404 prefix, 20 digits) must be labeled dhl.

    Regression test: with no DHL-specific pattern, real DHL shipments were
    labeled "fedex" via the generic 20-digit pattern -- routing them to the
    wrong carrier sensor.
    """
    found: dict[str, str] = {}
    _extract_tracking_numbers(
        "Ihre DHL Sendung 00340434650122256337 ist unterwegs.", found
    )
    assert found.get("00340434650122256337") == "dhl"


def test_evri_pattern_requires_context():
    """H+15-alphanumeric must not match arbitrary base64-ish fragments.

    Regression test: evri's pattern had no context requirement and no word
    boundaries, so it matched any 16-character "H..." fragment anywhere in
    HTML mail -- tracking pixel URLs, encoded query params, hashes -- none
    of which are tracking numbers.
    """
    found: dict[str, str] = {}
    _extract_tracking_numbers(
        "View this email in your browser: "
        "https://x.example/t/HYNNA5CNFSNUACCM/track.gif",
        found,
    )
    assert "HYNNA5CNFSNUACCM" not in found

    found = {}
    _extract_tracking_numbers(
        "Your parcel tracking number is HYNNA5CNFSNUACCM, track your delivery here.",
        found,
    )
    assert found.get("HYNNA5CNFSNUACCM") == "evri"


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
