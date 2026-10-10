"""Select entity for the 2-speed Pump 1 (off/low/high).

Pump 1 is driven by a cycle button: publishing {"P1next": 0} advances it
off -> low -> high -> off (the value is ignored). To set a target speed we press
the cycle the right number of times, spaced out to clear the controller's
debounce. The current option always reflects the live reported speed, including
when the spa drops to low on its own for circulation/heating.
"""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PUMP1_SPEEDS, pump1_speed
from .coordinator import SpaCoordinator
from .entity import SpaEntity

_LOGGER = logging.getLogger(__name__)

# Dwell between cycle presses — must exceed the controller debounce (~3s ignored,
# ~12s reliable from testing).
_PRESS_DWELL = 13
_MAX_PRESSES = 4


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    installed = coordinator.get("sett", "cfgP1")
    if installed is None:
        installed = coordinator.get("live", "P1") is not None
    if installed:
        async_add_entities([Pump1Select(coordinator)])


class Pump1Select(SpaEntity, SelectEntity):
    _attr_name = "Pump 1"
    _attr_icon = "mdi:pump"
    _attr_options = PUMP1_SPEEDS

    def __init__(self, coordinator: SpaCoordinator) -> None:
        super().__init__(coordinator, "pump1_speed")
        self._lock = asyncio.Lock()

    @property
    def current_option(self) -> str | None:
        return pump1_speed(self._get("live", "P1"))

    async def async_select_option(self, option: str) -> None:
        if option not in PUMP1_SPEEDS:
            return
        async with self._lock:
            seen: set[str] = set()
            for _ in range(_MAX_PRESSES):
                current = self.current_option
                if current == option:
                    return
                # If we've already visited this speed, the cycle has come back
                # around without reaching the target — it's unreachable right now
                # (e.g. the spa is forcing low for heating/circulation). Stop
                # rather than keep thrashing the pump.
                if current in seen:
                    _LOGGER.debug(
                        "Pump 1 target %s unreachable (stuck at %s); the spa is "
                        "likely circulating for heat/filtration", option, current
                    )
                    return
                seen.add(current)
                # One press advances one step in the off->low->high->off cycle.
                await self.coordinator.client.async_send_command({"P1next": 0})
                await asyncio.sleep(_PRESS_DWELL)
                await self.coordinator.async_request_refresh()
