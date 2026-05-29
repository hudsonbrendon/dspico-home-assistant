"""Sensors for DSpico."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from . import DspicoConfigEntry
from .const import CONF_NAME
from .data import DspicoData
from .entity import DspicoEntity


def _field(key: str) -> Callable[[DspicoData], StateType]:
    """Return a value_fn that reads a flat field from the store."""
    return lambda store: store.fields.get(key)


def _rtc(store: DspicoData) -> datetime | None:
    value = store.fields.get("rtc")
    if value is None:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    # The device RTC is a naive local timestamp. With zoneinfo, replace() does a
    # wall-clock interpretation; fold=0 is assumed during the DST overlap hour
    # (the device gives us no information to disambiguate it).
    return parsed.replace(tzinfo=dt_util.get_default_time_zone())


@dataclass(frozen=True, kw_only=True)
class DspicoSensorDescription(SensorEntityDescription):
    """Describes a DSpico sensor and how to derive its value from the store."""

    value_fn: Callable[[DspicoData], StateType | datetime | None]


SENSORS: tuple[DspicoSensorDescription, ...] = (
    DspicoSensorDescription(
        key="battery_level",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_field("battery_level"),
    ),
    DspicoSensorDescription(
        key="rssi",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_field("rssi"),
    ),
    DspicoSensorDescription(
        key="rtc",
        translation_key="rtc",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_rtc,
    ),
    DspicoSensorDescription(
        key="nickname",
        translation_key="nickname",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_field("nickname"),
    ),
    DspicoSensorDescription(
        key="color",
        translation_key="color",
        icon="mdi:palette",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_field("color"),
    ),
    DspicoSensorDescription(
        key="language",
        translation_key="language",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_field("language"),
    ),
    DspicoSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda store: store.last_seen,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DspicoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        DspicoSensor(store, entry.entry_id, name, desc) for desc in SENSORS
    )


class DspicoSensor(DspicoEntity, SensorEntity):
    """A single DSpico telemetry value."""

    entity_description: DspicoSensorDescription

    def __init__(
        self,
        store: DspicoData,
        entry_id: str,
        name: str,
        description: DspicoSensorDescription,
    ) -> None:
        super().__init__(store, entry_id, name, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        return self.entity_description.value_fn(self.store)
