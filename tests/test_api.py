"""OAuth adapter failures before any Duke Energy request is sent."""

from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientResponseError
from aiodukeenergy_co import DukeEnergyAuthError

from custom_components.duke_energy.api import DukeEnergyAuth
from .conftest import _make_id_token


@pytest.mark.parametrize("status", [400, 401, 403])
async def test_rejected_refresh_is_an_auth_failure(status):
    session = Mock(token={"id_token": _make_id_token()})
    session.async_ensure_token_valid = AsyncMock(
        side_effect=ClientResponseError(Mock(), (), status=status)
    )
    auth = DukeEnergyAuth(Mock(), session)
    with pytest.raises(DukeEnergyAuthError):
        await auth.async_get_id_token()


@pytest.mark.parametrize("status", [408, 429, 503])
async def test_temporary_refresh_error_stays_retryable(status):
    failure = ClientResponseError(Mock(), (), status=status)
    session = Mock(token={"id_token": _make_id_token()})
    session.async_ensure_token_valid = AsyncMock(side_effect=failure)
    auth = DukeEnergyAuth(Mock(), session)
    with pytest.raises(ClientResponseError) as raised:
        await auth.async_get_id_token()
    assert raised.value is failure
