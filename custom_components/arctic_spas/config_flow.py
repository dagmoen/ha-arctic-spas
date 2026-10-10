"""Config flow for Arctic Spas (Local): zeroconf discovery + manual entry."""
from __future__ import annotations

import socket
from typing import Any

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT

try:  # HA >= 2024.4
    from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
except ImportError:  # older HA
    from homeassistant.config_entries import ConfigFlow
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

try:  # HA >= 2024.8
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # older HA
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .const import CONF_SPA_GUID, DEFAULT_PORT, DOMAIN


def _test_connection(host: str, port: int) -> bool:
    """Return True if the spa's WebSocket port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except OSError:
        return False


class ArcticSpaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._spa_guid: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            if not await self.hass.async_add_executor_job(_test_connection, host, port):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Arctic Spas ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        props = discovery_info.properties or {}
        spa_guid = props.get("spa_guid")
        if not spa_guid:
            # Some other MQTT service, not an Arctic Spas.
            return self.async_abort(reason="not_arctic_spa")

        host = props.get("device_ip") or discovery_info.host
        self._host = host
        self._port = DEFAULT_PORT
        self._spa_guid = spa_guid

        await self.async_set_unique_id(spa_guid)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self.context["title_placeholders"] = {"name": f"Arctic Spas ({host})"}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=f"Arctic Spas ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_SPA_GUID: self._spa_guid,
                },
            )
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"host": self._host or ""},
        )
