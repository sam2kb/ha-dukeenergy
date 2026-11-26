"""Setup during Home Assistant startup must not wait on the recorder queue."""

import asyncio

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState

from custom_components.duke_energy.coordinator import DukeEnergyCoordinator


@pytest.mark.parametrize("state", [CoreState.not_running, CoreState.starting])
async def test_cost_update_is_deferred_until_started(
    hass, mock_config_entry, mock_api_with_meters, stats_store, state
):
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={"cost_meters": {"123": {"mode": "static", "price": 0.2}}},
    )
    # Like the real recorder before startup finishes: queued tasks do not run.
    queued = []
    stats_store.recorder.queue_task.side_effect = queued.append
    hass.set_state(state)
    coordinator = DukeEnergyCoordinator(hass, mock_api_with_meters, mock_config_entry)

    async with asyncio.timeout(5):
        await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert "duke_energy:electric_123_energy_cost" not in stats_store.data

    stats_store.recorder.queue_task.side_effect = lambda task: (
        task.future.done() or task.future.set_result(None)
    )
    for task in queued:
        task.future.set_result(None)
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done(wait_background_tasks=True)

    rows = stats_store.data["duke_energy:electric_123_energy_cost"]
    assert [row["sum"] for row in rows] == pytest.approx([0.26])
