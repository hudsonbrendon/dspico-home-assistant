"""Tests for the DSpico payload schema."""
import pytest
import voluptuous as vol

from custom_components.dspico.schema import TELEMETRY_SCHEMA, parse_payload


def _full_payload():
    return {
        "device": "dsi-quarto",
        "fw": "ds-ha-bridge 0.1.0",
        "battery": {"level": 80, "charging": True},
        "rtc": "2026-05-27T14:32:10",
        "identity": {"nickname": "Hudson", "color": 4, "language": "pt"},
        "wifi": {"rssi": -57, "ssid": "99lab"},
        "uptime_s": 134,
    }


def test_full_payload_parses():
    parsed = parse_payload(_full_payload())
    assert parsed["device"] == "dsi-quarto"
    assert parsed["battery_level"] == 80
    assert parsed["charging"] is True
    assert parsed["nickname"] == "Hudson"
    assert parsed["color"] == 4
    assert parsed["language"] == "pt"
    assert parsed["rssi"] == -57
    assert parsed["ssid"] == "99lab"
    assert parsed["uptime_s"] == 134
    assert parsed["rtc"] == "2026-05-27T14:32:10"


def test_minimal_payload_fills_none():
    parsed = parse_payload({"device": "dsi"})
    assert parsed["device"] == "dsi"
    assert parsed["battery_level"] is None
    assert parsed["charging"] is None
    assert parsed["nickname"] is None
    assert parsed["rssi"] is None


def test_missing_device_is_invalid():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"battery": {"level": 50}})


def test_out_of_range_battery_is_invalid():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"device": "dsi", "battery": {"level": 250}})


def test_bool_rejected_for_int_fields():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"device": "dsi", "battery": {"level": True}})


def test_empty_device_is_invalid():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"device": ""})


def test_unknown_keys_are_stripped():
    data = TELEMETRY_SCHEMA(
        {"device": "dsi", "bogus": 1, "wifi": {"rssi": -50, "x": 9}}
    )
    assert "bogus" not in data
    assert "x" not in data["wifi"]


def test_range_boundaries_valid():
    parsed = parse_payload(
        {"device": "dsi", "battery": {"level": 0}, "wifi": {"rssi": -120}}
    )
    assert parsed["battery_level"] == 0
    assert parsed["rssi"] == -120
    parsed = parse_payload(
        {"device": "dsi", "battery": {"level": 100}, "wifi": {"rssi": 0}}
    )
    assert parsed["battery_level"] == 100
    assert parsed["rssi"] == 0
