"""Tests for DSpico binary sensors."""
from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from homeassistant.util import dt as dt_util

from custom_components.dspico.const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN


@pytest.fixture
async def setup_entry(hass):
    assert await async_setup_component(hass, "webhook", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DSi Quarto",
        data={CONF_NAME: "DSi Quarto", CONF_WEBHOOK_ID: "abc123"},
        unique_id="abc123",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    if entry.state is ConfigEntryState.LOADED:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def _post(client, body):
    return await client.post("/api/webhook/abc123", json=body)


async def test_presence_on_after_post(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await _post(client, {"device": "dsi", "battery": {"charging": True}})
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "on"
    assert hass.states.get("binary_sensor.dsi_quarto_charging").state == "on"


async def test_presence_off_after_timeout(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await _post(client, {"device": "dsi"})
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "on"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=91))
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "off"
