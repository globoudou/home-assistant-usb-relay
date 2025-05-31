import voluptuous as vol

from homeassistant import config_entries
from .const import DOMAIN, DEFAULT_PORT, DEFAULT_RELAY_COUNT

class USBRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="USB Relay", data=user_input)

        data_schema = vol.Schema({
            vol.Required("port", default=DEFAULT_PORT): str,
            vol.Optional("relay_count", default=DEFAULT_RELAY_COUNT): int,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)