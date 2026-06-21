"""Tests for init."""

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mail_and_packages.const import DOMAIN
from custom_components.mail_and_packages import MailDataUpdateCoordinator, _MailEntryData
from tests.const import (
    FAKE_CONFIG_DATA,
    FAKE_CONFIG_DATA_AMAZON_FWD_STRING,
    FAKE_CONFIG_DATA_CUSTOM_IMG,
    FAKE_CONFIG_DATA_MISSING_TIMEOUT,
    FAKE_CONFIG_DATA_NO_PATH,
)


async def test_unload_entry(hass, mock_update, mock_copy_overlays):
    """Test unloading entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 43
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    assert await hass.config_entries.async_unload(entries[0].entry_id)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 43
    assert len(hass.states.async_entity_ids(DOMAIN)) == 0

    assert await hass.config_entries.async_remove(entries[0].entry_id)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 0


async def test_setup_entry(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """Test settting up entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 43
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1


async def test_no_path_no_sec(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """Test settting up entities."""
    entry = MockConfigEntry(
        domain=DOMAIN, title="imap.test.email", data=FAKE_CONFIG_DATA_NO_PATH, version=3
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 43
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1


async def test_missing_imap_timeout(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """Test settting up entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA_MISSING_TIMEOUT,
        version=3,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 42
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1


async def test_amazon_fwds_string(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """Test settting up entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA_AMAZON_FWD_STRING,
        version=3,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 42
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1


async def test_custom_img(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """Test settting up entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA_CUSTOM_IMG,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 43
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# Feature 4: Modern HA compatibility
# ---------------------------------------------------------------------------


async def test_runtime_data_set_after_setup(
    hass,
    mock_imap_no_email,
    mock_osremove,
    mock_osmakedir,
    mock_listdir,
    mock_update_time,
    mock_copy_overlays,
    mock_hash_file,
    mock_getctime_today,
    mock_update,
):
    """runtime_data must be a _MailEntryData with a coordinator after setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert isinstance(entry.runtime_data, _MailEntryData)
    assert isinstance(entry.runtime_data.coordinator, MailDataUpdateCoordinator)


async def test_imap_timeout_retains_previous_data(hass, mock_update):
    """On IMAP timeout after initial load, previous data is returned."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data.coordinator
    previous_data = coordinator.data

    with patch(
        "custom_components.mail_and_packages.process_emails",
        side_effect=asyncio.TimeoutError,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.data is previous_data
    assert coordinator.last_update_success is True


async def test_imap_timeout_on_first_run_raises(hass):
    """On IMAP timeout with no previous data, UpdateFailed is raised."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="imap.test.email",
        data=FAKE_CONFIG_DATA,
    )
    entry.add_to_hass(hass)

    coordinator = MailDataUpdateCoordinator(
        hass, entry, "imap.test.email", 1, 5, FAKE_CONFIG_DATA
    )
    assert coordinator.data is None

    with patch(
        "custom_components.mail_and_packages.process_emails",
        side_effect=asyncio.TimeoutError,
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
