"""Diagnostics support for Arctic Spa (Local)."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, decode_errors
from .coordinator import SpaCoordinator

# Fields to redact from the dump.
_REDACT = {"spa_guid", "SPASN", "TAG1", "TAG2"}


def _scrub(section: dict[str, Any]) -> dict[str, Any]:
    return {k: ("**REDACTED**" if k in _REDACT else v) for k, v in section.items()}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    return {
        "entry": {
            "host": "**REDACTED**",
            "port": entry.data.get("port"),
        },
        "connected": coordinator.client.connected,
        "last_update_success": coordinator.last_update_success,
        "active_errors": decode_errors(data.get("error")),
        "sections": {name: _scrub(section) for name, section in data.items()},
    }
