"""Climate entity: spa water temperature control."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_TEMP_F, MIN_TEMP_F
from .coordinator import SpaCoordinator
from .entity import SpaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SpaClimate(coordinator)])


class SpaClimate(SpaEntity, ClimateEntity):
    """Water temperature as a heat-only thermostat."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_target_temperature_step = 1
    _attr_min_temp = MIN_TEMP_F
    _attr_max_temp = MAX_TEMP_F
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(self, coordinator: SpaCoordinator) -> None:
        super().__init__(coordinator, "thermostat")

    @property
    def current_temperature(self) -> float | None:
        return self._get("live", "STemp")

    @property
    def target_temperature(self) -> float | None:
        tsp = self._get("sett", "TSP")
        if tsp is None:
            tsp = self._get("live", "TSP")
        return tsp

    @property
    def hvac_action(self) -> HVACAction:
        # H1/H2 are heater states: 1 warmup, 2 heating, 3 cooldown.
        h1 = self._get("live", "H1") or 0
        h2 = self._get("live", "H2") or 0
        return HVACAction.HEATING if (h1 in (1, 2) or h2 in (1, 2)) else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get("temperature")
        if temp is None:
            return
        value = max(MIN_TEMP_F, min(MAX_TEMP_F, int(round(temp))))
        await self.coordinator.async_send_command({"setTSP": value})
