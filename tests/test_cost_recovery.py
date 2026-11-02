"""Cost recovery uses committed consumption without refreshing Duke."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.util import dt as dt_util

from custom_components.duke_energy.coordinator import DukeEnergyCoordinator, MeterInfo


async def test_cost_catches_up_older_than_duke_fetch_window(
    hass, mock_config_entry, mock_api_with_meters, stats_store
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={"cost_meters": {"123": {"mode": "static", "price": 0.2}}},
    )
    reading = next(iter(mock_api_with_meters.get_energy_usage.return_value["data"]))
    old = reading - timedelta(days=90)
    stats_store.seed(
        "duke_energy:electric_123_energy_consumption",
        [
            {"start": old, "state": 1.0, "sum": 1.0},
            {"start": old + timedelta(hours=1), "state": 2.0, "sum": 3.0},
        ],
    )
    stats_store.seed(
        "duke_energy:electric_123_energy_cost",
        [{"start": old, "state": 0.1, "sum": 0.1}],
    )
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    rows = stats_store.data["duke_energy:electric_123_energy_cost"]
    assert [row["state"] for row in rows] == pytest.approx([0.1, 0.4, 0.26])
    assert [row["sum"] for row in rows] == pytest.approx([0.1, 0.5, 0.76])


async def test_cost_retries_after_price_recovers_even_when_duke_day_is_complete(
    hass, mock_config_entry, mock_api_with_meters, stats_store
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            "cost_meters": {"123": {"mode": "sensor", "entity_id": "sensor.rate"}}
        },
    )
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    await coordinator.async_refresh()
    assert "duke_energy:electric_123_energy_cost" not in stats_store.data
    assert coordinator._last_successful_date is not None
    mock_api_with_meters.reset_mock()
    hass.states.async_set("sensor.rate", "0.2")
    await coordinator.async_refresh()
    rows = stats_store.data["duke_energy:electric_123_energy_cost"]
    assert [row["sum"] for row in rows] == pytest.approx([0.26])
    mock_api_with_meters.get_meters.assert_not_awaited()
    mock_api_with_meters.get_energy_usage.assert_not_awaited()
    mock_api_with_meters.get_monthly_usage.assert_not_awaited()


async def test_explicit_rebuild_preserves_consumption_temperature_and_gas_starts(
    hass, mock_config_entry, mock_api_with_meters, stats_store
):
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    coordinator.meter_info = {
        "123": MeterInfo("ELECTRIC", "account1"),
        "456": MeterInfo("GAS", "account2"),
    }
    # Stored history can predate Duke's retention and the old four-year query.
    start = datetime(2020, 1, 1, tzinfo=ZoneInfo("America/New_York"))
    for prefix, offset in [("electric_123", 0), ("gas_456", 12)]:
        stats_store.seed(
            f"duke_energy:{prefix}_energy_consumption",
            [{"start": start + timedelta(hours=offset), "state": 2.0, "sum": 2.0}],
        )
        stats_store.seed(
            f"duke_energy:{prefix}_energy_cost",
            [{"start": start + timedelta(hours=offset), "state": 8.0, "sum": 8.0}],
        )
    stats_store.seed(
        "duke_energy:account_account1_temperature",
        [{"start": start, "mean": 70.0}],
    )
    original = deepcopy(stats_store.data)
    await coordinator.async_rebuild_costs(
        {
            "123": {"mode": "static", "price": 0.15},
            "456": {"mode": "static", "price": 0.5},
        }
    )
    for statistic_id, rows in original.items():
        if not statistic_id.endswith("_energy_cost"):
            assert stats_store.data[statistic_id] == rows
    for prefix, price in [("electric_123", 0.15), ("gas_456", 0.5)]:
        rows = stats_store.data[f"duke_energy:{prefix}_energy_cost"]
        assert len(rows) == 1
        assert rows[0]["sum"] == pytest.approx(2 * price)
        assert (
            rows[0]["start"]
            == original[f"duke_energy:{prefix}_energy_cost"][0]["start"]
        )
    assert mock_api_with_meters.mock_calls == []


async def test_concurrent_catchups_wait_for_committed_cost_sum(
    hass, mock_config_entry, mock_api_with_meters, stats_store
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={"cost_meters": {"123": {"mode": "static", "price": 0.2}}},
    )
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    coordinator.meter_info = {"123": MeterInfo("ELECTRIC", "account1")}
    start = datetime(2026, 7, 1, tzinfo=ZoneInfo("America/New_York"))
    stats_store.seed(
        "duke_energy:electric_123_energy_consumption",
        [{"start": start, "state": 2.0, "sum": 2.0}],
    )
    pending = []
    stats_store.mock_add.side_effect = lambda *args: pending.append(args)

    def commit(task):
        while pending:
            stats_store.add_external(*pending.pop(0))
        task.future.set_result(None)

    stats_store.recorder.queue_task.side_effect = commit
    await asyncio.gather(
        coordinator._async_update_costs(), coordinator._async_update_costs()
    )
    assert stats_store.mock_add.call_count == 1
    assert stats_store.data["duke_energy:electric_123_energy_cost"][0]["sum"] == 0.4


@pytest.mark.parametrize(
    "service,interval,offset", [("ELECTRIC", "HOURLY", 0), ("GAS", "DAILY", 12)]
)
@pytest.mark.freeze_time("2026-07-04T16:00:00Z")
async def test_cost_reads_committed_consumption_on_first_import(
    recorder_mock,
    hass,
    mock_config_entry,
    mock_api_with_meters,
    coordinator_cleanup,
    service,
    interval,
    offset,
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={"cost_meters": {"123": {"mode": "static", "price": 0.2}}},
    )
    meter = mock_api_with_meters.get_meters.return_value["123"]
    meter["serviceType"] = service
    meter["account"]["srcAcctId"] = "account1"
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    start = datetime(2026, 7, 3, tzinfo=ZoneInfo("America/New_York"))
    usage = {start: {"energy": 2.0, "temperature": None}}
    with patch.object(
        coordinator, "_async_get_energy_usage", return_value=(usage, interval)
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done(wait_background_tasks=True)
    assert coordinator.last_update_success
    cost_id = f"duke_energy:{service.lower()}_123_energy_cost"
    first = await recorder_mock.async_add_executor_job(
        statistics_during_period, hass, start, None, {cost_id}, "hour", None, {"sum"}
    )
    assert [row["sum"] for row in first[cost_id]] == pytest.approx([0.4])
    mock_api_with_meters.reset_mock()
    await coordinator.async_rebuild_costs({"123": {"mode": "static", "price": 0.3}})
    rows = await recorder_mock.async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        None,
        {cost_id},
        "hour",
        None,
        {"state", "sum"},
    )
    assert len(rows[cost_id]) == 1
    assert rows[cost_id][0]["state"] == pytest.approx(0.6)
    assert rows[cost_id][0]["sum"] == pytest.approx(0.6)
    assert rows[cost_id][0]["start"] == (start + timedelta(hours=offset)).timestamp()
    mock_api_with_meters.get_meters.assert_not_awaited()
    mock_api_with_meters.get_energy_usage.assert_not_awaited()


async def test_failed_explicit_rebuild_keeps_existing_costs(
    hass, mock_config_entry, mock_api_with_meters, stats_store
):
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)
    coordinator.meter_info = {"123": MeterInfo("ELECTRIC", "account1")}
    start = dt_util.utcnow() - timedelta(days=90)
    stats_store.seed(
        "duke_energy:electric_123_energy_consumption",
        [{"start": start, "state": 2.0, "sum": 2.0}],
    )
    stats_store.seed(
        "duke_energy:electric_123_energy_cost",
        [{"start": start, "state": 0.5, "sum": 0.5}],
    )
    original = deepcopy(stats_store.data)
    with pytest.raises(ValueError, match="No price history"):
        await coordinator.async_rebuild_costs(
            {"123": {"mode": "sensor", "entity_id": "sensor.unavailable"}}
        )
    assert stats_store.data == original
