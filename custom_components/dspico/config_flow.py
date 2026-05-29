"""Config flow for the DSpico integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.network import NoURLAvailableError

from .const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN

_USER_SCHEMA = vol.Schema({vol.Required(CONF_NAME): str})


class DspicoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DSpico."""

    VERSION = 1

    def __init__(self) -> None:
        self._name: str | None = None
        self._webhook_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA)

        self._name = user_input[CONF_NAME]
        self._webhook_id = webhook.async_generate_id()
        await self.async_set_unique_id(self._webhook_id)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._name is not None
        assert self._webhook_id is not None
        if user_input is None:
            try:
                webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)
            except NoURLAvailableError:
                webhook_url = f"/api/webhook/{self._webhook_id}"
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({}),
                description_placeholders={"webhook_url": webhook_url},
            )
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_NAME: self._name,
                CONF_WEBHOOK_ID: self._webhook_id,
            },
        )
