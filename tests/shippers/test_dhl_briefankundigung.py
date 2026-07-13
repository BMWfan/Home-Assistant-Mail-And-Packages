"""Tests for the DHL Briefankündigung API client token refresh handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.mail_and_packages.shippers.dhl_briefankundigung import (
    DHLBriefankundigungClient,
)


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
