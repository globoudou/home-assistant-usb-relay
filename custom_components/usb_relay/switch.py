import logging
import serial
import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, DEFAULT_BAUDRATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    port = entry.data["port"]
    relay_count = entry.data["relay_count"]

    try:
        usb = serial.Serial(port, DEFAULT_BAUDRATE, timeout=1)
    except serial.SerialException as e:
        _LOGGER.error(f"Erreur ouverture port série {port} : {e}")
        return

    entities = [USBRelaySwitch(usb, i + 1) for i in range(relay_count)]
    async_add_entities(entities)

class USBRelaySwitch(SwitchEntity):
    def __init__(self, serial_conn: serial.Serial, relay_id: int):
        self._serial = serial_conn
        self._relay_id = relay_id
        self._attr_name = f"USB Relay {relay_id}"
        self._attr_unique_id = f"usb_relay_{relay_id}"
        self._attr_is_on = False

    def turn_on(self, **kwargs):
        self._send_command(True)
        self._attr_is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        self._send_command(False)
        self._attr_is_on = False
        self.schedule_update_ha_state()

    def update(self):
        try:
            self._serial.write(bytes([0xFF]))
            result = self._serial.read(8)
            if len(result) >= self._relay_id:
                self._attr_is_on = result[self._relay_id - 1] == 1
        except Exception as e:
            _LOGGER.warning(f"Erreur lecture état relais {self._relay_id} : {e}")

    def _send_command(self, state: bool):
        try:
            header = 0xA0
            relay_byte = self._relay_id
            state_byte = 0x01 if state else 0x00
            checksum = (header + relay_byte + state_byte) & 0xFF
            command = bytes([header, relay_byte, state_byte, checksum])
            self._serial.write(command)
        except Exception as e:
            _LOGGER.error(f"Erreur commande relais {self._relay_id} : {e}")