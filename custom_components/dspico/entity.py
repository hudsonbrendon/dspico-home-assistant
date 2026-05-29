"""Base entity for DSpico."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_UPDATE
from .data import DspicoData


class DspicoEntity(Entity):
    """Shared behaviour for DSpico entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self, store: DspicoData, entry_id: str, device_name: str, key: str
    ) -> None:
        self.store = store
        self._entry_id = entry_id
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=device_name,
            manufacturer="Nintendo",
            model="DSi (DSpico)",
        )

    @property
    def available(self) -> bool:
        return self.store.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE.format(self._entry_id),
                self.async_write_ha_state,
            )
        )
