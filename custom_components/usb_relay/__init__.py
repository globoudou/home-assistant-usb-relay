from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .coordinator import USBRelayCoordinator
import os
import serial.tools.list_ports

_LOGGER = logging.getLogger(__name__)

def resolve_by_id_path(port: str) -> str:
    """Remplace /dev/ttyUSBx par le lien /dev/serial/by-id/... si possible."""
    for port_info in serial.tools.list_ports.comports():
        if port_info.device == port:
            by_id_path = "/dev/serial/by-id"
            if os.path.exists(by_id_path):
                for entry in os.listdir(by_id_path):
                    full_path = os.path.join(by_id_path, entry)
                    if os.path.realpath(full_path) == os.path.realpath(port):
                        return full_path
    return port

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    resolved_port = resolve_by_id_path(entry.data["port"])
    entry.data["port"] = resolved_port

    coordinator = USBRelayCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_unload_platforms(entry, ["switch"])
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
