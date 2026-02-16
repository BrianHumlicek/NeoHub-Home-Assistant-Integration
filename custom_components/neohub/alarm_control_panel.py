"""Alarm control panel platform for DSC Neo (via NeoHub) integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CONNECTION_STATE, SIGNAL_STATE_UPDATED
from .coordinator import NeoHubCoordinator

_LOGGER = logging.getLogger(__name__)

STATUS_MAP: dict[str, AlarmControlPanelState] = {
    "disarmed": AlarmControlPanelState.DISARMED,
    "armed_away": AlarmControlPanelState.ARMED_AWAY,
    "armed_home": AlarmControlPanelState.ARMED_HOME,
    "armed_night": AlarmControlPanelState.ARMED_NIGHT,
    "arming": AlarmControlPanelState.ARMING,
    "pending": AlarmControlPanelState.PENDING,
    "triggered": AlarmControlPanelState.TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DSC Neo alarm control panel entities."""
    coordinator: NeoHubCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[DscAlarmPanel] = []
    for session_id, session in coordinator.state.items():
        session_name = session.get("name", f"DSC Neo {session_id}")
        for partition in session.get("partitions", []):
            entities.append(
                DscAlarmPanel(
                    coordinator=coordinator,
                    session_id=session_id,
                    session_name=session_name,
                    partition_number=partition["partition_number"],
                    partition_name=partition.get(
                        "name",
                        f"Partition {partition['partition_number']}",
                    ),
                    initial_status=partition.get("status", "unknown"),
                )
            )

    async_add_entities(entities)


class DscAlarmPanel(AlarmControlPanelEntity):
    """Representation of a DSC Neo partition as an alarm control panel."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    _attr_code_arm_required = False
    _attr_code_format = CodeFormat.NUMBER

    def __init__(
        self,
        coordinator: NeoHubCoordinator,
        session_id: str,
        session_name: str,
        partition_number: int,
        partition_name: str,
        initial_status: str,
    ) -> None:
        """Initialize the alarm panel entity."""
        self._coordinator = coordinator
        self._session_id = session_id
        self._partition_number = partition_number
        self._status = initial_status
        self._attr_unique_id = f"{session_id}_partition_{partition_number}"
        self._attr_name = partition_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, session_id)},
            name=session_name,
            manufacturer="DSC",
            model="Neo",
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state."""
        return STATUS_MAP.get(self._status)

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._coordinator.connected

    async def async_added_to_hass(self) -> None:
        """Register dispatch listeners when added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_STATE_UPDATED}_partition_{self._session_id}_{self._partition_number}",
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
        """Handle a partition state update."""
        if "status" in data:
            self._status = data["status"]
        self.async_write_ha_state()

    @callback
    def _handle_connection_state(self, connected: bool) -> None:
        """Handle a connection state change."""
        self.async_write_ha_state()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._coordinator.client.arm_away(
            self._session_id, self._partition_number, code
        )

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home (stay) command."""
        await self._coordinator.client.arm_home(
            self._session_id, self._partition_number, code
        )

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        await self._coordinator.client.arm_night(
            self._session_id, self._partition_number, code
        )

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._coordinator.client.disarm(
            self._session_id, self._partition_number, code
        )
