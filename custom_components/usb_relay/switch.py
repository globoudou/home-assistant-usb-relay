from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [USBRelaySwitch(coordinator, i) for i in range(entry.data["relay_count"])]
    async_add_entities(entities)

class USBRelaySwitch(SwitchEntity):
    def __init__(self, coordinator, relay_id: int):
        self.coordinator = coordinator
        self._relay_id = relay_id

    @property
    def name(self):
        return f"USB Relay {self._relay_id + 1}"

    @property
    def is_on(self):
        if self.coordinator.data:
            return self.coordinator.data[self._relay_id] == 1
        return False

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_switch(self._relay_id, 1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_switch(self._relay_id, 0)

    async def async_update(self):
        await self.coordinator.async_request_refresh()
