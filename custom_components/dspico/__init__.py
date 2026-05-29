"""The DSpico integration."""
from __future__ import annotations

import homeassistant.components.webhook as ha_webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_NAME,
    CONF_WEBHOOK_ID,
    DEFAULT_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SIGNAL_UPDATE,
)
from .data import DspicoData
from .webhook import make_handler

type DspicoConfigEntry = ConfigEntry[DspicoData]


async def async_setup_entry(hass: HomeAssistant, entry: DspicoConfigEntry) -> bool:
    """Set up DSpico from a config entry."""
    store = DspicoData(hass, entry.entry_id, DEFAULT_INTERVAL)
    store.set_offline_callback(
        lambda: async_dispatcher_send(hass, SIGNAL_UPDATE.format(entry.entry_id))
    )
    entry.runtime_data = store

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    ha_webhook.async_register(
        hass,
        DOMAIN,
        entry.data[CONF_NAME],
        webhook_id,
        make_handler(store),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DspicoConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        ha_webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        entry.runtime_data.shutdown()
    return unload_ok
