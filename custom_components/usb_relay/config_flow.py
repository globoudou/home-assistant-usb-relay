import logging
import serial
import serial.tools.list_ports
from homeassistant import config_entries
import voluptuous as vol
import os

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def resolve_by_id(port: str) -> str:
    """Retourne le chemin /dev/serial/by-id/... correspondant si disponible."""
    by_id_path = "/dev/serial/by-id"
    if not os.path.exists(by_id_path):
        return port

    for entry in os.listdir(by_id_path):
        full_path = os.path.join(by_id_path, entry)
        if os.path.realpath(full_path) == os.path.realpath(port):
            return full_path
    return port

def detect_usb_relays():
    found = []
    ports = serial.tools.list_ports.comports()

    for port_info in ports:
        try:
            with serial.Serial(port_info.device, 9600, timeout=0.5) as ser:
                ser.write(bytes([0xFF]))
                response = ser.read(8)

                if 1 <= len(response) <= 8 and all(b in (0, 1) for b in response):
                    id_path = resolve_by_id(port_info.device)
                    _LOGGER.debug("USB relay detected on %s (%s) with %d channels", port_info.device, id_path, len(response))
                    found.append((id_path, len(response)))
        except Exception as e:
            _LOGGER.debug("Failed to probe %s: %s", port_info.device, e)
            continue

    return found

class USBRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        ports = await self.hass.async_add_executor_job(detect_usb_relays)
        if not ports:
            return self.async_abort(reason="no_devices_found")

        self.detected_ports = {p[0]: p[1] for p in ports}
        return await self.async_step_select_port()

    async def async_step_select_port(self, user_input=None):
        errors = {}

        if user_input is not None:
            self.selected_port = user_input["port"]
            self.relay_count = self.detected_ports.get(self.selected_port, 1)
            return await self.async_step_confirm()

        schema = vol.Schema({
            vol.Required("port"): vol.In(list(self.detected_ports.keys()))
        })

        return self.async_show_form(
            step_id="select_port",
            data_schema=schema,
            errors=errors
        )

    async def async_step_confirm(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=f"USB Relay ({self.selected_port})",
                data={
                    "port": self.selected_port,
                    "relay_count": user_input["relay_count"]
                }
            )

        schema = vol.Schema({
            vol.Required("relay_count", default=self.relay_count): vol.All(int, vol.Range(min=1, max=8))
        })

        return self.async_show_form(
            step_id="confirm",
            data_schema=schema
        )
