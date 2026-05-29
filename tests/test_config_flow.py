"""Tests for the DSpico config flow."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dspico.const import (
    CONF_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)


async def test_user_flow_creates_entry(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "DSi Quarto"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "DSi Quarto"
    assert result["data"][CONF_NAME] == "DSi Quarto"
    assert result["data"][CONF_WEBHOOK_ID]  # generated, non-empty


async def test_multiple_entries_allowed(hass: HomeAssistant):
    for name in ("DSi A", "DSi B"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: name}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2
