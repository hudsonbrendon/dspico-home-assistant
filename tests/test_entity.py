"""Tests for the DSpico entity base."""
from custom_components.dspico.data import DspicoData
from custom_components.dspico.entity import DspicoEntity


class _Probe(DspicoEntity):
    _attr_name = "Probe"

    @property
    def native_value(self):
        return self.store.fields.get("battery_level")


def test_device_info_and_unique_id(hass):
    store = DspicoData(hass, "entry1", 30)
    ent = _Probe(store, "entry1", "DSi Quarto", "battery_level")
    assert ent.unique_id == "entry1_battery_level"
    assert ent.device_info["identifiers"] == {("dspico", "entry1")}
    assert ent.device_info["name"] == "DSi Quarto"


def test_availability_follows_store(hass):
    store = DspicoData(hass, "entry1", 30)
    ent = _Probe(store, "entry1", "DSi Quarto", "battery_level")
    assert ent.available is False
    store.update({"device": "dsi", "battery_level": 50})
    assert ent.available is True
    store.shutdown()
