"""Tests that translation files cover every entity translation_key."""
import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "custom_components" / "dspico"

EXPECTED_SENSORS = {
    "battery",
    "wifi_signal",
    "rtc",
    "nickname",
    "color",
    "language",
    "last_seen",
}
EXPECTED_BINARY = {"presence", "charging"}


def _load(name):
    return json.loads((BASE / name).read_text())


def test_strings_and_translations_match():
    for fname in ("strings.json", "translations/en.json", "translations/pt-BR.json"):
        data = _load(fname)
        assert set(data["entity"]["sensor"]) == EXPECTED_SENSORS, fname
        assert set(data["entity"]["binary_sensor"]) == EXPECTED_BINARY, fname
        assert "user" in data["config"]["step"], fname
        assert "confirm" in data["config"]["step"], fname
