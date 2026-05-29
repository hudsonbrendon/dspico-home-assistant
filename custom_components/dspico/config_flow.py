"""Config flow for the DSpico integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN

_USER_SCHEMA = vol.Schema({vol.Required(CONF_NAME): str})


class DspicoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DSpico."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA)

        webhook_id = webhook.async_generate_id()
        await self.async_set_unique_id(webhook_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data={
                CONF_NAME: user_input[CONF_NAME],
                CONF_WEBHOOK_ID: webhook_id,
            },
        )
