"""Tests for DSpico constants."""
from custom_components.dspico import const


def test_constants_present():
    assert const.DOMAIN == "dspico"
    assert const.CONF_WEBHOOK_ID == "webhook_id"
    assert const.CONF_NAME == "name"
    assert const.DEFAULT_INTERVAL == 30
    assert const.TIMEOUT_FACTOR == 3
    assert const.SIGNAL_UPDATE == "dspico_update_{}"
    assert const.PLATFORMS == ["binary_sensor", "sensor"]
