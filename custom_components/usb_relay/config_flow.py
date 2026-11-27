"""Config flow for the USB Relay integration."""

from __future__ import annotations

from typing import Any

import serial
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_PORT, CONF_RELAY_COUNT, DOMAIN, MAX_RELAY_COUNT
from .helpers import list_serial_ports, probe_relay_board


class USBRelayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a USB relay board.

    The serial ports are only listed, never opened, until the user has picked
    one; only that port is then queried.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._port: str | None = None
        self._relay_count = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Let the user pick a serial port, then query that port only."""
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()
            try:
                relay_count = await self.hass.async_add_executor_job(probe_relay_board, port)
            except (OSError, serial.SerialException):
                errors["base"] = "cannot_connect"
            else:
                if relay_count is None:
                    errors["base"] = "not_a_relay_board"
                else:
                    self._port = port
                    self._relay_count = relay_count
                    return await self.async_step_confirm()

        ports = await self.hass.async_add_executor_job(list_serial_ports)
        configured = self._async_current_ids(include_ignore=False)
        available = {port: label for port, label in ports.items() if port not in configured}
        if not available:
            if ports:
                return self.async_abort(reason="already_configured")
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PORT): vol.In(available)}),
            errors=errors,
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
                    vol.Required(CONF_RELAY_COUNT, default=self._relay_count): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=MAX_RELAY_COUNT)
                    )
                }
            ),
            description_placeholders={"port": self._port},
        )
