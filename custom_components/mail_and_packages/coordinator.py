"""Data coordinator for Mail and Packages."""

import asyncio
import datetime
import logging
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from time import monotonic

import anyio
from aioimaplib import IMAP4_SSL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    ConfigEntryAuthFailed,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import const
from .const import (
    ATTR_USPS_IMAGE,
    AUTH_TYPE_PASSWORD,
    CONF_ALLOW_EXTERNAL,
    CONF_AUTH_TYPE,
    CONF_CUSTOM_DAYS,
    CONF_DHL_BRIEF_ENABLED,
    CONF_DHL_BRIEF_TOKENS,
    CONF_FOLDER,
    CONF_IMAP_SECURITY,
    CONF_IMAP_TIMEOUT,
    DEFAULT_CUSTOM_DAYS,
    DEFAULT_IMAP_TIMEOUT,
    DOMAIN,
    MAX_TRACKING_AGE_DAYS,
)
from .helpers import copy_images
from .shippers import get_shipper_for_sensor
from .shippers.dhl_briefankundigung import DHLBriefankundigungClient
from .utils.cache import EmailCache
from .utils.image import default_image_path, hash_file, image_file_name
from .utils.imap import (
    InvalidAuth,
    QuerySpec,
    batch_search_folders,
    login,
    logout,
    selectfolder,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class MailAndPackagesData:
    """Data for Mail and Packages integration."""

    coordinator: "MailDataUpdateCoordinator"
    cameras: list


type MailAndPackagesConfigEntry = ConfigEntry[MailAndPackagesData]


class MailDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching mail data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        config_entry: MailAndPackagesConfigEntry = None,
    ):
        """Initialize."""
        self.interval = timedelta(minutes=config.get(CONF_SCAN_INTERVAL))
        self.name = f"Mail and Packages ({config.get(CONF_HOST)})"
        self.timeout = config.get(CONF_IMAP_TIMEOUT, DEFAULT_IMAP_TIMEOUT)
        self.config = config
        self.config_entry = config_entry
        self.hass = hass
        self._data = {}
        self._file_mtime_cache = {}
        self._hash_cache = {}
        self._in_transit_tracking: dict[str, dict[str, str]] = {}
        self._tracking_loaded = False
        self._store: Store = Store(hass, 1, f"{DOMAIN}.tracking")

        _LOGGER.debug("Data will be update every %s", self.interval)

        super().__init__(hass, _LOGGER, name=self.name, update_interval=self.interval)

    async def _get_file_hash_if_changed(self, file_path):
        """Only hash file if mtime changed."""
        try:
            mtime = await self.hass.async_add_executor_job(os.path.getmtime, file_path)
            if (
                file_path in self._file_mtime_cache
                and self._file_mtime_cache[file_path] == mtime
            ):
                return self._hash_cache.get(file_path)

            # File changed, re-hash
            file_hash = await self.hass.async_add_executor_job(hash_file, file_path)
            self._file_mtime_cache[file_path] = mtime
            self._hash_cache[file_path] = file_hash
        except OSError:
            return None
        else:
            return file_hash

    async def _async_update_data(self):
        """Fetch data."""
        start = monotonic()
        try:
            async with asyncio.timeout(self.timeout):
                try:
                    config = dict(self.config)

                    # Refresh OAuth2 token if using OAuth authentication
                    auth_type = config.get(CONF_AUTH_TYPE, AUTH_TYPE_PASSWORD)
                    if auth_type != AUTH_TYPE_PASSWORD and self.config_entry:
                        try:
                            self.hass.data.setdefault(DOMAIN, {})
                            self.hass.data[DOMAIN]["oauth_provider"] = auth_type

                            implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
                                self.hass,
                                self.config_entry,
                            )
                            session = config_entry_oauth2_flow.OAuth2Session(
                                self.hass,
                                self.config_entry,
                                implementation,
                            )
                            await session.async_ensure_token_valid()
                            config["oauth_token"] = session.token["access_token"]
                        except Exception as err:
                            _LOGGER.error("Error refreshing OAuth token")
                            _LOGGER.debug("OAuth token refresh error details: %s", err)
                            raise UpdateFailed("OAuth token refresh failed") from err

                    data = await self.process_emails(self.hass, config)
                except UpdateFailed:
                    raise
                except Exception as error:
                    _LOGGER.error("Problem updating sensors: %s", error)
                    raise UpdateFailed(error) from error

                if data:
                    self._data = data
                    await self._binary_sensor_update()
                return self._data
        except TimeoutError:
            _LOGGER.error(
                "Mail and Packages scan exceeded its %.0fs time budget (elapsed %.1fs). "
                "This budget covers the ENTIRE scan (login plus every per-carrier IMAP "
                "search), not just connecting. Increase the scan time limit in the "
                "integration options, or reduce the mailbox size searched (use a "
                "dedicated folder), the days-back window, or the number of enabled "
                "carriers.",
                self.timeout,
                monotonic() - start,
            )
            raise

    async def process_emails(self, hass: HomeAssistant, config: dict) -> dict:
        """Process emails and update sensors."""
        # Initialize defaults and image paths
        data = self._initialize_data()
        config = await self._setup_image_config(hass, config)

        # Connect to IMAP
        account = await self._get_imap_connection(config)
        try:
            cache = EmailCache(account)
            now = datetime.datetime.now()
            today = now.strftime("%d-%b-%Y")
            today_iso = now.date().isoformat()
            days = config.get(CONF_CUSTOM_DAYS, DEFAULT_CUSTOM_DAYS)
            since_date = (now - datetime.timedelta(days=days)).strftime("%d-%b-%Y")

            # Load persisted tracking state on first scan after startup
            if not self._tracking_loaded:
                await self._async_load_tracking()
                self._tracking_loaded = True

            # Process logic
            shipper_data, account = await self._update_shippers(
                account, config, today, since_date, cache
            )
            # When a 17track API key is configured, use only the status data
            # that 17track produced (keyed as _17track_details). This prevents
            # email-based status classifications from conflicting with the
            # authoritative 17track status. Without an API key the existing
            # email-based _tracking_details are used as before.
            if config.get(const.CONF_17TRACK_API_KEY):
                tracking_details = shipper_data.pop("_17track_details", {})
                shipper_data.pop("_tracking_details", None)
            else:
                tracking_details = shipper_data.pop("_tracking_details", {})
            data.update(shipper_data)
            self._apply_tracking_state(data, tracking_details, today_iso)

            # Persist updated tracking state so it survives restarts
            await self._async_save_tracking()

            # Aggregate global transit and delivered sensors
            self._aggregate_package_counts(data)
        finally:
            await logout(account)

        # Fetch DHL Briefankündigung (letter previews) if configured
        if config.get(CONF_DHL_BRIEF_ENABLED):
            await self._fetch_dhl_brief(hass, data)

        # Post-process external images
        if config.get(CONF_ALLOW_EXTERNAL):
            try:
                await hass.async_add_executor_job(copy_images, hass, config)
            except (OSError, ValueError) as err:
                _LOGGER.error("Problem creating: %s", err)

        return data

    def _initialize_data(self) -> dict:
        """Initialize core data structure with default values."""
        data = {
            "mail_updated": datetime.datetime.now(datetime.UTC).isoformat(),
            "amazon_delivered_by_others": 0,
        }
        for sensor in const.SENSOR_TYPES:
            if sensor not in data:
                data[sensor] = 0
        # DHL brief sensors start as None (no letters yet) rather than 0
        data["dhl_brief_naechster"] = None
        data["dhl_brief_letters"] = []
        return data

    async def _setup_image_config(self, hass: HomeAssistant, config: dict) -> dict:
        """Configure image paths and filenames for all shippers."""
        image_path = default_image_path(hass, config)
        config["image_path"] = image_path

        shipper_images = {
            "amazon_image": (True, False, False, False),
            "ups_image": (False, True, False, False),
            "walmart_image": (False, False, True, False),
            "fedex_image": (False, False, False, True),
            "usps_image": (False, False, False, False),
        }

        for key, params in shipper_images.items():
            config[key] = await hass.async_add_executor_job(
                image_file_name, hass, config, *params
            )
        return config

    async def _get_imap_connection(self, config: dict) -> IMAP4_SSL:
        """Establish and return an authenticated IMAP connection."""
        try:
            account = await login(
                self.hass,
                config.get(CONF_HOST),
                config.get(CONF_PORT),
                config.get(CONF_USERNAME),
                config.get(CONF_PASSWORD),
                config.get(CONF_IMAP_SECURITY),
                config.get(CONF_VERIFY_SSL),
                config.get("oauth_token"),
                timeout=self.timeout,
            )
        except InvalidAuth as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            _LOGGER.error("Error logging into IMAP: %s", err)
            raise UpdateFailed(f"Login failed: {err}") from err

        # Stashed so utils.imap can transparently reconnect if a command
        # stalls mid-scan (observed against Exchange Online: a connection
        # stops responding to further commands after enough have been
        # issued, regardless of pacing between them).
        account._login_kwargs = {  # noqa: SLF001
            "host": config.get(CONF_HOST),
            "port": config.get(CONF_PORT),
            "user": config.get(CONF_USERNAME),
            "pwd": config.get(CONF_PASSWORD),
            "security": config.get(CONF_IMAP_SECURITY),
            "verify": config.get(CONF_VERIFY_SSL),
            "oauth_token": config.get("oauth_token"),
            "timeout": self.timeout,
        }
        account._hass = self.hass  # noqa: SLF001

        folders = config.get(CONF_FOLDER)
        if not folders:
            folders = ["INBOX"]
        elif isinstance(folders, str):
            folders = [folders]
        elif isinstance(folders, (list, tuple, set)):
            folders = [f for f in folders if isinstance(f, str) and f]
            if not folders:
                folders = ["INBOX"]
        else:
            folders = ["INBOX"]
        account._folders = folders  # noqa: SLF001
        account._current_folder = None  # noqa: SLF001

        if folders:
            try:
                folder_ok = await selectfolder(account, folders[0])
            except Exception as err:
                await logout(account)
                raise UpdateFailed(f"Folder selection failed: {err}") from err

            if not folder_ok:
                _LOGGER.error("Error selecting folder: %s", folders[0])
                await logout(account)
                raise UpdateFailed(f"Folder selection failed: {folders[0]}")

        return account

    async def _prefetch_imap_searches(
        self,
        account: IMAP4_SSL,
        sensors_by_shipper: dict,
        today: str,
        since_date: str,
    ) -> IMAP4_SSL:
        """Collect all IMAP queries from all shippers and batch-execute per folder.

        This ensures each IMAP folder is SELECTed exactly once for the entire
        scan instead of once per sensor, cutting SELECT round-trips from
        N_sensors × N_folders down to N_folders.

        Returns the account to use for the rest of the scan -- batch_search_folders
        may return a new connection object if a stalled command forced a reconnect.
        """
        all_queries: list[QuerySpec] = []
        for shipper_group in sensors_by_shipper.values():
            shipper_instance = shipper_group[0][0]
            sensors = [s[1] for s in shipper_group]
            if hasattr(shipper_instance, "collect_queries"):
                try:
                    all_queries.extend(
                        shipper_instance.collect_queries(
                            account, today, sensors, since_date
                        )
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Could not collect queries for pre-fetch: %s", err)

        if all_queries:
            n_folders = len(getattr(account, "_folders", ["INBOX"]))
            n_unique = len({spec.query for spec in all_queries})
            _LOGGER.debug(
                "Pre-fetching %d unique queries across %d folder(s) "
                "(%d total before dedup) via one broad search per folder",
                n_unique,
                n_folders,
                len(all_queries),
            )
            prefetch_start = monotonic()
            account = await batch_search_folders(account, all_queries)
            _LOGGER.debug(
                "Pre-fetch complete in %.1fs (%d broad SEARCHes + batched FETCHes)",
                monotonic() - prefetch_start,
                n_folders,
            )
        return account

    async def _update_shippers(
        self,
        account: IMAP4_SSL,
        config: dict,
        today: str,
        since_date: str,
        cache: EmailCache,
    ) -> tuple[dict, IMAP4_SSL]:
        """Group and process sensors by shipper.

        Returns (data, account) -- the account may be a new connection object
        if pre-fetch had to reconnect after a stalled command; the cache is
        re-pointed at it so subsequent fetches don't use the dead connection.
        """
        data = {}
        amazon_enabled = config.get(const.CONF_AMAZON_ENABLED, False)
        sensors_by_shipper: dict[str, list[tuple]] = {}

        for sensor in const.SENSOR_TYPES:
            if not amazon_enabled and sensor.startswith("amazon_"):
                continue
            shipper = get_shipper_for_sensor(self.hass, config, sensor)
            if shipper:
                sensors_by_shipper.setdefault(shipper.name, []).append(
                    (shipper, sensor)
                )

        account = await self._prefetch_imap_searches(
            account, sensors_by_shipper, today, since_date
        )
        cache.account = account

        for shipper_name, shipper_group in sensors_by_shipper.items():
            shipper_instance = shipper_group[0][0]
            sensors = [s[1] for s in shipper_group]

            shipper_start = monotonic()
            success = False
            try:
                results = await shipper_instance.process_batch(
                    account, today, sensors, cache, since_date=since_date
                )
                if isinstance(results, dict):
                    data.update(results)
                success = True
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Error processing shipper %s: %s", shipper_name, err)
            finally:
                _LOGGER.debug(
                    "Shipper %s %s in %.1fs",
                    shipper_name,
                    "processed" if success else "failed",
                    monotonic() - shipper_start,
                )

        return data, account

    def _apply_tracking_state(
        self,
        data: dict,
        tracking_details: dict[str, list[str]],
        today_iso: str,
    ) -> None:
        """Update in-transit tracking state and override sensor counts."""
        prefixes: set[str] = set()
        for sensor_key in tracking_details:
            prefix = "_".join(sensor_key.split("_")[:-1])
            if prefix:
                prefixes.add(prefix)

        for prefix in prefixes:
            delivering = list(tracking_details.get(f"{prefix}_delivering", []))
            delivering += list(tracking_details.get(f"{prefix}_exception", []))
            delivered = list(tracking_details.get(f"{prefix}_delivered", []))

            self._update_tracking_for_prefix(
                prefix, delivering, delivered, today_iso, MAX_TRACKING_AGE_DAYS
            )

            in_transit = self._in_transit_tracking.get(prefix, {})
            if in_transit:
                data[f"{prefix}_tracking"] = list(in_transit.keys())
                data[f"{prefix}_delivering"] = len(in_transit)
                delivered_count = data.get(f"{prefix}_delivered", 0)
                data[f"{prefix}_packages"] = len(in_transit) + (
                    delivered_count if isinstance(delivered_count, int) else 0
                )

    def _update_tracking_for_prefix(
        self,
        prefix: str,
        delivering: list[str],
        delivered: list[str],
        today_iso: str,
        ttl_days: int,
    ) -> None:
        """Add/expire delivering tracking numbers and remove delivered ones."""
        if prefix not in self._in_transit_tracking:
            self._in_transit_tracking[prefix] = {}

        in_transit = self._in_transit_tracking[prefix]

        # Add new delivering tracking numbers (record first-seen date)
        for tid in delivering:
            if tid and tid not in in_transit:
                in_transit[tid] = today_iso

        # Remove delivered tracking numbers
        for tid in delivered:
            in_transit.pop(tid, None)

        # Expire entries older than TTL
        cutoff = (
            datetime.date.fromisoformat(today_iso) - datetime.timedelta(days=ttl_days)
        ).isoformat()
        expired = [tid for tid, seen in in_transit.items() if seen < cutoff]
        for tid in expired:
            del in_transit[tid]

    async def _async_load_tracking(self) -> None:
        """Load persisted in-transit tracking state from storage."""
        stored = await self._store.async_load()
        if stored and isinstance(stored.get("in_transit"), dict):
            self._in_transit_tracking = stored["in_transit"]
            _LOGGER.debug(
                "Loaded %d tracked prefix(es) from storage",
                len(self._in_transit_tracking),
            )

    async def _async_save_tracking(self) -> None:
        """Persist current in-transit tracking state to storage."""
        await self._store.async_save({"in_transit": self._in_transit_tracking})

    def _aggregate_package_counts(self, data: dict) -> None:
        """Aggregate global transit and delivered counts from all shippers."""
        # Only update if sensors were requested in initialize_data
        if "zpackages_transit" in data:
            data["zpackages_transit"] = self._sum_transit_counts(data)
        if "zpackages_delivered" in data:
            data["zpackages_delivered"] = self._sum_delivered_counts(data)

    def _sum_delivered_counts(self, data: dict) -> int:
        """Sum delivered packages from all shippers."""
        delivered = 0
        exclude_keys = (
            "zpackages_delivered",
            "amazon_delivered_by_others",
            "usps_mail_delivered",
        )

        for key, value in data.items():
            if (
                isinstance(value, int)
                and value > 0
                and key.endswith("_delivered")
                and key not in exclude_keys
            ):
                delivered += value
        return delivered

    def _sum_transit_counts(self, data: dict) -> int:
        """Sum transit and exception packages from all shippers."""
        transit = 0
        shippers_counted = set()

        # Amazon is special as it uses amazon_packages for total arriving
        if data.get("amazon_packages", 0) > 0:
            transit += data["amazon_packages"]
            shippers_counted.add("amazon")

        for key, value in data.items():
            if not isinstance(value, int) or value <= 0:
                continue

            # Add exceptions for all shippers
            if key.endswith("_exception") and key != "zpackages_exception":
                transit += value
                continue

            # Match shipper prefix
            shipper = next((s for s in const.SHIPPERS if key.startswith(s)), None)
            if not shipper or shipper in shippers_counted:
                continue

            # Priority: _delivering (preferred generic state) or _packages
            if key.endswith(("_delivering", "_packages")):
                transit += value
                shippers_counted.add(shipper)

        return transit

    async def _fetch_dhl_brief(self, hass: HomeAssistant, data: dict) -> None:
        """Fetch DHL Briefankündigung letters and update data dict."""
        if not self.config_entry:
            return

        tokens = self.config_entry.data.get(CONF_DHL_BRIEF_TOKENS)
        if not tokens:
            _LOGGER.warning("DHL Briefankündigung: keine Tokens gespeichert")
            return

        client = DHLBriefankundigungClient(hass, tokens)
        letters = await client.fetch_letters()

        if not letters:
            data["dhl_brief_anzahl"] = 0
            data["dhl_brief_naechster"] = None
            data["dhl_brief_letters"] = []
            return

        # Image storage: <ha_config>/www/mail_and_packages/dhl_letters/
        letters_dir = (
            Path(hass.config.path()) / "www" / "mail_and_packages" / "dhl_letters"
        )

        letter_details: list[dict] = []
        earliest_date: datetime.date | None = None

        for letter in letters:
            letter_id = str(letter.get("id", letter.get("adviceId", "")))
            # Normalize the planned delivery date across possible field names
            raw_date = (
                letter.get("plannedDeliveryDate")
                or letter.get("deliveryDate")
                or letter.get("date")
                or letter.get("expectedDelivery")
            )
            letter_date: datetime.date | None = None
            if raw_date:
                try:
                    letter_date = datetime.date.fromisoformat(str(raw_date)[:10])
                    if earliest_date is None or letter_date < earliest_date:
                        earliest_date = letter_date
                except ValueError:
                    pass

            image_url = (
                letter.get("imageUrl")
                or letter.get("image_url")
                or letter.get("previewUrl")
            )
            image_path: str | None = None
            if image_url and letter_id:
                save_path = str(letters_dir / f"{letter_id}.jpg")
                image_path = await client.fetch_and_decrypt_image(image_url, save_path)

            letter_details.append(
                {
                    "id": letter_id,
                    "date": raw_date,
                    "image_path": image_path,
                }
            )

        data["dhl_brief_anzahl"] = len(letters)
        data["dhl_brief_naechster"] = earliest_date
        data["dhl_brief_letters"] = letter_details

        # Persist refreshed tokens if they changed
        if client.tokens != tokens:
            new_entry_data = dict(self.config_entry.data)
            new_entry_data[CONF_DHL_BRIEF_TOKENS] = client.tokens
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_entry_data
            )

    async def _binary_sensor_update(self):
        """Update binary sensor states."""
        # USPS uses ATTR_USPS_IMAGE instead of the old ATTR_IMAGE_NAME
        _LOGGER.debug("Data: %s", self._data)
        image = self._data.get(ATTR_USPS_IMAGE)
        if image:
            path = default_image_path(self.hass, self.config)
            usps_image = f"{path}/{image}"
            usps_none = f"{Path(__file__).parent}/mail_none.gif"
            usps_check = await anyio.Path(usps_image).exists()
            _LOGGER.debug("USPS Check: %s", usps_check)
            if usps_check:
                # Optimized: Use _get_file_hash_if_changed
                image_hash = await self._get_file_hash_if_changed(usps_image)
                none_hash = await self._get_file_hash_if_changed(usps_none)

                _LOGGER.debug("USPS Image hash: %s", image_hash)
                _LOGGER.debug("USPS None hash: %s", none_hash)

                if image_hash != none_hash:
                    self._data["usps_update"] = True
                else:
                    self._data["usps_update"] = False

        # Handle generic delivery cameras (Amazon, UPS, Walmart, FedEx, Generic) with unified logic
        # Derive camera list dynamically from CAMERA_DATA, excluding usps_camera and generic_camera
        delivery_cameras = [
            camera_type.replace("_camera", "")
            for camera_type in const.CAMERA_DATA
            if camera_type not in ("usps_camera", "generic_camera")
        ]

        for base_name in delivery_cameras:
            # Derive attribute and config keys dynamically
            image_attr_name = f"ATTR_{base_name.upper()}_IMAGE"
            image_attr = getattr(const, image_attr_name, None)
            if not image_attr:
                continue

            custom_img_key = getattr(
                const,
                f"CONF_{base_name.upper()}_CUSTOM_IMG",
                None,
            )
            custom_img_file_key = getattr(
                const,
                f"CONF_{base_name.upper()}_CUSTOM_IMG_FILE",
                None,
            )
            update_key = f"{base_name}_update"

            image = self._data.get(image_attr)
            _LOGGER.debug("%s image from data: %s", base_name.title(), image)
            if image:
                # Normalize path to avoid double slashes
                image_path = (
                    default_image_path(self.hass, self.config).rstrip("/") + "/"
                )
                path = f"{image_path}{base_name}/"
                # Use absolute path for file existence check
                delivery_image_relative = f"{path}{image}"
                delivery_image = f"{self.hass.config.path()}/{delivery_image_relative}"
                _LOGGER.debug(
                    "Full %s image path: %s",
                    base_name.title(),
                    delivery_image,
                )

                if custom_img_key and self.config.get(custom_img_key):
                    none_image = self.config.get(custom_img_file_key)
                else:
                    none_image = (
                        f"{Path(__file__).parent}/no_deliveries_{base_name}.jpg"
                    )

                image_check = await anyio.Path(delivery_image).exists()
                _LOGGER.debug("%s Check: %s", base_name.title(), image_check)
                if image_check:
                    # Optimized: Use _get_file_hash_if_changed
                    image_hash = await self._get_file_hash_if_changed(delivery_image)
                    none_hash = await self._get_file_hash_if_changed(none_image)

                    _LOGGER.debug("%s Image hash: %s", base_name.title(), image_hash)
                    _LOGGER.debug("%s None hash: %s", base_name.title(), none_hash)

                    if image_hash != none_hash:
                        self._data[update_key] = True
                    else:
                        self._data[update_key] = False
