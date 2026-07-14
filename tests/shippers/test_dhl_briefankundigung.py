"""Tests for the DHL Briefankündigung API client token refresh handling."""

import base64
import hashlib
import re
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import aiohttp
import pytest

from custom_components.mail_and_packages.shippers.dhl_briefankundigung import (
    DHLBriefankundigungClient,
    exchange_code,
    generate_code_verifier,
    get_auth_url,
)

_UNRESERVED_RE = re.compile(r"^[A-Za-z0-9\-._~]+$")


def _make_hass():
    return MagicMock()


def _mock_session(status, json_data=None, text_data="", raise_exc=None):
    """Build a mock aiohttp session that returns a canned POST response."""
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text_data)
    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)
    if raise_exc is not None:
        resp.raise_for_status = MagicMock(side_effect=raise_exc)
    else:
        resp.raise_for_status = MagicMock(return_value=None)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=cm)
    return session


@pytest.mark.asyncio
async def test_refresh_400_sets_auth_failed():
    """A 400 response means the refresh token is dead -- auth_failed True."""
    hass = _make_hass()
    session = _mock_session(status=400, text_data="invalid_grant")
    client = DHLBriefankundigungClient(hass, {"refresh_token": "rt", "expires_at": 0})
    with patch(
        "custom_components.mail_and_packages.shippers.dhl_briefankundigung."
        "async_get_clientsession",
        return_value=session,
    ):
        await client._refresh()

    assert client.auth_failed is True


@pytest.mark.asyncio
async def test_refresh_503_does_not_set_auth_failed():
    """A transient 503 response must not trigger the repair flow."""
    hass = _make_hass()
    raise_exc = aiohttp.ClientResponseError(
        request_info=MagicMock(), history=(), status=503
    )
    session = _mock_session(status=503, text_data="unavailable", raise_exc=raise_exc)
    client = DHLBriefankundigungClient(hass, {"refresh_token": "rt", "expires_at": 0})
    with patch(
        "custom_components.mail_and_packages.shippers.dhl_briefankundigung."
        "async_get_clientsession",
        return_value=session,
    ):
        await client._refresh()

    assert client.auth_failed is False


def test_generate_code_verifier_unique_and_rfc_compliant():
    """Two calls yield different verifiers, both valid PKCE code_verifiers."""
    verifier1 = generate_code_verifier()
    verifier2 = generate_code_verifier()

    assert verifier1 != verifier2
    for verifier in (verifier1, verifier2):
        assert 43 <= len(verifier) <= 128
        assert _UNRESERVED_RE.match(verifier)


def _expected_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def test_get_auth_url_challenge_matches_verifier():
    """The code_challenge query param matches the independently computed value."""
    verifier = generate_code_verifier()
    url = get_auth_url(verifier)

    params = parse_qs(urlparse(url).query)
    assert params["code_challenge"][0] == _expected_challenge(verifier)
    assert params["code_challenge_method"][0] == "S256"


def test_get_auth_url_differs_per_verifier():
    """Two different verifiers must produce two different code_challenge values.

    Regression guard against re-hardcoding a single static verifier/challenge.
    """
    verifier1 = generate_code_verifier()
    verifier2 = generate_code_verifier()

    challenge1 = parse_qs(urlparse(get_auth_url(verifier1)).query)["code_challenge"][0]
    challenge2 = parse_qs(urlparse(get_auth_url(verifier2)).query)["code_challenge"][0]

    assert challenge1 != challenge2


@pytest.mark.asyncio
async def test_exchange_code_sends_given_verifier():
    """exchange_code posts the exact code_verifier passed in, in the body."""
    hass = _make_hass()
    session = _mock_session(status=200, json_data={"access_token": "at"})
    verifier = generate_code_verifier()

    with patch(
        "custom_components.mail_and_packages.shippers.dhl_briefankundigung."
        "async_get_clientsession",
        return_value=session,
    ):
        await exchange_code(hass, "auth-code", verifier)

    _, kwargs = session.post.call_args
    assert kwargs["data"]["code_verifier"] == verifier
