"""The DSC Neo integration."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import CONF_ACCESS_TOKEN, CONF_SSL, DEFAULT_SSL, DOMAIN
from .coordinator import NeoHubCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
]

CONNECT_RETRY_ATTEMPTS = 3
CONNECT_RETRY_DELAY = 5
INITIAL_STATE_TIMEOUT = 30
STATE_STABLE_SECONDS = 10


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DSC Neo from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    coordinator = NeoHubCoordinator(
        hass=hass,
        host=host,
        port=port,
        ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
    )

    coordinator.async_setup()

    connected = False
    for attempt in range(1, CONNECT_RETRY_ATTEMPTS + 1):
        if await coordinator.async_connect():
            connected = True
            break
        if attempt < CONNECT_RETRY_ATTEMPTS:
            _LOGGER.info(
                "Retrying NeoHub connection in %ss (attempt %s/%s)",
                CONNECT_RETRY_DELAY,
                attempt + 1,
                CONNECT_RETRY_ATTEMPTS,
            )
            await asyncio.sleep(CONNECT_RETRY_DELAY)

    if not connected:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Failed to connect to NeoHub at {host}:{port} "
            f"after {CONNECT_RETRY_ATTEMPTS} attempts"
        )

    deadline = time.monotonic() + INITIAL_STATE_TIMEOUT
    while not coordinator.state:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(1.0, remaining))

    if not coordinator.state:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Connected to NeoHub at {host}:{port} but did not receive "
            f"initial state within {INITIAL_STATE_TIMEOUT}s"
        )

    _LOGGER.debug("Received initial state, waiting for stable state from NeoHub")
    while await coordinator.async_wait_for_state_update(STATE_STABLE_SECONDS):
        _LOGGER.debug("Received updated full_state, waiting for stable state...")

    state = coordinator.state
    _LOGGER.info(
        "NeoHub state stable: %d session(s), %d partition(s), %d zone(s)",
        len(state),
        sum(len(s.get("partitions", [])) for s in state.values()),
        sum(len(s.get("zones", [])) for s in state.values()),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    device_registry = dr.async_get(hass)
    for session_id, session in state.items():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, session_id)},
            name=session.get("name", f"DSC Neo {session_id}"),
            manufacturer="DSC",
            model="NeoHub",
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: NeoHubCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update by reloading."""
    await hass.config_entries.async_reload(entry.entry_id)
