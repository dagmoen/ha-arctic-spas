"""Switch entities for spa equipment (pumps, lights, blowers, etc.)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCHES
from .coordinator import SpaCoordinator
from .entity import SpaEntity


def _installed(coordinator: SpaCoordinator, spec: dict) -> bool:
    cfg = spec.get("cfg")
    if cfg is not None:
        flag = coordinator.get("sett", cfg)
        if flag is not None:
            return bool(flag)
    return coordinator.get("live", spec["field"]) is not None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SpaSwitch(coordinator, spec)
        for spec in SWITCHES
        if _installed(coordinator, spec)
    )


class SpaSwitch(SpaEntity, SwitchEntity):
    def __init__(self, coordinator: SpaCoordinator, spec: dict) -> None:
        super().__init__(coordinator, spec["key"])
        self._spec = spec
        self._attr_name = spec["name"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]

    @property
    def is_on(self) -> bool | None:
        value = self._get("live", self._spec["field"])
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        on_values = self._spec.get("on_values")
        if on_values is not None:
            return int(value) in on_values
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return bool(value)

    async def _send(self, value: int) -> None:
        await self.coordinator.async_send_command(
            {key: value for key in self._spec["command"]}
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(0)
