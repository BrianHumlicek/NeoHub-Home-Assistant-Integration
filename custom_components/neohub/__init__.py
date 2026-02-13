"""The DSC Neo integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_ACCESS_TOKEN, CONF_SSL, DEFAULT_SSL, DOMAIN
from .coordinator import NeoHubCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
]

STARTUP_TIMEOUT_SECONDS = 10
STARTUP_POLL_INTERVAL = 0.5


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DSC Neo from a config entry."""
    coordinator = NeoHubCoordinator(
        hass=hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        ssl=entry.data.get(CONF_SSL, DEFAULT_SSL),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
    )

    if not await coordinator.async_setup():
        raise ConfigEntryNotReady("Failed to connect to DSC Neo")

    attempts = int(STARTUP_TIMEOUT_SECONDS / STARTUP_POLL_INTERVAL)
    for _ in range(attempts):
        if coordinator.state:
            break
        await asyncio.sleep(STARTUP_POLL_INTERVAL)

    if not coordinator.state:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            "Connected but did not receive initial state from DSC Neo"
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

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
