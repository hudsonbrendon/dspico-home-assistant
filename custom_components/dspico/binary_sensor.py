"""Binary sensors for DSpico."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DspicoConfigEntry
from .const import CONF_NAME
from .entity import DspicoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DspicoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = entry.runtime_data
    name = entry.data[CONF_NAME]
    async_add_entities(
        [
            DspicoPresence(store, entry.entry_id, name),
            DspicoCharging(store, entry.entry_id, name),
        ]
    )


class DspicoPresence(DspicoEntity, BinarySensorEntity):
    _attr_translation_key = "presence"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, store, entry_id, name):
        super().__init__(store, entry_id, name, "presence")

    @property
    def available(self) -> bool:
        # Presence must report even when offline, so it is always available.
        return True

    @property
    def is_on(self) -> bool | None:
        return self.store.available


class DspicoCharging(DspicoEntity, BinarySensorEntity):
    _attr_translation_key = "charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, store, entry_id, name):
        super().__init__(store, entry_id, name, "charging")

    @property
    def is_on(self) -> bool | None:
        return self.store.fields.get("charging")
