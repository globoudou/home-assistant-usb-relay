class USBRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        ports = await self.hass.async_add_executor_job(detect_usb_relays)
        if not ports:
            return self.async_abort(reason="no_devices_found")

        self.detected_ports = {p[0]: p[1] for p in ports}  # stocke {port: relay_count}
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
