import asyncio
import logging
import serial
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class USBRelayCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name="usb_relay", update_interval=None)
        self.hass = hass
        self.port = config["port"]
        self.relay_count = config["relay_count"]
        self._lock = asyncio.Lock()
        self._state = [0] * self.relay_count

    async def _async_update_data(self):
        """Lecture complète de l'état des relais."""
        try:
            return await self.hass.async_add_executor_job(self._read_relays)
        except Exception as e:
            raise UpdateFailed(f"Error reading relay state: {e}")

    def _read_relays(self):
        with self._lock:  # 🔒 protection accès série
            with serial.Serial(self.port, 9600, timeout=0.5) as ser:
                ser.write(bytes([0xFF]))
                response = ser.read(self.relay_count)
                if len(response) != self.relay_count:
                    raise IOError(f"Expected {self.relay_count} bytes, got {len(response)}")
                self._state = list(response)
                return self._state

    async def async_switch(self, relay: int, state: int):
        """Changer l'état d'un relais puis rafraîchir tout l'état."""
        async with self._lock:
            await self.hass.async_add_executor_job(self._write_relay, relay, state)
        # ✅ lecture immédiate après écriture
        await self.async_request_refresh()

    def _write_relay(self, relay: int, state: int):
        cmd = [0xA0, 0x0A, relay & 0xFF, state & 0xFF]
        checksum = sum(cmd) & 0xFF
        cmd.append(checksum)
        with serial.Serial(self.port, 9600, timeout=0.5) as ser:
            ser.write(bytes(cmd))
