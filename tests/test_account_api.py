"""Exercise account discovery and inherited requests with mocked HTTP only."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientResponseError
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from yarl import URL

from custom_components.duke_energy import DukeEnergy
from custom_components.duke_energy.api import DukeEnergyAuth

from .conftest import _make_id_token

BASE = "https://api-v2.cma.duke-energy.app"


def account_payload(*, legacy=False, explicit_ids=False):
    account = {
        "accountNumber": "0000123456",
        "primaryBpNumber" if legacy else "primaryBPNumber": "primary-test",
        "serviceAddressParsed": {"zipCode": "00000"},
    }
    if explicit_ids:
        account.update(
            srcSysCd="CUSTOM", srcAcctId="existing-source", srcAcctId2="secondary"
        )
    return {
        "relatedBpNumber" if legacy else "relatedBPNumber": "related-test",
        "accounts": [account],
    }


def meter_details(service="ELECTRIC", serial="meter-1"):
    return {
        "meterInfo": [
            {
                "serialNum": serial,
                "serviceType": service,
                "agreementActiveDate": "2020-01-01",
                "agreementEndDate": "9999-12-31",
                "meterCertificationDate": "2020-01-01",
                "isCertifiedSmartMeter": True,
            }
        ]
    }


@pytest.fixture
async def api_transport(monkeypatch):
    # Older HA test doubles omit aiohttp's status-derived `ok` property.
    monkeypatch.setattr(
        AiohttpClientMockResponse,
        "ok",
        property(lambda response: response.status < 400),
        raising=False,
    )
    transport = AiohttpClientMocker()
    async with transport.create_session(asyncio.get_running_loop()) as session:
        oauth = Mock(token={"id_token": _make_id_token()})
        oauth.async_ensure_token_valid = AsyncMock()
        auth = DukeEnergyAuth(session, oauth)
        auth.async_get_access_token = AsyncMock(return_value="fixture-duke-api-token")
        # Keep the retired route's exact failure so tests reproduce issue #5.
        transport.get(
            BASE + "/account-list",
            status=403,
            json={"message": "Invalid key=value pair in Authorization header"},
        )
        yield DukeEnergy(auth), transport


@pytest.mark.parametrize(
    "legacy,explicit_ids", [(False, False), (False, True), (True, True)]
)
async def test_account_discovery_uses_new_route_and_normalizes_fields(
    api_transport, legacy, explicit_ids
):
    client, transport = api_transport
    transport.get(
        BASE + "/account/list",
        json=account_payload(legacy=legacy, explicit_ids=explicit_ids),
    )
    transport.get(BASE + "/account-details-v2", json=meter_details())

    accounts = await client.get_accounts()
    account = accounts["0000123456"]
    assert account["srcSysCd"] == ("CUSTOM" if explicit_ids else "ISU")
    assert account["srcAcctId"] == ("existing-source" if explicit_ids else "0000123456")
    assert account["srcAcctId2"] == ("secondary" if explicit_ids else "")
    assert account["primaryBpNumber"] == "primary-test"
    details_query = transport.mock_calls[1][1].query
    assert details_query["srcSysCd"] == account["srcSysCd"]
    assert details_query["srcAcctId"] == account["srcAcctId"]
    assert details_query["primaryBpNumber"] == "primary-test"
    assert details_query["relatedBpNumber"] == "related-test"
    assert transport.mock_calls[0][1].path == "/account/list"
    assert transport.mock_calls[0][1].query["fetchFreshData"] == "true"
    assert all(
        call[3]["Authorization"] == "Bearer fixture-duke-api-token"
        for call in transport.mock_calls
    )


@pytest.mark.parametrize("empty", [None, ""])
async def test_empty_source_ids_and_legacy_bp_values_use_new_fields(
    api_transport, empty
):
    client, transport = api_transport
    payload = account_payload()
    payload["relatedBpNumber"] = empty
    payload["accounts"][0].update(
        srcSysCd=empty, srcAcctId=empty, srcAcctId2=empty, primaryBpNumber=empty
    )
    transport.get(BASE + "/account/list", json=payload)
    transport.get(BASE + "/account-details-v2", json=meter_details())
    account = (await client.get_accounts())["0000123456"]
    assert (account["srcSysCd"], account["srcAcctId"], account["srcAcctId2"]) == (
        "ISU",
        "0000123456",
        "",
    )
    assert transport.mock_calls[1][1].query["primaryBpNumber"] == "primary-test"
    assert transport.mock_calls[1][1].query["relatedBpNumber"] == "related-test"


async def test_populated_legacy_bp_numbers_take_precedence(api_transport):
    client, transport = api_transport
    payload = account_payload(legacy=True, explicit_ids=True)
    payload["relatedBPNumber"] = "do-not-use"
    payload["accounts"][0]["primaryBPNumber"] = "do-not-use"
    transport.get(BASE + "/account/list", json=payload)
    transport.get(BASE + "/account-details-v2", json=meter_details())
    await client.get_accounts()
    query = transport.mock_calls[1][1].query
    assert query["primaryBpNumber"] == "primary-test"
    assert query["relatedBpNumber"] == "related-test"


@pytest.mark.parametrize(
    "service,interval,period,series",
    [
        ("ELECTRIC", "HOURLY", "DAY", "12 AM"),
        ("GAS", "DAILY", "WEEK", "10/27/2026"),
    ],
)
async def test_new_accounts_feed_existing_usage_and_billing_methods(
    api_transport, service, interval, period, series
):
    client, transport = api_transport
    transport.get(BASE + "/account/list", json=account_payload())
    transport.get(BASE + "/account-details-v2", json=meter_details(service))
    transport.post(
        BASE + "/account/usage/graph",
        json={
            "usageArray": [{"date": series, "usage": "1.25", "temperatureAvg": "70"}]
        },
    )
    transport.post(
        BASE + "/account/usage/monthly", json={"thisPeriod": {"usage": "1.25"}}
    )
    transport.get(
        BASE + "/billing-and-payment/multi-account-payment/info-v3",
        json={"accounts": [{"accountNumber": "0000123456", "balance": 10}]},
    )

    meters = await client.get_meters()
    assert meters["meter-1"]["serviceType"] == service
    start = datetime(2026, 10, 27)
    usage = await client.get_energy_usage("meter-1", interval, period, start, start)
    assert next(iter(usage["data"].values()))["energy"] == 1.25
    await client.get_monthly_usage("meter-1", start_date=start)
    billing = await client.get_billing_payment_info()
    assert billing["0000123456"]["balance"] == 10
    bodies = [call[2] for call in transport.mock_calls if call[0].upper() == "POST"]
    assert len(bodies) == 2
    for body in bodies:
        assert body["srcSysCd"] == "ISU"
        assert body["srcAcctId"] == "0000123456"
        assert body["serviceType"] == service
    assert bodies[0]["srcAcctId2"] == ""
    assert (
        len([call for call in transport.mock_calls if call[1].path == "/account/list"])
        == 1
    )


async def test_multiple_accounts_keep_separate_source_ids_and_meter_links(
    api_transport,
):
    client, transport = api_transport
    payload = account_payload(explicit_ids=True)
    payload["accounts"].append(
        {"accountNumber": "0000654321", "primaryBPNumber": "second-bp"}
    )
    transport.get(BASE + "/account/list", json=payload)
    transport.get(
        URL(BASE + "/account-details-v2").with_query(srcAcctId="existing-source"),
        json=meter_details(),
    )
    transport.get(
        URL(BASE + "/account-details-v2").with_query(srcAcctId="0000654321"),
        json=meter_details("GAS", "meter-2"),
    )
    meters = await client.get_meters()
    assert meters["meter-1"]["account"]["srcAcctId"] == "existing-source"
    assert meters["meter-2"]["account"]["srcAcctId"] == "0000654321"
    assert meters["meter-2"]["account"]["srcAcctId2"] == ""
    assert set(meters) == {"meter-1", "meter-2"}


async def test_account_cache_and_explicit_refresh_are_preserved(api_transport):
    client, transport = api_transport
    transport.get(BASE + "/account/list", json=account_payload())
    transport.get(BASE + "/account-details-v2", json=meter_details())
    original = await client.get_accounts()
    assert await client.get_accounts() is original
    assert transport.call_count == 2
    await client.get_accounts(fresh=True)
    assert transport.call_count == 4


@pytest.mark.parametrize("status", [401, 403, 429, 503])
async def test_new_route_errors_are_not_retried_with_different_credentials(
    api_transport, status
):
    client, transport = api_transport
    transport.get(BASE + "/account/list", status=status)
    with pytest.raises(ClientResponseError) as raised:
        await client.get_accounts()
    assert raised.value.status == status
    assert transport.call_count == 1
    assert transport.mock_calls[0][1].path == "/account/list"


async def test_failed_account_refresh_keeps_previous_cache(api_transport):
    client, transport = api_transport
    transport.get(BASE + "/account/list", json=account_payload())
    transport.get(BASE + "/account-details-v2", json=meter_details())
    original = await client.get_accounts()
    transport.clear_requests()
    payload = account_payload()
    payload["accounts"].append(
        {"accountNumber": "0000654321", "primaryBPNumber": "second-bp"}
    )
    transport.get(BASE + "/account/list", json=payload)
    transport.get(
        URL(BASE + "/account-details-v2").with_query(srcAcctId="0000123456"),
        json=meter_details(),
    )
    transport.get(
        URL(BASE + "/account-details-v2").with_query(srcAcctId="0000654321"), status=503
    )
    with pytest.raises(ClientResponseError):
        await client.get_accounts(fresh=True)
    assert await client.get_accounts() is original
    assert set(original) == {"0000123456"}
