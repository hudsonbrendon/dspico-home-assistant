"""Runtime data store and availability watchdog for DSpico."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import TIMEOUT_FACTOR


class DspicoData:
    """Holds the latest telemetry and tracks availability via heartbeat.

    A single offline callback is supported (last registration wins).
    ``entry_id`` is exposed for callers (e.g. dispatcher signals) and is not
    used internally.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, interval: int) -> None:
        self._hass = hass
        self.entry_id = entry_id
        self._timeout = timedelta(seconds=interval * TIMEOUT_FACTOR)
        self.fields: dict[str, Any] = {}
        self._last_seen: datetime | None = None
        self._cancel_watchdog: Callable[[], None] | None = None
        self._offline_cb: Callable[[], None] | None = None
        self._available: bool = False

    @property
    def available(self) -> bool:
        if self._last_seen is None:
            return False
        if not self._available:
            return False
        return dt_util.utcnow() - self._last_seen < self._timeout

    def set_offline_callback(self, cb: Callable[[], None]) -> None:
        self._offline_cb = cb

    @callback
    def update(self, fields: dict[str, Any]) -> None:
        """Record a fresh payload and (re)arm the offline watchdog."""
        self.fields = fields
        self._last_seen = dt_util.utcnow()
        self._available = True
        if self._cancel_watchdog is not None:
            self._cancel_watchdog()
        self._cancel_watchdog = async_call_later(
            self._hass, self._timeout.total_seconds(), self._handle_timeout
        )

    @callback
    def _handle_timeout(self, _now: datetime) -> None:
        # If the handle fired naturally, the cancellation function is a no-op;
        # keep it so that a manual call in tests doesn't strand the live timer.
        self._available = False
        if self._offline_cb is not None:
            self._offline_cb()

    @callback
    def shutdown(self) -> None:
        if self._cancel_watchdog is not None:
            self._cancel_watchdog()
            self._cancel_watchdog = None
