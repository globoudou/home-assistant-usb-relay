from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    count = int(entry.data["relay_count"])
    entities = [USBRelaySwitch(coordinator, i) for i in range(count)]
    async_add_entities(entities)

class USBRelaySwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, relay_idx: int):
        super().__init__(coordinator)
        self._idx = relay_idx
        # Nom lisible et identifiant stable (basé sur le port et l'index)
        self._attr_name = f"Relay {relay_idx + 1}"
        self._attr_unique_id = f"usb_relay::{getattr(coordinator, 'port', 'unknown')}::{relay_idx+1}"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        if not data or self._idx >= len(data):
            return False
        return data[self._idx] == 1

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_switch(self._idx, 1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_switch(self._idx, 0)
