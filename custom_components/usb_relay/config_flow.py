"""Config flow for the USB Relay integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_PORT, CONF_RELAY_COUNT, DOMAIN, MAX_RELAY_COUNT
from .helpers import detect_usb_relays


class USBRelayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Detect a USB relay board and add it."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._detected: dict[str, int] = {}
        self._port: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Probe the serial ports for relay boards."""
        detected = await self.hass.async_add_executor_job(detect_usb_relays)
        configured = self._async_current_ids(include_ignore=False)
        self._detected = {port: count for port, count in detected.items() if port not in configured}
        if not self._detected:
            if detected:
                return self.async_abort(reason="already_configured")
            return self.async_abort(reason="no_devices_found")
        return await self.async_step_select_port()

    async def async_step_select_port(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick one of the detected boards."""
        if user_input is not None:
            self._port = user_input[CONF_PORT]
            await self.async_set_unique_id(self._port)
            self._abort_if_unique_id_configured()
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="select_port",
            data_schema=vol.Schema({vol.Required(CONF_PORT): vol.In(list(self._detected))}),
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the number of relays on the board."""
        assert self._port is not None
        if user_input is not None:
            return self.async_create_entry(
                title=f"USB Relay ({self._port})",
                data={
                    CONF_PORT: self._port,
                    CONF_RELAY_COUNT: user_input[CONF_RELAY_COUNT],
                },
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_RELAY_COUNT, default=self._detected.get(self._port, 1)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_RELAY_COUNT))
                }
            ),
            description_placeholders={"port": self._port},
        )
