"""Tests for the DSpico config flow."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dspico.const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN


async def _run_flow(hass: HomeAssistant, name: str):
    """Drive the two-step flow (user -> confirm) and return the final result."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: name}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert "webhook_url" in result["description_placeholders"]

    return await hass.config_entries.flow.async_configure(result["flow_id"], {})


async def test_user_flow_creates_entry(hass: HomeAssistant):
    result = await _run_flow(hass, "DSi Quarto")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "DSi Quarto"
    assert result["data"][CONF_NAME] == "DSi Quarto"
    assert isinstance(result["data"][CONF_WEBHOOK_ID], str)
    assert result["data"][CONF_WEBHOOK_ID]


async def test_multiple_entries_allowed(hass: HomeAssistant):
    r1 = await _run_flow(hass, "DSi A")
    r2 = await _run_flow(hass, "DSi B")
    assert r1["type"] == FlowResultType.CREATE_ENTRY
    assert r2["type"] == FlowResultType.CREATE_ENTRY
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    ids = [e.data[CONF_WEBHOOK_ID] for e in entries]
    assert ids[0] != ids[1]
