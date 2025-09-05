import asyncio
import logging
import serial
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class USBRelayCoordinator(DataUpdateCoordinator[list[int]]):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name="usb_relay", update_interval=None)
        self.hass = hass
        self.port = config["port"]
        self.relay_count = int(config["relay_count"])
        self._lock = asyncio.Lock()  # 🔒 verrou async pour séquencer lecture/écriture

    async def _async_update_data(self):
        """Lecture complète de l'état des relais (protégée par un lock async)."""
        async with self._lock:
            try:
                state = await self.hass.async_add_executor_job(self._read_relays)
                return state
            except Exception as e:
                raise UpdateFailed(f"Error reading relay state: {e}")

    def _read_relays(self) -> list[int]:
        """Bloc IO synchrone (pas de lock asyncio ici)."""
        with serial.Serial(self.port, 9600, timeout=0.5) as ser:
            ser.write(bytes([0xFF]))
            response = ser.read(self.relay_count)

        if len(response) != self.relay_count:
            raise IOError(f"Expected {self.relay_count} bytes, got {len(response)}")
        # Optionnel: valider que chaque octet est bien 0/1
        if any(b not in (0, 1) for b in response):
            raise IOError(f"Invalid relay bytes: {list(response)}")

        return list(response)

    async def async_switch(self, relay_idx: int, state: int):
        """
        Change l'état d'un relais puis publie immédiatement le nouvel état.
        On reste sous le même lock pour éviter toute concurrence.
        """
        async with self._lock:
            await self.hass.async_add_executor_job(self._write_relay, relay_idx, state)
            new_state = await self.hass.async_add_executor_job(self._read_relays)
            # Met à jour immédiatement les abonnés (entités) sans repasser par un cycle de refresh
            self.async_set_updated_data(new_state)

    def _write_relay(self, relay_idx: int, state: int):
        """
        Ecriture synchrone de la commande sur le port série.
        Protocole: 0xA0, 0x0n, 0x0s, checksum
        - n = numéro de relais (1..N)
        - s = 1 (ON) ou 0 (OFF)
        - checksum = (0xA0 + n + s) & 0xFF
        """
        relay_num = (relay_idx + 1) & 0xFF  # UI 0-based -> protocole 1-based
        header = 0xA0
        state_byte = 0x01 if state else 0x00
        checksum = (header + relay_num + state_byte) & 0xFF
        payload = bytes([header, relay_num, state_byte, checksum])

        with serial.Serial(self.port, 9600, timeout=0.5) as ser:
            ser.write(payload)
