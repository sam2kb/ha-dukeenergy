"""API for Duke Energy bound to Home Assistant OAuth."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, override

from aiodukeenergy_co import AbstractDukeEnergyAuth, DukeEnergyAuthError
from aiodukeenergy_co import DukeEnergy as BaseDukeEnergy
from aiohttp import ClientResponseError
from yarl import URL

if TYPE_CHECKING:
    import aiohttp
    from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

_LOGGER = logging.getLogger(__name__)

_API_BASE_URL = URL("https://api-v2.cma.duke-energy.app")


class DukeEnergyAuth(AbstractDukeEnergyAuth):
    """Provide Duke Energy authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        oauth_session: OAuth2Session,
    ) -> None:
        """Initialize Duke Energy auth."""
        super().__init__(websession)
        self._oauth_session = oauth_session

        # If id_token provided, decode to populate email/internal_user_id
        if self._oauth_session.token["id_token"]:
            self._update_user_info_from_token(self._oauth_session.token["id_token"])

    async def async_get_id_token(self) -> str:
        """Return a valid ID token."""
        try:
            await self._oauth_session.async_ensure_token_valid()
        except ClientResponseError as err:
            if (
                HTTPStatus.BAD_REQUEST <= err.status < HTTPStatus.INTERNAL_SERVER_ERROR
                and err.status
                not in (HTTPStatus.REQUEST_TIMEOUT, HTTPStatus.TOO_MANY_REQUESTS)
            ):
                # Let the coordinator start HA reauthentication, including when
                # the rejected refresh happens after initial setup.
                msg = "OAuth refresh was rejected"
                raise DukeEnergyAuthError(msg) from err
            raise
        except ValueError as err:
            msg = "OAuth refresh returned an unusable ID token"
            raise DukeEnergyAuthError(msg) from err
        return self._oauth_session.token["id_token"]


class DukeEnergyClient(BaseDukeEnergy):
    """Adapt account discovery while retaining the pinned client's other APIs."""

    @override
    async def get_accounts(self, fresh: bool = False) -> dict[str, dict[str, Any]]:
        """Read the current account route and normalize its renamed fields."""
        if self._accounts and not fresh:
            return self._accounts

        # aiodukeenergy-co 1.3.0 still calls the retired account-list route.
        # Adapted from hunterjm/aiodukeenergy PR #25 by @b-v-co.
        account_list = await self._get_json(
            _API_BASE_URL.joinpath("account", "list"),
            {
                "email": self.email,
                "internalUserID": self.internal_user_id,
                "fetchFreshData": "true",
            },
        )
        related_bp = account_list.get("relatedBpNumber") or account_list.get(
            "relatedBPNumber"
        )
        accounts = {}
        for raw_account in account_list["accounts"]:
            account = dict(raw_account)
            account["srcSysCd"] = account.get("srcSysCd") or "ISU"
            account["srcAcctId"] = account.get("srcAcctId") or account["accountNumber"]
            account["srcAcctId2"] = account.get("srcAcctId2") or ""
            account["primaryBpNumber"] = account.get("primaryBpNumber") or account.get(
                "primaryBPNumber"
            )
            details = await self._get_json(
                _API_BASE_URL.joinpath("account-details-v2"),
                {
                    "email": self.email,
                    "srcSysCd": account["srcSysCd"],
                    "srcAcctId": account["srcAcctId"],
                    "primaryBpNumber": account["primaryBpNumber"],
                    "relatedBpNumber": related_bp,
                },
            )
            accounts[account["accountNumber"]] = {**account, "details": details}

        # Keep the previous cache intact if any account-details request fails.
        self._accounts = accounts
        return self._accounts
