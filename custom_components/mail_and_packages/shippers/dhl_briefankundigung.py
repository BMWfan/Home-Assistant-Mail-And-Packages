"""DHL Briefankündigung (letter preview) API client."""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

_TOKEN_URL = "https://login.dhl.de/af5f9bb6-27ad-4af4-9445-008e7a5cddb8/login/token"
# NOTE: the app uses /login/authorize -- the standards-looking
# /login/oauth2/v2.0/authorize path is blocked by DHL's API gateway with a
# blanket 403 ("Requested endpoint is forbidden"), verified live. URL shape
# (path, scope, state/claims/prompt params) mirrors what the Post & DHL app
# sends, as documented by the ioBroker.parcel adapter.
_AUTH_URL = "https://login.dhl.de/af5f9bb6-27ad-4af4-9445-008e7a5cddb8/login/authorize"
_ADVICES_URL = "https://www.dhl.de/int-aviseanzeigen/advices"
_CLIENT_ID = "83471082-5c13-4fce-8dcb-19d2a3fca413"
_CLIENT_BASIC_AUTH = "Basic ODM0NzEwODItNWMxMy00ZmNlLThkY2ItMTlkMmEzZmNhNDEzOg=="
_CODE_VERIFIER = "zmVs5AKfGvv45a9aUvuOid9a_erOirp7XL1sn9kWT_o"
_REDIRECT_URI = "dhllogin://de.deutschepost.dhl/login"

# DHL's login/token endpoint sits behind Akamai bot protection and rejects
# requests that don't look like the Post & DHL app -- aiohttp's default
# Python-aiohttp User-Agent gets a generic "invalid" back. This is the exact
# UA the app (and the working ioBroker.parcel adapter) sends.
_APP_USER_AGENT = "DHLPaket_PROD/1367 CFNetwork/1240.0.4 Darwin/20.6.0"

# Opaque state blob the app sends; the login UI expects it to be present.
_AUTH_STATE = "eyJycyI6dHJ1ZSwicnYiOmZhbHNlLCJmaWQiOiJhcHAtbG9naW4tbWVoci1mb290ZXIiLCJoaWQiOiJhcHAtbG9naW4tbWVoci1oZWFkZXIiLCJycCI6ZmFsc2V9"
_AUTH_CLAIMS = (
    '{"id_token":{"email":null,"post_number":null,"twofa":null,'
    '"service_mask":null,"deactivate_account":null,"last_login":null,'
    '"customer_type":null,"display_name":null,'
    '"data_confirmation_required":null}}'
)


def get_auth_url() -> str:
    """Return the DHL OAuth2 PKCE authorization URL."""
    verifier_bytes = _CODE_VERIFIER.encode()
    digest = hashlib.sha256(verifier_bytes).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    params = {
        "redirect_uri": _REDIRECT_URI,
        "state": _AUTH_STATE,
        "client_id": _CLIENT_ID,
        "response_type": "code",
        "scope": "openid offline_access",
        "claims": _AUTH_CLAIMS,
        "nonce": "",
        "login_hint": "",
        "prompt": "login",
        "ui_locales": "de-DE",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return _AUTH_URL + "?" + urlencode(params)


def extract_code(raw: str) -> str:
    """Extract the authorization code from a raw code or full redirect URL."""
    raw = raw.strip()
    if raw.startswith(("dhllogin://", "http")):
        parsed = urlparse(raw)
        params = parse_qs(parsed.query)
        codes = params.get("code")
        if codes:
            return codes[0]
    return raw


async def exchange_code(hass: HomeAssistant, code: str) -> dict:
    """Exchange an authorization code for DHL tokens."""
    session = async_get_clientsession(hass)
    # client_id is intentionally NOT in the body: the client is already
    # authenticated via the Basic auth header, and DHL rejects specifying it
    # both ways with HTTP 400 "cannot specify authorization in multiple ways".
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _REDIRECT_URI,
        "code_verifier": _CODE_VERIFIER,
    }
    headers = {
        "Authorization": _CLIENT_BASIC_AUTH,
        "User-Agent": _APP_USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    async with session.post(_TOKEN_URL, data=data, headers=headers) as resp:
        if resp.status != 200:
            body = await resp.text()
            _LOGGER.error(
                "DHL Briefankündigung: Token-Austausch fehlgeschlagen (HTTP %s): %s",
                resp.status,
                body[:500],
            )
            resp.raise_for_status()
        tokens: dict = await resp.json(content_type=None)
        tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
        return tokens


class DHLBriefankundigungClient:
    """Client for the DHL Briefankündigung (letter preview) API."""

    def __init__(self, hass: HomeAssistant, tokens: dict) -> None:
        """Initialize with existing tokens."""
        self._hass = hass
        self._tokens: dict = dict(tokens)

    @property
    def tokens(self) -> dict:
        """Return current tokens so the caller can persist any refresh."""
        return self._tokens

    async def _ensure_token_valid(self) -> str:
        """Return a valid id_token, refreshing if it expires within 60 s."""
        if time.time() >= self._tokens.get("expires_at", 0) - 60:
            await self._refresh()
        return self._tokens.get("id_token", "")

    async def _refresh(self) -> None:
        """Refresh access and id tokens using the stored refresh token."""
        refresh_token = self._tokens.get("refresh_token")
        if not refresh_token:
            _LOGGER.error("DHL Briefankündigung: kein Refresh-Token vorhanden")
            return
        session = async_get_clientsession(self._hass)
        # client_id omitted from the body on purpose -- see exchange_code.
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {
            "Authorization": _CLIENT_BASIC_AUTH,
            "User-Agent": _APP_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with session.post(_TOKEN_URL, data=data, headers=headers) as resp:
                resp.raise_for_status()
                new_tokens: dict = await resp.json(content_type=None)
                new_tokens["expires_at"] = time.time() + new_tokens.get(
                    "expires_in", 3600
                )
                self._tokens.update(new_tokens)
                _LOGGER.debug("DHL Briefankündigung: Token erfolgreich erneuert")
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("DHL Briefankündigung Token-Refresh fehlgeschlagen: %s", err)

    async def fetch_letters(self) -> list[dict]:
        """Fetch letter announcements from the DHL advices API."""
        id_token = await self._ensure_token_valid()
        if not id_token:
            return []

        session = async_get_clientsession(self._hass)
        headers = {
            "Cookie": f"dhli={id_token}",
            "Accept": "application/json",
            "User-Agent": _APP_USER_AGENT,
        }
        try:
            async with session.get(
                _ADVICES_URL, params={"width": "414"}, headers=headers
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("DHL Briefankündigung: Abruf fehlgeschlagen: %s", err)
            return []

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("advices", data.get("items", []))
        return []

    async def fetch_and_decrypt_image(
        self, image_url: str, save_path: str
    ) -> str | None:
        """Download, decrypt, and save a DHL letter preview image.

        Returns the saved file path on success, None on failure.
        """
        session = async_get_clientsession(self._hass)
        try:
            async with session.get(image_url) as resp:
                resp.raise_for_status()
                encrypted_data = await resp.read()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "DHL Briefankündigung: Bild-Download fehlgeschlagen (%s): %s",
                image_url,
                err,
            )
            return None

        filename = image_url.rsplit("/", 1)[-1].split("?", maxsplit=1)[0]
        try:
            decrypted = await self._hass.async_add_executor_job(
                _decrypt_image, encrypted_data, filename
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error(
                "DHL Briefankündigung: Entschlüsselung fehlgeschlagen (%s): %s",
                filename,
                err,
            )
            return None

        try:
            await self._hass.async_add_executor_job(
                _write_file, Path(save_path), decrypted
            )
        except OSError as err:
            _LOGGER.error(
                "DHL Briefankündigung: Bild-Speicherung fehlgeschlagen (%s): %s",
                save_path,
                err,
            )
            return None

        return save_path


def _write_file(path: Path, data: bytes) -> None:
    """Write bytes to path, creating parent directories (runs in executor)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _decrypt_image(encrypted_data: bytes, filename: str) -> bytes:
    """Decrypt an AES-256-GCM encrypted DHL letter image.

    Key material is derived from SHA-512 of the filename:
      key  = digest[0:32]
      IV   = digest[32:44]  (12 bytes – GCM nonce)
      AAD  = digest[44:56]
    The last 16 bytes of encrypted_data are the GCM auth tag.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415

    key_material = hashlib.sha512(filename.encode()).digest()
    key = key_material[:32]
    nonce = key_material[32:44]
    aad = key_material[44:56]

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, encrypted_data, aad)
