from future import annotations import logging from homeassistant.core import HomeAssistant from homeassistant.config_entries import ConfigEntry from homeassistant.helpers.typing import ConfigType from .const import DOMAIN from .coordinator import USBRelayCoordinator

_LOGGER = logging.getLogger(name)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool: """Set up the USB Relay component.""" return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool: """Set up USB Relay from a config entry.""" coordinator = USBRelayCoordinator(hass, entry.data) await coordinator.async_config_entry_first_refresh()

hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

hass.async_create_task(
    hass.config_entries.async_forward_entry_setup(entry, "switch")
)

return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool: """Unload a config entry.""" await hass.config_entries.async_forward_entry_unload(entry, "switch") hass.data[DOMAIN].pop(entry.entry_id) return True
