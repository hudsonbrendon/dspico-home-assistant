"""Constants for the DSpico integration."""
from __future__ import annotations

DOMAIN = "dspico"

CONF_WEBHOOK_ID = "webhook_id"
CONF_NAME = "name"

DEFAULT_INTERVAL = 30  # seconds between expected POSTs
TIMEOUT_FACTOR = 3  # device considered offline after INTERVAL * FACTOR

# Dispatcher signal, formatted with the config entry_id.
SIGNAL_UPDATE = "dspico_update_{}"

PLATFORMS = ["binary_sensor", "sensor"]
