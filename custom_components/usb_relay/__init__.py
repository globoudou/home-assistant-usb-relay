"""The USB Relay integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_PORT, CONF_RELAY_COUNT, DOMAIN
from .coordinator import USBRelayConfigEntry, USBRelayCoordinator
from .helpers import resolve_by_id

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: USBRelayConfigEntry) -> bool:
    """Set up a USB relay board from a config entry."""
    if entry.unique_id is None and not any(
        other.unique_id == entry.data[CONF_PORT]
        for other in hass.config_entries.async_entries(DOMAIN)
    ):
        # Entries created before 1.3.2 have no unique ID.
        hass.config_entries.async_update_entry(entry, unique_id=entry.data[CONF_PORT])

    # Prefer the stable /dev/serial/by-id link over /dev/ttyUSBx.
    port = await hass.async_add_executor_job(resolve_by_id, entry.data[CONF_PORT])

    coordinator = USBRelayCoordinator(hass, entry, port, int(entry.data[CONF_RELAY_COUNT]))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: USBRelayConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
