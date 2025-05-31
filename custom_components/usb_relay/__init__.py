DOMAIN = "usb_relay"

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )
    return True

async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_forward_entry_unload(entry, "switch")