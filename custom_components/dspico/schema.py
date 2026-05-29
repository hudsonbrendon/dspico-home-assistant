"""Validation and flattening for DSpico telemetry payloads."""
from __future__ import annotations

from typing import Any

import voluptuous as vol


def _strict_int(value: Any) -> int:
    """Accept real integers only — reject bool (a subclass of int)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise vol.Invalid("expected an integer")
    return value


_BATTERY = vol.Schema(
    {
        vol.Optional("level"): vol.All(_strict_int, vol.Range(min=0, max=100)),
        vol.Optional("charging"): bool,
    },
    extra=vol.REMOVE_EXTRA,
)

_IDENTITY = vol.Schema(
    {
        vol.Optional("nickname"): vol.All(str, vol.Length(max=32)),
        vol.Optional("color"): vol.All(_strict_int, vol.Range(min=0, max=15)),
        vol.Optional("language"): vol.All(str, vol.Length(max=8)),
    },
    extra=vol.REMOVE_EXTRA,
)

_WIFI = vol.Schema(
    {
        vol.Optional("rssi"): vol.All(_strict_int, vol.Range(min=-120, max=0)),
        vol.Optional("ssid"): vol.All(str, vol.Length(max=64)),
    },
    extra=vol.REMOVE_EXTRA,
)

TELEMETRY_SCHEMA = vol.Schema(
    {
        vol.Required("device"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Optional("fw"): vol.All(str, vol.Length(max=64)),
        vol.Optional("battery"): _BATTERY,
        vol.Optional("rtc"): vol.All(str, vol.Length(max=32)),
        vol.Optional("identity"): _IDENTITY,
        vol.Optional("wifi"): _WIFI,
        vol.Optional("uptime_s"): vol.All(_strict_int, vol.Range(min=0)),
    },
    extra=vol.REMOVE_EXTRA,
)


def parse_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and flatten a telemetry payload into a flat dict.

    Raises vol.Invalid for malformed payloads. Missing optional fields are
    returned as None so entities render as 'unknown'. Unknown keys are stripped.
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
