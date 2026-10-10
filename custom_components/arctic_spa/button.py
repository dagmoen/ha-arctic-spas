"""Button entities for one-shot spa actions (boost cycles)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SpaCoordinator
from .entity import SpaEntity

# key, name, command payload, optional sett cfg flag that must be installed, icon
# Filter boost is a one-shot timed cycle, so a button fits better than a switch.
# (SpaBoy boost stays a switch — it has an on/off state.)
BUTTONS = [
    {"key": "filter_boost", "name": "Filter Boost", "command": {"FLTRboost": 1},
     "cfg": None, "icon": "mdi:air-filter"},
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for spec in BUTTONS:
        cfg = spec.get("cfg")
        if cfg is None or coordinator.get("sett", cfg):
            entities.append(SpaButton(coordinator, spec))
    async_add_entities(entities)


class SpaButton(SpaEntity, ButtonEntity):
    def __init__(self, coordinator: SpaCoordinator, spec: dict) -> None:
        super().__init__(coordinator, spec["key"])
        self._spec = spec
        self._attr_name = spec["name"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(dict(self._spec["command"]))
