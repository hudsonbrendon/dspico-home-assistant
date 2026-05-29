"""Webhook handler for DSpico telemetry."""
from __future__ import annotations

import json
import logging

import voluptuous as vol
from aiohttp.web import Request, Response
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_UPDATE
from .data import DspicoData
from .schema import parse_payload

_LOGGER = logging.getLogger(__name__)


def make_handler(store: DspicoData):
    """Build a webhook handler bound to a runtime store."""

    async def handler(
        hass: HomeAssistant, webhook_id: str, request: Request
    ) -> Response:
        try:
            raw = await request.json()
        except (ValueError, json.JSONDecodeError):
            _LOGGER.debug("DSpico webhook %s: body was not JSON", webhook_id)
            return Response(status=400)
        try:
            fields = parse_payload(raw)
        except vol.Invalid as err:
            _LOGGER.debug("DSpico webhook %s: invalid payload: %s", webhook_id, err)
            return Response(status=400)

        try:
            store.update(fields)
            async_dispatcher_send(hass, SIGNAL_UPDATE.format(store.entry_id))
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "DSpico webhook %s: unexpected error updating store", webhook_id
            )
            return Response(status=500)
        return Response(status=200)

    return handler
