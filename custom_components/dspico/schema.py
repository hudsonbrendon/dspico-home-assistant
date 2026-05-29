"""Validation and flattening for DSpico telemetry payloads."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

_BATTERY = vol.Schema(
    {
        vol.Optional("level"): vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional("charging"): bool,
    }
)

_IDENTITY = vol.Schema(
    {
        vol.Optional("nickname"): str,
        vol.Optional("color"): vol.All(int, vol.Range(min=0, max=15)),
        vol.Optional("language"): str,
    }
)

_WIFI = vol.Schema(
    {
        vol.Optional("rssi"): vol.All(int, vol.Range(min=-120, max=0)),
        vol.Optional("ssid"): str,
    }
)

TELEMETRY_SCHEMA = vol.Schema(
    {
        vol.Required("device"): str,
        vol.Optional("fw"): str,
        vol.Optional("battery"): _BATTERY,
        vol.Optional("rtc"): str,
        vol.Optional("identity"): _IDENTITY,
        vol.Optional("wifi"): _WIFI,
        vol.Optional("uptime_s"): vol.All(int, vol.Range(min=0)),
    }
)


def parse_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and flatten a telemetry payload into a flat dict.

    Raises vol.Invalid for malformed payloads. Missing optional fields are
    returned as None so entities render as 'unknown'.
    """
    data = TELEMETRY_SCHEMA(raw)
    battery = data.get("battery", {})
    identity = data.get("identity", {})
    wifi = data.get("wifi", {})
    return {
        "device": data["device"],
        "fw": data.get("fw"),
        "battery_level": battery.get("level"),
        "charging": battery.get("charging"),
        "rtc": data.get("rtc"),
        "nickname": identity.get("nickname"),
        "color": identity.get("color"),
        "language": identity.get("language"),
        "rssi": wifi.get("rssi"),
        "ssid": wifi.get("ssid"),
        "uptime_s": data.get("uptime_s"),
    }
