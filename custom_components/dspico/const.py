"""Constants for the DSpico integration."""
from __future__ import annotations

from typing import Final

from homeassistant.const import CONF_NAME, CONF_WEBHOOK_ID, Platform

DOMAIN: Final = "dspico"

# CONF_NAME / CONF_WEBHOOK_ID are re-exported from homeassistant.const so call
# sites can keep doing `from .const import CONF_NAME, CONF_WEBHOOK_ID`.
__all__ = [
    "DOMAIN",
    "CONF_NAME",
    "CONF_WEBHOOK_ID",
    "DEFAULT_INTERVAL",
    "TIMEOUT_FACTOR",
    "SIGNAL_UPDATE",
    "PLATFORMS",
]

DEFAULT_INTERVAL: Final = 30  # seconds between expected webhook POSTs
TIMEOUT_FACTOR: Final = 3  # offline threshold = DEFAULT_INTERVAL * TIMEOUT_FACTOR (90 s)

# Dispatcher signal, formatted positionally with the entry_id:
# SIGNAL_UPDATE.format(entry_id)
SIGNAL_UPDATE: Final = "dspico_update_{}"

PLATFORMS: Final[list[Platform]] = [Platform.BINARY_SENSOR, Platform.SENSOR]
