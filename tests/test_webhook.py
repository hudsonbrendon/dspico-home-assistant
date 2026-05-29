"""Tests for the DSpico webhook handler and setup."""
from http import HTTPStatus

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dspico.const import (
    CONF_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)


@pytest.fixture
async def setup_entry(hass: HomeAssistant):
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


async def test_valid_post_updates_store(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post(
        "/api/webhook/abc123",
        json={"device": "dsi", "battery": {"level": 77, "charging": False}},
    )
    assert resp.status == HTTPStatus.OK
    store = setup_entry.runtime_data
    assert store.fields["battery_level"] == 77
    assert store.available is True


async def test_invalid_post_returns_400(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post("/api/webhook/abc123", json={"battery": {"level": 5}})
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_non_json_returns_400(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post("/api/webhook/abc123", data=b"not json")
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unload_unregisters_webhook(hass, setup_entry):
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    from homeassistant.components import webhook

    webhook.async_register(hass, DOMAIN, "x", "abc123", lambda *a: None)
    webhook.async_unregister(hass, "abc123")
