"""Sensors for DSpico."""
from __future__ import annotations

from dataclasses import dataclass

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
from homeassistant.util import dt as dt_util

from . import DspicoConfigEntry
from .const import CONF_NAME
from .entity import DspicoEntity


@dataclass(frozen=True, kw_only=True)
class DspicoSensorDescription(SensorEntityDescription):
    """Describes a DSpico sensor."""


SENSORS: tuple[DspicoSensorDescription, ...] = (
    DspicoSensorDescription(
        key="battery_level",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DspicoSensorDescription(
        key="rssi",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DspicoSensorDescription(
        key="rtc",
        translation_key="rtc",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    DspicoSensorDescription(
        key="nickname",
        translation_key="nickname",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DspicoSensorDescription(
        key="color",
        translation_key="color",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DspicoSensorDescription(
        key="language",
        translation_key="language",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DspicoSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
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

    def __init__(self, store, entry_id, name, description: DspicoSensorDescription):
        super().__init__(store, entry_id, name, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        if self._key == "last_seen":
            return self.store.last_seen
        value = self.store.fields.get(self._key)
        if self._key == "rtc" and value is not None:
            parsed = dt_util.parse_datetime(value)
            if parsed is None:
                return None
            return parsed.replace(tzinfo=dt_util.get_default_time_zone())
        return value
