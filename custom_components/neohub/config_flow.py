"""Config flow for DSC Neo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .const import CONF_ACCESS_TOKEN, CONF_SSL, DEFAULT_PORT, DEFAULT_SSL, DOMAIN
from .pyneohub import NeoHubClient, NeoHubConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SSL, default=DEFAULT_SSL): bool,
        vol.Optional(CONF_ACCESS_TOKEN): str,
    }
)


class NeoHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DSC Neo (via NeoHub)."""

    VERSION = 1

    _hassio_discovery: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if await self._test_connection(user_input):
                return self.async_create_entry(
                    title=f"NeoHub server ({user_input[CONF_HOST]})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """Handle a discovery initiated by the Hass.io supervisor."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        config = discovery_info.config
        self._hassio_discovery = {
            CONF_HOST: config.get("host", "localhost"),
            CONF_PORT: config.get("port", DEFAULT_PORT),
            CONF_SSL: config.get("ssl", DEFAULT_SSL),
            CONF_ACCESS_TOKEN: config.get("access_token"),
        }
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a Hass.io discovery."""
        assert self._hassio_discovery is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            if await self._test_connection(self._hassio_discovery):
                return self.async_create_entry(
                    title=f"NeoHub ({self._hassio_discovery[CONF_HOST]})",
                    data=self._hassio_discovery,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="hassio_confirm",
            description_placeholders={
                "host": self._hassio_discovery[CONF_HOST],
                "port": str(self._hassio_discovery[CONF_PORT]),
            },
            errors=errors,
        )

    async def _test_connection(self, data: dict[str, Any]) -> bool:
        """Test whether we can connect to the NeoHub WebSocket."""
        client = NeoHubClient(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            ssl=data.get(CONF_SSL, DEFAULT_SSL),
            access_token=data.get(CONF_ACCESS_TOKEN),
        )
        try:
            await client.connect()
            await client.disconnect()
            return True
        except NeoHubConnectionError:
            _LOGGER.debug("Connection test failed", exc_info=True)
            return False
