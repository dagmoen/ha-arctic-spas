"""Shared base entity for Arctic Spas."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SpaCoordinator


class SpaEntity(CoordinatorEntity[SpaCoordinator]):
    """Base entity: reads from the coordinator snapshot."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    def _get(self, section: str, field: str):
        return self.coordinator.get(section, field)

    @property
    def device_info(self) -> DeviceInfo:
        serial = self.coordinator.get("sett", "SPASN")
        sw_parts = [
            self.coordinator.get("sett", "YOCFWVer"),
            self.coordinator.get("sett", "SBFWVer"),
            self.coordinator.get("sett", "LPCFWVer"),
        ]
        sw = " / ".join(str(p) for p in sw_parts if p)
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            manufacturer="Arctic Spas",
            name="Arctic Spas",
            model=str(serial) if serial else None,
            sw_version=sw or None,
        )
