import logging
import serial
from datetime import timedelta

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

class USBRelayCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: ConfigType):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

        self.port = config["port"]
        self.relay_count = config["relay_count"]
        self._serial = None

    def _open_serial(self):
        if not self._serial or not self._serial.is_open:
            self._serial = serial.Serial(self.port, 9600, timeout=1)

    def _close_serial(self):
        if self._serial and self._serial.is_open:
            self._serial.close()

    def read_states(self):
        """Send 0xFF and read the state of all relays."""
        self._open_serial()
        self._serial.write(bytes([0xFF]))
        response = self._serial.read(self.relay_count)
        return [bool(b) for b in response]

    def write_state(self, relay: int, state: bool):
        """Send command to switch a relay."""
        # Format: 0xA0 0x0n 0x0s 0xcs
        # n = relay number (1-based)
        # s = 1 (on) or 0 (off)
        # cs = checksum = 0xA0 + 0x0n + 0x0s
        self._open_serial()
        header = 0xA0
        n = 0x01 + relay
        s = 0x01 if state else 0x00
        checksum = (header + n + s) & 0xFF
        self._serial.write(bytes([header, n, s, checksum]))

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.read_states)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with relay: {err}")
