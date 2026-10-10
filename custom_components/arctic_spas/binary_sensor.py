"""Binary sensors: heating, filtering, error, SpaBoy status, economy."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSORS, DOMAIN, decode_errors
from .coordinator import SpaCoordinator
from .entity import SpaEntity

_DEVICE_CLASS = {
    "running": BinarySensorDeviceClass.RUNNING,
    "connectivity": BinarySensorDeviceClass.CONNECTIVITY,
    "heat": BinarySensorDeviceClass.HEAT,
    "problem": BinarySensorDeviceClass.PROBLEM,
}

# live `Filter` values that mean "filtering".
_FILTERING = {1, 2, 6, 7}


def _present(coordinator: SpaCoordinator, spec: dict) -> bool:
    field = spec["field"]
    if field == "__heating__":
        return coordinator.get("live", "H1") is not None or coordinator.get("live", "H2") is not None
    if field == "__filtering__":
        return coordinator.get("live", "Filter") is not None
    if field == "__error__":
        return "error" in (coordinator.data or {})
    return coordinator.get(spec["section"], field) is not None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SpaBinarySensor(coordinator, spec)
        for spec in BINARY_SENSORS
        if _present(coordinator, spec)
    )


class SpaBinarySensor(SpaEntity, BinarySensorEntity):
    def __init__(self, coordinator: SpaCoordinator, spec: dict) -> None:
        super().__init__(coordinator, spec["key"])
        self._spec = spec
        self._attr_name = spec["name"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]
        if spec.get("device_class"):
            self._attr_device_class = _DEVICE_CLASS[spec["device_class"]]
        if spec.get("category") == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        field = self._spec["field"]
        if field == "__heating__":
            h1 = self._get("live", "H1")
            h2 = self._get("live", "H2")
            if h1 is None and h2 is None:
                return None
            return (h1 in (1, 2)) or (h2 in (1, 2))
        if field == "__filtering__":
            v = self._get("live", "Filter")
            return None if v is None else int(v) in _FILTERING
        if field == "__error__":
            return bool(decode_errors((self.coordinator.data or {}).get("error")))
        value = self._get(self._spec["section"], field)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return bool(value)

    @property
    def extra_state_attributes(self):
        if self._spec["field"] != "__error__":
            return None
        return {"active_errors": decode_errors((self.coordinator.data or {}).get("error"))}
