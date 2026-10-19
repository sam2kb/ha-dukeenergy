"""Diagnostics support for the Duke Energy integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import DukeEnergyConfigEntry

_REDACTED = "**REDACTED**"
_SECRET_KEYS = frozenset({"token", "access_token", "refresh_token", "id_token"})


def _redact(value: Any) -> Any:
    """Return a copy of value with token material replaced."""
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

    diagnostics: dict[str, Any] = {
        "entry": {
            "title": _REDACTED,
            "unique_id": _REDACTED,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": _redact(dict(entry.data)),
            "options": _redact(dict(entry.options)),
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
            serial: {
                "service_type": info.service_type,
                "last_updated": _serialize(coordinator.meter_last_updated.get(serial)),
            }
            for serial, info in coordinator.meter_info.items()
        },
        "statistic_ids": sorted(coordinator.statistic_ids),
    }
    return diagnostics
