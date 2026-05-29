"""Tests for the DSpico runtime data store."""
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util

from custom_components.dspico.data import DspicoData


@pytest.fixture
def store(hass):
    s = DspicoData(hass, entry_id="abc", interval=30)
    yield s
    s.shutdown()


def test_starts_unavailable(store):
    assert store.available is False
    assert store.fields == {}


def test_update_marks_available(store):
    store.update({"device": "dsi", "battery_level": 50})
    assert store.available is True
    assert store.fields["battery_level"] == 50


def test_goes_offline_after_timeout(store, freezer):
    store.update({"device": "dsi"})
    assert store.available is True
    freezer.tick(timedelta(seconds=91))  # 30 * 3 + 1
    assert store.available is False


def test_offline_callback_fires(hass, store):
    fired = []
    store.set_offline_callback(lambda: fired.append(True))
    store.update({"device": "dsi"})
    # Simulate the watchdog firing.
    store._handle_timeout(dt_util.utcnow())
    assert fired == [True]


async def test_watchdog_fires_callback_after_timeout(hass, store):
    """The real async_call_later timer must invoke the offline callback."""
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    fired = []
    store.set_offline_callback(lambda: fired.append(True))
    store.update({"device": "dsi"})
    async_fire_time_changed(
        hass, dt_util.utcnow() + store._timeout + timedelta(seconds=1)
    )
    await hass.async_block_till_done()
    assert fired == [True]
