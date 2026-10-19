"""Diagnostics support for the Duke Energy integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import DukeEnergyConfigEntry

_REDACTED = "**REDACTED**"
_SECRET_KEYS = frozenset(
    {"token", "access_token", "refresh_token", "id_token", "entity_id"}
)


def _redact(value: Any) -> Any:
    """Return a copy with tokens and user-selected entity names replaced."""
    if isinstance(value, dict):
        return {
            key: _REDACTED if key in _SECRET_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _serialize(value: Any) -> Any:
    """Render dates as ISO strings so the diagnostics dump is JSON-safe."""
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant,
    entry: DukeEnergyConfigEntry,
) -> dict[str, Any]:
    """Return redacted diagnostics for a Duke Energy config entry."""
    coordinator = getattr(entry, "runtime_data", None)
    options = dict(entry.options)
    cost_meters = options.get("cost_meters", {})
    serials = set(cost_meters)
    if coordinator is not None:
        serials.update(coordinator.meter_info)
    meter_names = {
        serial: f"meter_{index}"
        for index, serial in enumerate(sorted(serials), start=1)
    }
    if "cost_meters" in options:
        options["cost_meters"] = {
            meter_names[serial]: config for serial, config in cost_meters.items()
        }

    diagnostics: dict[str, Any] = {
        "entry": {
            "title": _REDACTED,
            "unique_id": _REDACTED,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": _redact(dict(entry.data)),
            "options": _redact(options),
        },
        "coordinator": None,
    }

    if coordinator is None:
        return diagnostics

    diagnostics["coordinator"] = {
        "status": coordinator.status,
        "last_poll": _serialize(coordinator.last_poll_time),
        "next_poll": _serialize(coordinator.next_poll_time),
        "accounts": len(coordinator.account_info),
        "meters": {
            meter_names[serial]: {
                "service_type": info.service_type,
                "last_updated": _serialize(coordinator.meter_last_updated.get(serial)),
            }
            for serial, info in coordinator.meter_info.items()
        },
        # IDs embed meter serials or internal account IDs. Counts retain the
        # useful registration information without exporting those identifiers.
        "statistics": {
            kind: sum(
                statistic_id.endswith(suffix)
                for statistic_id in coordinator.statistic_ids
            )
            for kind, suffix in (
                ("consumption", "_energy_consumption"),
                ("cost", "_energy_cost"),
                ("temperature", "_temperature"),
            )
        },
    }
    return diagnostics
