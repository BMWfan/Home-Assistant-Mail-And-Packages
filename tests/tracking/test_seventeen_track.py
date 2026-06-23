"""Tests for the 17track API client and Universal shipper 17track integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mail_and_packages.tracking.seventeen_track import (
    SeventeenTrackClient,
)


def _make_hass():
    return MagicMock()


def _mock_session(json_data=None, raise_exc=None, status=200):
    """Build a mock aiohttp session that returns json_data on POST."""
    resp = AsyncMock()
    resp.status = status
    resp.raise_for_status = MagicMock(
        side_effect=raise_exc if raise_exc and status >= 400 else None
    )
    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)

    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=cm)
    if raise_exc and status < 400:
        session.post = MagicMock(side_effect=raise_exc)
    return session


@pytest.mark.asyncio
async def test_register_calls_api():
    """register() POSTs tracking numbers to the register endpoint."""
    hass = _make_hass()
    session = _mock_session(json_data={"code": 0, "data": {}})
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        await client.register(["1Z12345E0291980793"])

    session.post.assert_called_once()
    call_kwargs = session.post.call_args
    assert "register" in call_kwargs[0][0]
    assert call_kwargs[1]["json"] == [{"number": "1Z12345E0291980793"}]


@pytest.mark.asyncio
async def test_register_empty_list_skips_api():
    """register() with an empty list makes no API call."""
    hass = _make_hass()
    session = MagicMock()
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        await client.register([])

    session.post.assert_not_called()


@pytest.mark.asyncio
async def test_get_status_batch_returns_parsed_status():
    """get_status_batch() returns a dict with status info for accepted numbers."""
    api_response = {
        "code": 0,
        "data": {
            "accepted": [
                {
                    "number": "1Z12345E0291980793",
                    "carrier": 100066,
                    "track": {
                        "e": 10,
                        "z0": {
                            "a": "In transit to destination",
                            "z": "Frankfurt, DE",
                            "d": "2024-06-20T10:00:00Z",
                        },
                    },
                }
            ],
            "rejected": [],
        },
    }
    hass = _make_hass()
    session = _mock_session(json_data=api_response)
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch(["1Z12345E0291980793"])

    assert "1Z12345E0291980793" in result
    info = result["1Z12345E0291980793"]
    assert info["status"] == "In Transit"
    assert info["status_code"] == 10
    assert info["last_location"] == "Frankfurt, DE"


@pytest.mark.asyncio
async def test_get_status_batch_delivered():
    """status_code 40 maps to 'Delivered'."""
    api_response = {
        "code": 0,
        "data": {
            "accepted": [
                {
                    "number": "123456789012",
                    "track": {
                        "e": 40,
                        "z0": {"a": "Delivered", "z": "Berlin", "d": ""},
                    },
                }
            ],
            "rejected": [],
        },
    }
    hass = _make_hass()
    session = _mock_session(json_data=api_response)
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch(["123456789012"])

    assert result["123456789012"]["status"] == "Delivered"


@pytest.mark.asyncio
async def test_get_status_batch_rejected_number():
    """Rejected tracking numbers are returned with status 'Unknown'."""
    api_response = {
        "code": 0,
        "data": {
            "accepted": [],
            "rejected": [{"number": "INVALID123", "error": {"code": -18019901}}],
        },
    }
    hass = _make_hass()
    session = _mock_session(json_data=api_response)
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch(["INVALID123"])

    assert result["INVALID123"]["status"] == "Unknown"
    assert result["INVALID123"]["status_code"] == -1


@pytest.mark.asyncio
async def test_get_status_batch_network_error_returns_empty():
    """Network errors are caught and an empty dict is returned."""
    hass = _make_hass()
    session = _mock_session(raise_exc=OSError("connection refused"))
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch(["1Z12345E0291980793"])

    assert result == {}


@pytest.mark.asyncio
async def test_get_status_batch_api_error_code_returns_empty():
    """Non-zero API code is logged and an empty dict is returned."""
    api_response = {"code": 401, "data": {}}
    hass = _make_hass()
    session = _mock_session(json_data=api_response)
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch(["1Z12345E0291980793"])

    assert result == {}


@pytest.mark.asyncio
async def test_get_status_batch_empty_list_skips_api():
    """get_status_batch() with an empty list makes no API call."""
    hass = _make_hass()
    session = MagicMock()
    with patch(
        "custom_components.mail_and_packages.tracking.seventeen_track.async_get_clientsession",
        return_value=session,
    ):
        client = SeventeenTrackClient(hass, "test-key")
        result = await client.get_status_batch([])

    session.post.assert_not_called()
    assert result == {}
