"""Switch platform for the USB Relay integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import USBRelayConfigEntry, USBRelayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: USBRelayConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one switch per relay."""
    coordinator = entry.runtime_data
    async_add_entities(USBRelaySwitch(coordinator, idx) for idx in range(coordinator.relay_count))


class USBRelaySwitch(CoordinatorEntity[USBRelayCoordinator], SwitchEntity):
    """One relay of the board."""

    _attr_has_entity_name = True
    _attr_translation_key = "relay"

    def __init__(self, coordinator: USBRelayCoordinator, relay_idx: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._idx = relay_idx
        self._attr_translation_placeholders = {"index": str(relay_idx + 1)}
        # Same format as previous versions so existing entities are kept.
        self._attr_unique_id = f"usb_relay::{coordinator.port}::{relay_idx + 1}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="USB Relay",
            model=f"{coordinator.relay_count}-channel USB relay board (CH340)",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the relay is on."""
        data = self.coordinator.data
        if not data or self._idx >= len(data):
            return None
        return data[self._idx] == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the relay on."""
        await self.coordinator.async_switch(self._idx, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the relay off."""
        await self.coordinator.async_switch(self._idx, False)
