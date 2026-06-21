"""Mail and Packages Integration."""
import asyncio
import dataclasses
import logging
from datetime import timedelta

from async_timeout import timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_RESOURCES
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ALLOW_EXTERNAL,
    CONF_AMAZON_DAYS,
    CONF_AMAZON_FWDS,
    CONF_IMAGE_SECURITY,
    CONF_IMAP_TIMEOUT,
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    DEFAULT_AMAZON_DAYS,
    DEFAULT_IMAP_TIMEOUT,
    DOMAIN,
    ISSUE_URL,
    PACKAGES_DELIVERED,
    PACKAGES_IN_TRANSIT,
    PACKAGES_TRACKED,
    PLATFORMS,
    SERVICE_ADD_PACKAGE,
    SERVICE_CLEAR_ALL_DELIVERED,
    SERVICE_CLEAR_PACKAGE,
    SERVICE_MARK_DELIVERED,
    VERSION,
)
from .helpers import default_image_path, process_emails
from .package_registry import PackageRegistry


@dataclasses.dataclass
class _MailEntryData:
    coordinator: "MailDataUpdateCoordinator"
    cameras: list = dataclasses.field(default_factory=list)


_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, config_entry: ConfigEntry
):  # pylint: disable=unused-argument
    """Disallow configuration via YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Load the saved entities."""
    _LOGGER.info(
        "Version %s is starting, if you have any issues please report" " them here: %s",
        VERSION,
        ISSUE_URL,
    )
    updated_config = config_entry.data.copy()

    # Set amazon fwd blank if missing
    if CONF_AMAZON_FWDS not in updated_config.keys():
        updated_config[CONF_AMAZON_FWDS] = []

    # Set default timeout if missing
    if CONF_IMAP_TIMEOUT not in updated_config.keys():
        updated_config[CONF_IMAP_TIMEOUT] = DEFAULT_IMAP_TIMEOUT

    # Set external path off by default
    if CONF_ALLOW_EXTERNAL not in config_entry.data.keys():
        updated_config[CONF_ALLOW_EXTERNAL] = False

    updated_config[CONF_PATH] = default_image_path(hass, config_entry)

    # Set image security always on
    if CONF_IMAGE_SECURITY not in config_entry.data.keys():
        updated_config[CONF_IMAGE_SECURITY] = True

    # Sort the resources
    updated_config[CONF_RESOURCES] = sorted(updated_config[CONF_RESOURCES])

    # Make sure amazon forwarding emails are not a string
    if isinstance(updated_config[CONF_AMAZON_FWDS], str):
        tmp = updated_config[CONF_AMAZON_FWDS]
        tmp_list = []
        if "," in tmp:
            tmp_list = tmp.split(",")
        else:
            tmp_list.append(tmp)
        updated_config[CONF_AMAZON_FWDS] = tmp_list

    if updated_config != config_entry.data:
        hass.config_entries.async_update_entry(config_entry, data=updated_config)

    config_entry.add_update_listener(update_listener)

    config_entry.options = config_entry.data
    config = config_entry.data

    # Variables for data coordinator
    host = config.get(CONF_HOST)
    the_timeout = config.get(CONF_IMAP_TIMEOUT)
    interval = config.get(CONF_SCAN_INTERVAL)

    # Setup the data coordinator
    coordinator = MailDataUpdateCoordinator(
        hass, config_entry, host, the_timeout, interval, config
    )

    # Load package registry and attach to coordinator
    registry = PackageRegistry(hass, config_entry.entry_id)
    await registry.async_load()
    coordinator.registry = registry

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    # Raise ConfEntryNotReady if coordinator didn't update
    if not coordinator.last_update_success:
        _LOGGER.error("Error updating sensor data: %s", coordinator.last_exception)
        raise ConfigEntryNotReady

    config_entry.runtime_data = _MailEntryData(coordinator=coordinator)

    _register_services(hass)

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug("Attempting to unload sensors from the %s integration", DOMAIN)

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        _LOGGER.debug("Successfully removed sensors from the %s integration", DOMAIN)

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener."""
    _LOGGER.debug("Attempting to reload sensors from the %s integration", DOMAIN)

    if config_entry.data == config_entry.options:
        _LOGGER.debug("No changes detected not reloading sensors.")
        return

    new_data = config_entry.options.copy()

    hass.config_entries.async_update_entry(
        entry=config_entry,
        data=new_data,
    )

    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_migrate_entry(hass, config_entry):
    """Migrate an old config entry."""
    version = config_entry.version

    # 1 -> 4: Migrate format
    if version == 1:
        _LOGGER.debug("Migrating from version %s", version)
        updated_config = config_entry.data.copy()

        if CONF_AMAZON_FWDS in updated_config.keys():
            if not isinstance(updated_config[CONF_AMAZON_FWDS], list):
                updated_config[CONF_AMAZON_FWDS] = [
                    x.strip() for x in updated_config[CONF_AMAZON_FWDS].split(",")
                ]
            else:
                updated_config[CONF_AMAZON_FWDS] = []
        else:
            _LOGGER.warning("Missing configuration data: %s", CONF_AMAZON_FWDS)

        # Force path change
        updated_config[CONF_PATH] = "images/mail_and_packages/"

        # Always on image security
        if not config_entry.data[CONF_IMAGE_SECURITY]:
            updated_config[CONF_IMAGE_SECURITY] = True

        # Add default Amazon Days configuration
        updated_config[CONF_AMAZON_DAYS] = DEFAULT_AMAZON_DAYS

        if updated_config != config_entry.data:
            hass.config_entries.async_update_entry(config_entry, data=updated_config)

        config_entry.version = 4
        _LOGGER.debug("Migration to version %s complete", config_entry.version)

    # 2 -> 4
    if version == 2:
        _LOGGER.debug("Migrating from version %s", version)
        updated_config = config_entry.data.copy()

        # Force path change
        updated_config[CONF_PATH] = "images/mail_and_packages/"

        # Always on image security
        if not config_entry.data[CONF_IMAGE_SECURITY]:
            updated_config[CONF_IMAGE_SECURITY] = True

        # Add default Amazon Days configuration
        updated_config[CONF_AMAZON_DAYS] = DEFAULT_AMAZON_DAYS

        if updated_config != config_entry.data:
            hass.config_entries.async_update_entry(config_entry, data=updated_config)

        config_entry.version = 4
        _LOGGER.debug("Migration to version %s complete", config_entry.version)

    if version == 3:
        _LOGGER.debug("Migrating from version %s", version)
        updated_config = config_entry.data.copy()

        # Add default Amazon Days configuration
        updated_config[CONF_AMAZON_DAYS] = DEFAULT_AMAZON_DAYS

        if updated_config != config_entry.data:
            hass.config_entries.async_update_entry(config_entry, data=updated_config)

        config_entry.version = 4
        _LOGGER.debug("Migration to version %s complete", config_entry.version)

    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register package registry services (idempotent — skips if already registered)."""
    if hass.services.has_service(DOMAIN, SERVICE_MARK_DELIVERED):
        return

    def _registries():
        for entry in hass.config_entries.async_entries(DOMAIN):
            rd = getattr(entry, "runtime_data", None)
            if rd is not None and rd.coordinator.registry is not None:
                yield rd.coordinator.registry

    async def _handle_mark_delivered(call):
        tracking_number = call.data["tracking_number"]
        for reg in _registries():
            await reg.async_mark_delivered(tracking_number)

    async def _handle_clear_package(call):
        tracking_number = call.data["tracking_number"]
        for reg in _registries():
            await reg.async_clear_package(tracking_number)

    async def _handle_clear_all_delivered(call):
        for reg in _registries():
            await reg.async_clear_all_delivered()

    async def _handle_add_package(call):
        tracking_number = call.data["tracking_number"]
        carrier = call.data.get("carrier", "unknown")
        for reg in _registries():
            await reg.async_add_or_update(tracking_number, carrier, "in_transit")

    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_DELIVERED,
        _handle_mark_delivered,
        schema=vol.Schema({vol.Required("tracking_number"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_PACKAGE,
        _handle_clear_package,
        schema=vol.Schema({vol.Required("tracking_number"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_ALL_DELIVERED,
        _handle_clear_all_delivered,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_PACKAGE,
        _handle_add_package,
        schema=vol.Schema({
            vol.Required("tracking_number"): cv.string,
            vol.Optional("carrier", default="unknown"): cv.string,
        }),
    )


class MailDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching mail data."""

    def __init__(self, hass, config_entry, host, the_timeout, interval, config):
        """Initialize."""
        self.interval = timedelta(minutes=interval)
        self.name = f"Mail and Packages ({host})"
        self.timeout = the_timeout
        self.config = config
        self.hass = hass
        self.registry = None  # set after construction by async_setup_entry

        _LOGGER.debug("Data will be update every %s", self.interval)

        super().__init__(
            hass,
            _LOGGER,
            name=self.name,
            update_interval=self.interval,
            config_entry=config_entry,
        )

    async def _async_update_data(self):
        """Fetch data, retaining previous values on IMAP timeout."""
        try:
            async with timeout(self.timeout):
                try:
                    data = await self.hass.async_add_executor_job(
                        process_emails, self.hass, self.config
                    )
                except Exception as error:
                    _LOGGER.error("Problem updating sensors: %s", error)
                    raise UpdateFailed(error) from error

            if self.registry is not None:
                await self.registry.async_update_from_data(data)
                data[PACKAGES_TRACKED] = self.registry.count_tracked
                data[PACKAGES_IN_TRANSIT] = self.registry.count_in_transit
                data[PACKAGES_DELIVERED] = self.registry.count_delivered

            return data
        except asyncio.TimeoutError:
            if self.data is not None:
                _LOGGER.warning(
                    "IMAP connection timed out after %ss — retaining previous sensor values",
                    self.timeout,
                )
                return self.data
            raise UpdateFailed("IMAP connection timed out on first run")
