"""Coordinator for the USB Relay integration."""

from __future__ import annotations

import asyncio
import logging

import serial
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_BAUDRATE, DOMAIN, SERIAL_TIMEOUT
from .helpers import READ_STATE_COMMAND, build_switch_command

_LOGGER = logging.getLogger(__name__)

type USBRelayConfigEntry = ConfigEntry[USBRelayCoordinator]


class USBRelayCoordinator(DataUpdateCoordinator[list[int]]):
    """Reads and writes the relay board over its serial port."""

    config_entry: USBRelayConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: USBRelayConfigEntry,
        port: str,
        relay_count: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.port = port
        self.relay_count = relay_count
        # Serialize every read/write on the serial port.
        self._lock = asyncio.Lock()

    async def _async_update_data(self) -> list[int]:
        """Read the state of every relay."""
        async with self._lock:
            try:
                return await self.hass.async_add_executor_job(self._read_relays)
            except (OSError, serial.SerialException) as err:
                raise UpdateFailed(f"Error reading relay state: {err}") from err

    async def async_switch(self, relay_idx: int, state: bool) -> None:
        """Switch a relay, then publish the new state of the board."""
        async with self._lock:
            try:
                await self.hass.async_add_executor_job(self._write_relay, relay_idx, state)
                new_state = await self.hass.async_add_executor_job(self._read_relays)
            except (OSError, serial.SerialException) as err:
                raise HomeAssistantError(f"Error switching relay {relay_idx + 1}: {err}") from err
        self.async_set_updated_data(new_state)

    def _read_relays(self) -> list[int]:
        """Blocking read of the relay states."""
        with serial.Serial(self.port, DEFAULT_BAUDRATE, timeout=SERIAL_TIMEOUT) as ser:
            ser.write(READ_STATE_COMMAND)
            response = ser.read(self.relay_count)

        if len(response) != self.relay_count:
            raise OSError(f"Expected {self.relay_count} bytes, got {len(response)}")
        if any(b not in (0, 1) for b in response):
            raise OSError(f"Invalid relay bytes: {list(response)}")
        return list(response)

    def _write_relay(self, relay_idx: int, state: bool) -> None:
        """Blocking write of a switch command."""
        with serial.Serial(self.port, DEFAULT_BAUDRATE, timeout=SERIAL_TIMEOUT) as ser:
            ser.write(build_switch_command(relay_idx, state))
