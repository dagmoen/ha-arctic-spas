"""Sensor entities: temperatures, power, SpaBoy chemistry, status enums."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ENUM_SENSORS, SENSORS, decode_errors
from .coordinator import SpaCoordinator
from .entity import SpaEntity

_CATEGORY = {"diagnostic": EntityCategory.DIAGNOSTIC}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SpaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for spec in SENSORS:
        if coordinator.get(spec["section"], spec["field"]) is not None:
            entities.append(SpaSensor(coordinator, spec))
    for spec in ENUM_SENSORS:
        if coordinator.get(spec["section"], spec["field"]) is not None:
            entities.append(SpaEnumSensor(coordinator, spec))
    if "error" in (coordinator.data or {}):
        entities.append(SpaErrorSensor(coordinator))
    async_add_entities(entities)


class _Base(SpaEntity, SensorEntity):
    def __init__(self, coordinator: SpaCoordinator, spec: dict) -> None:
        super().__init__(coordinator, spec["key"])
        self._spec = spec
        self._attr_name = spec["name"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]
        if spec.get("unit"):
            self._attr_native_unit_of_measurement = spec["unit"]
        if spec.get("device_class"):
            self._attr_device_class = spec["device_class"]
        if spec.get("state_class") == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if spec.get("category"):
            self._attr_entity_category = _CATEGORY[spec["category"]]


class SpaSensor(_Base):
    @property
    def native_value(self):
        value = self._get(self._spec["section"], self._spec["field"])
        if value is None:
            return None
        if self._spec.get("divisor"):
            value = value / self._spec["divisor"]
        if self._spec.get("multiplier"):
            value = value * self._spec["multiplier"]
        if "round" in self._spec:
            value = round(value, self._spec["round"])
            if self._spec["round"] == 0:
                value = int(value)
        return value


class SpaEnumSensor(_Base):
    _attr_device_class = None

    @property
    def native_value(self):
        idx = self._get(self._spec["section"], self._spec["field"])
        if idx is None:
            return None
        try:
            return self._spec["map"].get(int(idx))
        except (ValueError, TypeError):
            return None


class SpaErrorSensor(SpaEntity, SensorEntity):
    """Human-readable active-error summary, with the full list as an attribute."""

    _attr_name = "Error"
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: SpaCoordinator) -> None:
        super().__init__(coordinator, "error_detail")

    @property
    def native_value(self):
        active = decode_errors((self.coordinator.data or {}).get("error"))
        return "OK" if not active else "; ".join(active)

    @property
    def extra_state_attributes(self):
        return {"active_errors": decode_errors((self.coordinator.data or {}).get("error"))}
