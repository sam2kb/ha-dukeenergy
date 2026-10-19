"""Tests for Duke Energy config entry diagnostics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.duke_energy.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_token_material(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Tokens and account identifiers never reach the diagnostics dump."""
    mock_config_entry.runtime_data = SimpleNamespace(
        status="complete",
        last_poll_time=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        next_poll_time=None,
        account_info={"acct-1": "0001"},
        meter_info={"serial-1": SimpleNamespace(service_type="ELECTRIC")},
        meter_last_updated={"serial-1": datetime(2026, 10, 19, 11, 0, tzinfo=UTC)},
        statistic_ids={"duke_energy:electric_serial-1_energy_consumption"},
    )

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    dump = json.dumps(result)

    assert "test-access-token" not in dump
    assert "test-refresh-token" not in dump
    assert "test-user-id" not in dump
    assert "test@example.com" not in dump
    assert result["coordinator"]["status"] == "complete"
    assert result["coordinator"]["last_poll"] == "2026-10-19T12:00:00+00:00"
    assert result["coordinator"]["meters"]["serial-1"] == {
        "service_type": "ELECTRIC",
        "last_updated": "2026-10-19T11:00:00+00:00",
    }
    assert result["coordinator"]["statistic_ids"] == [
        "duke_energy:electric_serial-1_energy_consumption"
    ]


async def test_diagnostics_without_coordinator(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A failed setup still produces a redacted dump."""
    mock_config_entry.runtime_data = None

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["coordinator"] is None
    assert result["entry"]["data"]["token"] == "**REDACTED**"
