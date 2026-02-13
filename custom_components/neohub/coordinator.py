"""Coordinator for DSC Neo (via NeoHub) integration."""

from __future__ import annotations

import logging
from typing import Any

from .pyneohub import NeoHubClient, NeoHubConnectionError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_CONNECTION_STATE, SIGNAL_STATE_UPDATED

_LOGGER = logging.getLogger(__name__)


class NeoHubCoordinator:
    """Coordinator to manage NeoHub client and Home Assistant integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        ssl: bool,
        access_token: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self._client = NeoHubClient(
            host=host,
            port=port,
            ssl=ssl,
            access_token=access_token,
        )

        self._unregister_callbacks: list = []

    @property
    def client(self) -> NeoHubClient:
        """Return the client instance."""
        return self._client

    @property
    def connected(self) -> bool:
        """Return True if connected."""
        return self._client.connected

    @property
    def state(self) -> dict[str, Any]:
        """Return the current state."""
        return self._client.state

    async def async_setup(self) -> bool:
        """Set up the coordinator."""
        self._register_callbacks()

        try:
            await self._client.connect()
        except NeoHubConnectionError as err:
            _LOGGER.error("Failed to connect: %s", err)
            return False

        return True

    async def async_shutdown(self) -> None:
        """Shut down the coordinator."""
        for unregister in self._unregister_callbacks:
            unregister()
        self._unregister_callbacks.clear()

        await self._client.disconnect()

    def _register_callbacks(self) -> None:
        """Register callbacks with the client."""
        self._unregister_callbacks.append(
            self._client.register_connection_callback(self._handle_connection)
        )
        self._unregister_callbacks.append(
            self._client.register_disconnection_callback(self._handle_disconnection)
        )
        self._unregister_callbacks.append(
            self._client.register_full_state_callback(self._handle_full_state)
        )
        self._unregister_callbacks.append(
            self._client.register_partition_update_callback(
                self._handle_partition_update
            )
        )
        self._unregister_callbacks.append(
            self._client.register_zone_update_callback(self._handle_zone_update)
        )

    def _handle_connection(self) -> None:
        """Handle connection event."""
        async_dispatcher_send(self.hass, SIGNAL_CONNECTION_STATE, True)

    def _handle_disconnection(self) -> None:
        """Handle disconnection event."""
        _LOGGER.warning("DSC Neo disconnected")
        async_dispatcher_send(self.hass, SIGNAL_CONNECTION_STATE, False)

    def _handle_full_state(self, data: dict[str, Any]) -> None:
        """Handle full_state message from client."""
        for session in data.get("sessions", []):
            session_id = session.get("session_id")
            if session_id is None:
                continue

            for partition in session.get("partitions", []):
                pn = partition.get("partition_number")
                if pn is None:
                    continue
                async_dispatcher_send(
                    self.hass,
                    f"{SIGNAL_STATE_UPDATED}_partition_{session_id}_{pn}",
                    partition,
                )

            for zone in session.get("zones", []):
                zn = zone.get("zone_number")
                if zn is None:
                    continue
                async_dispatcher_send(
                    self.hass,
                    f"{SIGNAL_STATE_UPDATED}_zone_{session_id}_{zn}",
                    zone,
                )

    def _handle_partition_update(self, data: dict[str, Any]) -> None:
        """Handle partition_update message from client."""
        session_id = data.get("session_id")
        partition_number = data.get("partition_number")

        if session_id is None or partition_number is None:
            return

        async_dispatcher_send(
            self.hass,
            f"{SIGNAL_STATE_UPDATED}_partition_{session_id}_{partition_number}",
            data,
        )

    def _handle_zone_update(self, data: dict[str, Any]) -> None:
        """Handle zone_update message from client."""
        session_id = data.get("session_id")
        zone_number = data.get("zone_number")

        if session_id is None or zone_number is None:
            return

        async_dispatcher_send(
            self.hass,
            f"{SIGNAL_STATE_UPDATED}_zone_{session_id}_{zone_number}",
            data,
        )

