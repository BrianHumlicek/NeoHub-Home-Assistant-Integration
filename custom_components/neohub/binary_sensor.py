"""Binary sensor platform for DSC Neo integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CONNECTION_STATE, SIGNAL_STATE_UPDATED
from .coordinator import NeoHubCoordinator

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_MAP: dict[str, BinarySensorDeviceClass] = {
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "motion": BinarySensorDeviceClass.MOTION,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "gas": BinarySensorDeviceClass.GAS,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "vibration": BinarySensorDeviceClass.VIBRATION,
    "safety": BinarySensorDeviceClass.SAFETY,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DSC Neo binary sensor entities."""
    coordinator: NeoHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    device_registry = dr.async_get(hass)
    hub_device_ids: dict[str, str | None] = {}
    for session_id in coordinator.state:
        hub_device = device_registry.async_get_device_by_identifier(
            (DOMAIN, session_id), entry.entry_id
        )
        hub_device_ids[session_id] = hub_device.id if hub_device else None

    entities: list[DscZoneSensor] = []
    for session_id, session in coordinator.state.items():
        for zone in session.get("zones", []):
            entities.append(
                DscZoneSensor(
                    coordinator=coordinator,
                    session_id=session_id,
                    hub_device_id=hub_device_ids[session_id],
                    zone_number=zone["zone_number"],
                    zone_name=zone.get(
                        "name", f"Zone {zone['zone_number']}"
                    ),
                    device_class_str=zone.get("device_class", ""),
                    initial_open=zone.get("open", False),
                    initial_bypassed=zone.get("bypassed", False),
                    partition_list=zone.get("partitions", []),
                )
            )

    async_add_entities(entities)


class DscZoneSensor(BinarySensorEntity):
    """Representation of a DSC Neo zone as a binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NeoHubCoordinator,
        session_id: str,
        hub_device_id: str | None,
        zone_number: int,
        zone_name: str,
        device_class_str: str,
        initial_open: bool,
        initial_bypassed: bool,
        partition_list: list[int],
    ) -> None:
        """Initialize the binary sensor entity."""
        self._coordinator = coordinator
        self._session_id = session_id
        self._zone_number = zone_number
        self._bypassed = initial_bypassed
        self._partition_list = partition_list
        self._attr_unique_id = f"{session_id}_zone_{zone_number}"
        self._attr_name = None
        self._attr_is_on = initial_open
        self._attr_device_class = DEVICE_CLASS_MAP.get(device_class_str)
        device_info: DeviceInfo = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": zone_name,
            "manufacturer": "DSC",
            "model": "Neo Zone",
        }
        if hub_device_id is not None:
            device_info["via_device_id"] = hub_device_id
        self._attr_device_info = device_info

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "bypassed": self._bypassed,
            "partitions": self._partition_list,
        }

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._coordinator.connected

    async def async_added_to_hass(self) -> None:
        """Register dispatch listeners when added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_STATE_UPDATED}_zone_{self._session_id}_{self._zone_number}",
                self._handle_update,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_CONNECTION_STATE,
                self._handle_connection_state,
            )
        )

    @callback
    def _handle_update(self, data: dict[str, Any]) -> None:
        """Handle a zone state update."""
        if "open" in data:
            self._attr_is_on = data["open"]
        if "bypassed" in data:
            self._bypassed = data["bypassed"]
        if "partitions" in data:
            self._partition_list = data["partitions"]
        self.async_write_ha_state()

    @callback
    def _handle_connection_state(self, connected: bool) -> None:
        """Handle a connection state change."""
        self.async_write_ha_state()
