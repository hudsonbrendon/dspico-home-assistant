"""Tests for DSpico sensors."""
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


def _state(hass, entry, key):
    ent_reg = er.async_get(hass)
    eid = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
    assert eid is not None, f"no entity for key {key}"
    return hass.states.get(eid)


async def test_sensor_values(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await client.post(
        "/api/webhook/abc123",
        json={
            "device": "dsi",
            "battery": {"level": 80, "charging": True},
            "rtc": "2026-05-27T14:32:10",
            "identity": {"nickname": "Hudson", "color": 4, "language": "pt"},
            "wifi": {"rssi": -57, "ssid": "99lab"},
            "uptime_s": 134,
        },
    )
    await hass.async_block_till_done()

    assert _state(hass, setup_entry, "battery_level").state == "80"
    assert _state(hass, setup_entry, "rssi").state == "-57"
    assert _state(hass, setup_entry, "nickname").state == "Hudson"
    assert _state(hass, setup_entry, "color").state == "4"
    assert _state(hass, setup_entry, "language").state == "pt"

    # rtc is parsed to a timezone-aware timestamp.
    rtc_state = _state(hass, setup_entry, "rtc").state
    parsed = dt_util.parse_datetime(rtc_state)
    assert parsed is not None
    assert parsed.tzinfo is not None
    # last_seen is set by the store on update.
    assert _state(hass, setup_entry, "last_seen").state not in (
        "unknown",
        "unavailable",
    )


async def test_missing_field_is_unknown(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await client.post("/api/webhook/abc123", json={"device": "dsi"})
    await hass.async_block_till_done()
    assert _state(hass, setup_entry, "battery_level").state == "unknown"
