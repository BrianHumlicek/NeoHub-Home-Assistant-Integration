"""NeoHub WebSocket client library."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

RECONNECT_INTERVAL = 10
MAX_RECONNECT_INTERVAL = 300


class NeoHubError(Exception):
    """Base exception for NeoHub client."""


class NeoHubConnectionError(NeoHubError):
    """Connection error."""


class NeoHubClient:
    """WebSocket client for NeoHub."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        ssl: bool = False,
        access_token: str | None = None,
    ) -> None:
        """Initialize the client.
        
        Args:
            host: Hostname or IP address
            port: Port number
            ssl: Use SSL/TLS
            access_token: Optional bearer token for authentication
        """
        self.host = host
        self.port = port
        self.ssl = ssl
        self.access_token = access_token
        
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._state: dict[str, Any] = {}
        self._connected = False
        self._listen_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._shutdown = False
        
        # Callbacks
        self._on_connect: list[Callable[[], None]] = []
        self._on_disconnect: list[Callable[[], None]] = []
        self._on_full_state: list[Callable[[dict[str, Any]], None]] = []
        self._on_partition_update: list[Callable[[dict[str, Any]], None]] = []
        self._on_zone_update: list[Callable[[dict[str, Any]], None]] = []
        self._on_error: list[Callable[[str], None]] = []

    @property
    def connected(self) -> bool:
        """Return True if connected to WebSocket."""
        return self._connected

    @property
    def state(self) -> dict[str, Any]:
        """Return the current state dictionary keyed by session_id."""
        return self._state

    @property
    def ws_url(self) -> str:
        """Return the WebSocket URL."""
        scheme = "wss" if self.ssl else "ws"
        return f"{scheme}://{self.host}:{self.port}/api/ws"

    def register_connection_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback for connection events.
        
        Returns:
            A function to unregister the callback
        """
        self._on_connect.append(callback)
        return lambda: self._on_connect.remove(callback)

    def register_disconnection_callback(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback for disconnection events.
        
        Returns:
            A function to unregister the callback
        """
        self._on_disconnect.append(callback)
        return lambda: self._on_disconnect.remove(callback)

    def register_full_state_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Register a callback for full_state messages.
        
        Returns:
            A function to unregister the callback
        """
        self._on_full_state.append(callback)
        return lambda: self._on_full_state.remove(callback)

    def register_partition_update_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Register a callback for partition_update messages.
        
        Returns:
            A function to unregister the callback
        """
        self._on_partition_update.append(callback)
        return lambda: self._on_partition_update.remove(callback)

    def register_zone_update_callback(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        """Register a callback for zone_update messages.
        
        Returns:
            A function to unregister the callback
        """
        self._on_zone_update.append(callback)
        return lambda: self._on_zone_update.remove(callback)

    def register_error_callback(
        self, callback: Callable[[str], None]
    ) -> Callable[[], None]:
        """Register a callback for error messages.
        
        Returns:
            A function to unregister the callback
        """
        self._on_error.append(callback)
        return lambda: self._on_error.remove(callback)

    async def connect(self) -> bool:
        """Connect to the WebSocket server and request initial state."""
        self._shutdown = False
        try:
            self._session = aiohttp.ClientSession()
            headers: dict[str, str] = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            self._ws = await self._session.ws_connect(
                self.ws_url,
                headers=headers,
                heartbeat=30,
            )
            self._connected = True
            
            for callback in self._on_connect:
                callback()

            await self._send({"type": "get_full_state"})

            self._listen_task = asyncio.create_task(self._listen())

            _LOGGER.info("Connected to NeoHub at %s:%s", self.host, self.port)
            return True

        except Exception as err:
            _LOGGER.error("Failed to connect to NeoHub: %s", err)
            await self._cleanup()
            raise NeoHubConnectionError(f"Connection failed: {err}") from err

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        self._shutdown = True
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        if self._listen_task is not None:
            self._listen_task.cancel()
            self._listen_task = None
        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up the WebSocket and HTTP session."""
        was_connected = self._connected
        self._connected = False

        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None

        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

        if was_connected:
            for callback in self._on_disconnect:
                try:
                    callback()
                except Exception:
                    _LOGGER.exception("Error in disconnection callback")

    async def _send(self, data: dict[str, Any]) -> None:
        """Send a JSON message over the WebSocket."""
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_json(data)
        else:
            _LOGGER.warning("Cannot send message, WebSocket not connected")

    async def _listen(self) -> None:
        """Listen for incoming WebSocket messages."""
        try:
            assert self._ws is not None
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        self._handle_message(data)
                    except json.JSONDecodeError:
                        _LOGGER.error("Invalid JSON received: %s", msg.data)
                    except Exception:
                        _LOGGER.exception("Error handling message")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", self._ws.exception())
                    break
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                ):
                    _LOGGER.warning(
                        "WebSocket closed by server (code=%s)",
                        getattr(msg, 'data', 'N/A'),
                    )
                    break
        except asyncio.CancelledError:
            return
        except Exception:
            _LOGGER.exception("WebSocket listen error")

        await self._cleanup()
        if not self._shutdown:
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff."""
        interval = RECONNECT_INTERVAL
        while not self._shutdown:
            _LOGGER.debug("Reconnecting in %s seconds", interval)
            await asyncio.sleep(interval)
            try:
                if await self.connect():
                    return
            except NeoHubConnectionError:
                pass
            interval = min(interval * 2, MAX_RECONNECT_INTERVAL)

    def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle an incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "full_state":
            self._handle_full_state(data)
        elif msg_type == "partition_update":
            self._handle_partition_update(data)
        elif msg_type == "zone_update":
            self._handle_zone_update(data)
        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            _LOGGER.error("NeoHub server error: %s", error_msg)
            for callback in self._on_error:
                try:
                    callback(error_msg)
                except Exception:
                    _LOGGER.exception("Error in error callback")
        else:
            _LOGGER.warning("Unknown message type '%s': %s", msg_type, data)

    def _handle_full_state(self, data: dict[str, Any]) -> None:
        """Process a full_state message."""
        self._state = {}
        for session in data.get("sessions", []):
            session_id = session.get("session_id")
            if session_id is None:
                _LOGGER.error("Session missing session_id: %s", session)
                continue
            self._state[session_id] = session

        _LOGGER.info(
            "Received full state: %d session(s), %d partition(s), %d zone(s)",
            len(self._state),
            sum(len(s.get("partitions", [])) for s in self._state.values()),
            sum(len(s.get("zones", [])) for s in self._state.values()),
        )

        for callback in self._on_full_state:
            try:
                callback(data)
            except Exception:
                _LOGGER.exception("Error in full_state callback")

    def _handle_partition_update(self, data: dict[str, Any]) -> None:
        """Process a partition_update message."""
        session_id = data.get("session_id")
        partition_number = data.get("partition_number")

        if session_id is None or partition_number is None:
            _LOGGER.error(
                "Received partition_update missing required fields. Data: %s",
                data,
            )
            return

        if session_id in self._state:
            for partition in self._state[session_id].get("partitions", []):
                if partition["partition_number"] == partition_number:
                    if "status" in data:
                        partition["status"] = data["status"]
                    break

        for callback in self._on_partition_update:
            try:
                callback(data)
            except Exception:
                _LOGGER.exception("Error in partition_update callback")

    def _handle_zone_update(self, data: dict[str, Any]) -> None:
        """Process a zone_update message."""
        session_id = data.get("session_id")
        zone_number = data.get("zone_number")

        if session_id is None or zone_number is None:
            _LOGGER.error(
                "Received zone_update missing required fields. Data: %s",
                data,
            )
            return

        if session_id in self._state:
            for zone in self._state[session_id].get("zones", []):
                if zone["zone_number"] == zone_number:
                    if "open" in data:
                        zone["open"] = data["open"]
                    if "partitions" in data:
                        zone["partitions"] = data["partitions"]
                    break

        for callback in self._on_zone_update:
            try:
                callback(data)
            except Exception:
                _LOGGER.exception("Error in zone_update callback")

    # ── Commands ────────────────────────────────────────────────────────

    async def arm_away(
        self, session_id: str, partition_number: int, code: str | None = None
    ) -> None:
        """Send an arm-away command."""
        await self._send(
            {
                "type": "arm_away",
                "session_id": session_id,
                "partition_number": partition_number,
                "code": code,
            }
        )

    async def arm_home(
        self, session_id: str, partition_number: int, code: str | None = None
    ) -> None:
        """Send an arm-home (stay) command."""
        await self._send(
            {
                "type": "arm_home",
                "session_id": session_id,
                "partition_number": partition_number,
                "code": code,
            }
        )

    async def arm_night(
        self, session_id: str, partition_number: int, code: str | None = None
    ) -> None:
        """Send an arm-night command."""
        await self._send(
            {
                "type": "arm_night",
                "session_id": session_id,
                "partition_number": partition_number,
                "code": code,
            }
        )

    async def disarm(
        self, session_id: str, partition_number: int, code: str | None = None
    ) -> None:
        """Send a disarm command."""
        await self._send(
            {
                "type": "disarm",
                "session_id": session_id,
                "partition_number": partition_number,
                "code": code,
            }
        )
