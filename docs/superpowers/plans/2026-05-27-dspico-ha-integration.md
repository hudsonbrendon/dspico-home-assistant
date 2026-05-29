# DSpico Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Home Assistant custom integration (`dspico`) that receives JSON telemetry from a Nintendo DSi over a webhook and exposes it as sensors/binary_sensors with heartbeat-based availability.

**Architecture:** A config-flow integration registers an HA webhook on setup. The DSi `POST`s JSON to that webhook; a handler validates the payload, stores it in a per-entry runtime object, and dispatches updates to entities. A watchdog marks the device unavailable when no POST arrives within `interval * 3`.

**Tech Stack:** Python 3.12+, Home Assistant, `voluptuous` (validation), `pytest` + `pytest-homeassistant-custom-component` (TDD).

This plan is one of two; the other is `2026-05-27-ds-ha-bridge-homebrew.md` (the DSi app). They share the JSON contract in `docs/superpowers/specs/2026-05-27-dspico-home-assistant-design.md` §4. This plan is fully testable on its own using simulated POSTs.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `custom_components/dspico/manifest.json` | Integration metadata (hassfest key order). |
| `custom_components/dspico/const.py` | Domain, defaults, config keys, dispatcher signal. |
| `custom_components/dspico/schema.py` | `voluptuous` schema + parser for the telemetry payload. |
| `custom_components/dspico/data.py` | `DspicoData` runtime store + availability watchdog. |
| `custom_components/dspico/__init__.py` | Setup/unload entry, webhook register/unregister, platform forwarding. |
| `custom_components/dspico/webhook.py` | Webhook handler: validate → store → dispatch. |
| `custom_components/dspico/config_flow.py` | User config flow, generates `webhook_id`. |
| `custom_components/dspico/entity.py` | `DspicoEntity` base (device_info, availability, dispatcher). |
| `custom_components/dspico/binary_sensor.py` | `presence`, `charging`. |
| `custom_components/dspico/sensor.py` | `battery`, `rtc`, `wifi_rssi`, `nickname`, `color`, `language`, `last_seen`. |
| `custom_components/dspico/strings.json` + `translations/en.json` + `translations/pt-BR.json` | UI strings. |
| `hacs.json` | HACS metadata. |
| `requirements-test.txt` | Test dependencies. |
| `tests/conftest.py` | Pytest fixtures (`enable_custom_integrations`, payload factory, entry factory). |
| `tests/test_*.py` | One test module per source module. |
| `.github/workflows/validate.yml` | hassfest + HACS + pytest in CI. |

---

## Task 1: Project scaffold and test harness

**Files:**
- Create: `requirements-test.txt`
- Create: `custom_components/dspico/__init__.py`
- Create: `custom_components/dspico/manifest.json`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_init.py`

- [ ] **Step 1: Create the test requirements file**

Create `requirements-test.txt`:

```text
pytest-homeassistant-custom-component==0.13.190
```

- [ ] **Step 2: Create a virtualenv and install deps**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements-test.txt
```
Expected: installs `homeassistant` + `pytest` transitively, ends with `Successfully installed ...`.

- [ ] **Step 3: Create the manifest (hassfest key order)**

Create `custom_components/dspico/manifest.json` (keys: `domain`, `name` first, then alphabetical — this order passes hassfest):

```json
{
  "domain": "dspico",
  "name": "DSpico",
  "codeowners": ["@hudsonbrendon"],
  "config_flow": true,
  "dependencies": ["webhook"],
  "documentation": "https://github.com/hudsonbrendon/dspico-home-assistant",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/hudsonbrendon/dspico-home-assistant/issues",
  "version": "0.1.0"
}
```

- [ ] **Step 4: Create an empty integration module so HA can import it**

Create `custom_components/dspico/__init__.py`:

```python
"""The DSpico integration."""
```

- [ ] **Step 5: Create the test package and conftest**

Create `tests/__init__.py` (empty file).

Create `tests/conftest.py` (autouse but conditional: the plugin's
`enable_custom_integrations` transitively pulls in the async `hass` fixture, so
forcing it onto pure-sync tests fails — only activate it when the test uses
`hass`):

```python
"""Fixtures for DSpico tests."""
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    """Enable custom integrations only for tests that use Home Assistant."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
    yield
```

Also create `setup.cfg` so async tests run without per-function markers:

```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: Write a smoke test that the manifest loads**

Create `tests/test_init.py`:

```python
"""Smoke tests for the DSpico integration package."""
import json
from pathlib import Path


def test_manifest_is_valid_json():
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "dspico"
        / "manifest.json"
    )
    data = json.loads(manifest_path.read_text())
    assert data["domain"] == "dspico"
    assert data["config_flow"] is True
    assert "webhook" in data["dependencies"]
    assert data["iot_class"] == "local_push"
```

- [ ] **Step 7: Run the test**

Run: `.venv/bin/pytest tests/test_init.py -v`
Expected: PASS (1 passed).

- [ ] **Step 8: Commit**

```bash
git add requirements-test.txt custom_components/dspico tests
git commit -m "chore: scaffold dspico integration and test harness"
```

---

## Task 2: Constants

**Files:**
- Create: `custom_components/dspico/const.py`
- Test: `tests/test_const.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_const.py`:

```python
"""Tests for DSpico constants."""
from custom_components.dspico import const


def test_constants_present():
    assert const.DOMAIN == "dspico"
    assert const.CONF_WEBHOOK_ID == "webhook_id"
    assert const.CONF_NAME == "name"
    assert const.DEFAULT_INTERVAL == 30
    assert const.TIMEOUT_FACTOR == 3
    assert const.SIGNAL_UPDATE == "dspico_update_{}"
    assert const.PLATFORMS == ["binary_sensor", "sensor"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_const.py -v`
Expected: FAIL with `ModuleNotFoundError` or `AttributeError`.

- [ ] **Step 3: Write the implementation**

Create `custom_components/dspico/const.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_const.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/const.py tests/test_const.py
git commit -m "feat: add dspico constants"
```

---

## Task 3: Payload schema and parser

**Files:**
- Create: `custom_components/dspico/schema.py`
- Test: `tests/test_schema.py`

The schema validates the §4 contract. Missing optional keys are tolerated and
returned as `None`; an invalid payload raises `vol.Invalid`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_schema.py`:

```python
"""Tests for the DSpico payload schema."""
import pytest
import voluptuous as vol

from custom_components.dspico.schema import TELEMETRY_SCHEMA, parse_payload


def _full_payload():
    return {
        "device": "dsi-quarto",
        "fw": "ds-ha-bridge 0.1.0",
        "battery": {"level": 80, "charging": True},
        "rtc": "2026-05-27T14:32:10",
        "identity": {"nickname": "Hudson", "color": 4, "language": "pt"},
        "wifi": {"rssi": -57, "ssid": "99lab"},
        "uptime_s": 134,
    }


def test_full_payload_parses():
    parsed = parse_payload(_full_payload())
    assert parsed["device"] == "dsi-quarto"
    assert parsed["battery_level"] == 80
    assert parsed["charging"] is True
    assert parsed["nickname"] == "Hudson"
    assert parsed["color"] == 4
    assert parsed["language"] == "pt"
    assert parsed["rssi"] == -57
    assert parsed["ssid"] == "99lab"
    assert parsed["uptime_s"] == 134
    assert parsed["rtc"] == "2026-05-27T14:32:10"


def test_minimal_payload_fills_none():
    parsed = parse_payload({"device": "dsi"})
    assert parsed["device"] == "dsi"
    assert parsed["battery_level"] is None
    assert parsed["charging"] is None
    assert parsed["nickname"] is None
    assert parsed["rssi"] is None


def test_missing_device_is_invalid():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"battery": {"level": 50}})


def test_out_of_range_battery_is_invalid():
    with pytest.raises(vol.Invalid):
        TELEMETRY_SCHEMA({"device": "dsi", "battery": {"level": 250}})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: custom_components.dspico.schema`.

- [ ] **Step 3: Write the implementation**

Create `custom_components/dspico/schema.py`:

```python
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
    returned as None so entities render as 'unknown'.
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_schema.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/schema.py tests/test_schema.py
git commit -m "feat: add telemetry payload schema and parser"
```

---

## Task 4: Runtime data store with availability watchdog

**Files:**
- Create: `custom_components/dspico/data.py`
- Test: `tests/test_data.py`

`DspicoData` holds the latest parsed payload and `last_seen`. `available`
returns True while the last POST is within `interval * TIMEOUT_FACTOR`. A
watchdog scheduled with `async_call_later` invokes a callback when the device
goes offline so entities can refresh.

- [ ] **Step 1: Write the failing test**

Create `tests/test_data.py`:

```python
"""Tests for the DSpico runtime data store."""
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util

from custom_components.dspico.data import DspicoData


@pytest.fixture
def store(hass):
    return DspicoData(hass, entry_id="abc", interval=30)


def test_starts_unavailable(store):
    assert store.available is False
    assert store.fields == {}


def test_update_marks_available(store):
    store.update({"device": "dsi", "battery_level": 50})
    assert store.available is True
    assert store.fields["battery_level"] == 50


def test_goes_offline_after_timeout(store, freezer):
    store.update({"device": "dsi"})
    assert store.available is True
    freezer.tick(timedelta(seconds=91))  # 30 * 3 + 1
    assert store.available is False


def test_offline_callback_fires(hass, store):
    fired = []
    store.set_offline_callback(lambda: fired.append(True))
    store.update({"device": "dsi"})
    # Simulate the watchdog firing.
    store._handle_timeout(dt_util.utcnow())
    assert fired == [True]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_data.py -v`
Expected: FAIL with `ModuleNotFoundError: custom_components.dspico.data`.

- [ ] **Step 3: Write the implementation**

Create `custom_components/dspico/data.py`:

```python
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
    """Holds the latest telemetry and tracks availability via heartbeat."""

    def __init__(self, hass: HomeAssistant, entry_id: str, interval: int) -> None:
        self._hass = hass
        self.entry_id = entry_id
        self._timeout = timedelta(seconds=interval * TIMEOUT_FACTOR)
        self.fields: dict[str, Any] = {}
        self._last_seen: datetime | None = None
        self._cancel_watchdog: Callable[[], None] | None = None
        self._offline_cb: Callable[[], None] | None = None

    @property
    def available(self) -> bool:
        if self._last_seen is None:
            return False
        return dt_util.utcnow() - self._last_seen < self._timeout

    def set_offline_callback(self, cb: Callable[[], None]) -> None:
        self._offline_cb = cb

    @callback
    def update(self, fields: dict[str, Any]) -> None:
        """Record a fresh payload and (re)arm the offline watchdog."""
        self.fields = fields
        self._last_seen = dt_util.utcnow()
        if self._cancel_watchdog is not None:
            self._cancel_watchdog()
        self._cancel_watchdog = async_call_later(
            self._hass, self._timeout.total_seconds(), self._handle_timeout
        )

    @callback
    def _handle_timeout(self, _now: datetime) -> None:
        self._cancel_watchdog = None
        if self._offline_cb is not None:
            self._offline_cb()

    @callback
    def shutdown(self) -> None:
        if self._cancel_watchdog is not None:
            self._cancel_watchdog()
            self._cancel_watchdog = None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_data.py -v`
Expected: PASS (4 passed). (`freezer` is provided by `pytest-homeassistant-custom-component`'s bundled `pytest-freezer`.)

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/data.py tests/test_data.py
git commit -m "feat: add runtime data store with availability watchdog"
```

---

## Task 5: Config flow

**Files:**
- Create: `custom_components/dspico/config_flow.py`
- Test: `tests/test_config_flow.py`

The user enters a name; the flow generates a `webhook_id`, sets it as the
unique id, and stores `name` + `webhook_id` in the entry.

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_flow.py`:

```python
"""Tests for the DSpico config flow."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dspico.const import (
    CONF_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)


async def test_user_flow_creates_entry(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "DSi Quarto"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "DSi Quarto"
    assert result["data"][CONF_NAME] == "DSi Quarto"
    assert result["data"][CONF_WEBHOOK_ID]  # generated, non-empty


async def test_multiple_entries_allowed(hass: HomeAssistant):
    for name in ("DSi A", "DSi B"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: name}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_config_flow.py -v`
Expected: FAIL — config flow not found / cannot import.

- [ ] **Step 3: Write the implementation**

Create `custom_components/dspico/config_flow.py`:

```python
"""Config flow for the DSpico integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.network import NoURLAvailableError

from .const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN

_USER_SCHEMA = vol.Schema({vol.Required(CONF_NAME): str})


class DspicoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DSpico."""

    VERSION = 1

    def __init__(self) -> None:
        self._name: str | None = None
        self._webhook_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_USER_SCHEMA)

        self._name = user_input[CONF_NAME]
        self._webhook_id = webhook.async_generate_id()
        await self.async_set_unique_id(self._webhook_id)
        self._abort_if_unique_id_configured()
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._name is not None
        assert self._webhook_id is not None
        if user_input is None:
            try:
                webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)
            except NoURLAvailableError:
                webhook_url = f"/api/webhook/{self._webhook_id}"
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({}),
                description_placeholders={"webhook_url": webhook_url},
            )
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_NAME: self._name,
                CONF_WEBHOOK_ID: self._webhook_id,
            },
        )
```

The config flow has two steps: `user` collects the name and generates the
webhook id; `confirm` shows the generated webhook URL (via
`description_placeholders`) so the user can copy it into `dspico_ha.cfg`, then
creates the entry. `strings.json` (Task 10) must therefore include a `confirm`
step with a `{webhook_url}` placeholder.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_config_flow.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/config_flow.py tests/test_config_flow.py
git commit -m "feat: add config flow generating a webhook id"
```

---

## Task 6: Setup entry, webhook registration, and handler

**Files:**
- Create: `custom_components/dspico/webhook.py`
- Modify: `custom_components/dspico/__init__.py`
- Test: `tests/test_webhook.py`

`async_setup_entry` builds a `DspicoData`, registers the webhook, stores both
in `entry.runtime_data`, and forwards platforms. The handler validates the body
and updates the store, then dispatches `SIGNAL_UPDATE`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_webhook.py`:

```python
"""Tests for the DSpico webhook handler and setup."""
from http import HTTPStatus

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dspico.const import (
    CONF_NAME,
    CONF_WEBHOOK_ID,
    DOMAIN,
)


@pytest.fixture
async def setup_entry(hass: HomeAssistant):
    assert await async_setup_component(hass, "webhook", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DSi Quarto",
        data={CONF_NAME: "DSi Quarto", CONF_WEBHOOK_ID: "abc123"},
        unique_id="abc123",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    # Unload on teardown so the watchdog timer doesn't linger (verify_cleanup).
    if entry.state is ConfigEntryState.LOADED:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_valid_post_updates_store(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post(
        "/api/webhook/abc123",
        json={"device": "dsi", "battery": {"level": 77, "charging": False}},
    )
    assert resp.status == HTTPStatus.OK
    store = setup_entry.runtime_data
    assert store.fields["battery_level"] == 77
    assert store.available is True


async def test_invalid_post_returns_400(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post("/api/webhook/abc123", json={"battery": {"level": 5}})
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_non_json_returns_400(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    resp = await client.post("/api/webhook/abc123", data=b"not json")
    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_unload_unregisters_webhook(hass, setup_entry):
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    # Re-registering with the same id must now succeed (i.e. it was freed).
    from homeassistant.components import webhook

    webhook.async_register(hass, DOMAIN, "x", "abc123", lambda *a: None)
    webhook.async_unregister(hass, "abc123")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_webhook.py -v`
Expected: FAIL — `webhook.py` missing / setup not implemented.

- [ ] **Step 3: Write the webhook handler**

Create `custom_components/dspico/webhook.py`:

```python
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
```

- [ ] **Step 4: Implement setup/unload in `__init__.py`**

Replace the contents of `custom_components/dspico/__init__.py`:

```python
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
```

> **Import note:** the HA webhook module is imported as `ha_webhook`, NOT
> `from homeassistant.components import webhook`. Because this package also has a
> local `webhook.py` submodule (`from .webhook import make_handler`), importing
> that submodule binds the name `webhook` as a package attribute and would
> shadow the HA module — so a distinct alias is required.
> **Unload order:** unload platforms first; only unregister the webhook and
> `shutdown()` the store if the platform unload succeeded.

- [ ] **Step 5: Create placeholder platform modules so forwarding succeeds**

Create `custom_components/dspico/binary_sensor.py`:

```python
"""Binary sensors for DSpico (filled in Task 8)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback):
    return None
```

Create `custom_components/dspico/sensor.py`:

```python
"""Sensors for DSpico (filled in Task 9)."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback):
    return None
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_webhook.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add custom_components/dspico/__init__.py custom_components/dspico/webhook.py \
        custom_components/dspico/binary_sensor.py custom_components/dspico/sensor.py \
        tests/test_webhook.py
git commit -m "feat: register webhook, validate payload, update store on POST"
```

---

## Task 7: Entity base class

**Files:**
- Create: `custom_components/dspico/entity.py`
- Test: `tests/test_entity.py`

`DspicoEntity` provides shared `device_info`, availability from the store, and
dispatcher subscription so entities re-render on each POST and on offline.

- [ ] **Step 1: Write the failing test**

Create `tests/test_entity.py`:

```python
"""Tests for the DSpico entity base."""
from custom_components.dspico.data import DspicoData
from custom_components.dspico.entity import DspicoEntity


class _Probe(DspicoEntity):
    _attr_name = "Probe"

    @property
    def native_value(self):
        return self.store.fields.get("battery_level")


def test_device_info_and_unique_id(hass):
    store = DspicoData(hass, "entry1", 30)
    ent = _Probe(store, "entry1", "DSi Quarto", "battery_level")
    assert ent.unique_id == "entry1_battery_level"
    assert ent.device_info["identifiers"] == {("dspico", "entry1")}
    assert ent.device_info["name"] == "DSi Quarto"


def test_availability_follows_store(hass):
    store = DspicoData(hass, "entry1", 30)
    ent = _Probe(store, "entry1", "DSi Quarto", "battery_level")
    assert ent.available is False
    store.update({"device": "dsi", "battery_level": 50})
    assert ent.available is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_entity.py -v`
Expected: FAIL — `entity.py` missing.

- [ ] **Step 3: Write the implementation**

Create `custom_components/dspico/entity.py`:

```python
"""Base entity for DSpico."""
from __future__ import annotations

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.device_info import DeviceInfo
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_entity.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/entity.py tests/test_entity.py
git commit -m "feat: add DSpico entity base"
```

---

## Task 8: Binary sensors (presence, charging)

**Files:**
- Modify: `custom_components/dspico/binary_sensor.py`
- Test: `tests/test_binary_sensor.py`

`presence` is `connectivity` and reflects `store.available` (so it is `on`
whenever any entity is available and `off` after timeout). `charging` reflects
`battery.charging`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_binary_sensor.py`:

```python
"""Tests for DSpico binary sensors."""
from datetime import timedelta

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dspico.const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN


@pytest.fixture
async def setup_entry(hass):
    assert await async_setup_component(hass, "webhook", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DSi Quarto",
        data={CONF_NAME: "DSi Quarto", CONF_WEBHOOK_ID: "abc123"},
        unique_id="abc123",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _post(client, body):
    return await client.post("/api/webhook/abc123", json=body)


async def test_presence_on_after_post(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await _post(client, {"device": "dsi", "battery": {"charging": True}})
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "on"
    assert hass.states.get("binary_sensor.dsi_quarto_charging").state == "on"


async def test_presence_off_after_timeout(
    hass, hass_client_no_auth, setup_entry, freezer
):
    client = await hass_client_no_auth()
    await _post(client, {"device": "dsi"})
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "on"

    freezer.tick(timedelta(seconds=91))
    async_fire = pytest.importorskip(
        "pytest_homeassistant_custom_component.common"
    ).async_fire_time_changed
    async_fire(hass)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.dsi_quarto_presence").state == "off"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_binary_sensor.py -v`
Expected: FAIL — entities not created.

- [ ] **Step 3: Write the implementation**

Replace `custom_components/dspico/binary_sensor.py`:

```python
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
    def is_on(self) -> bool:
        return self.store.available


class DspicoCharging(DspicoEntity, BinarySensorEntity):
    _attr_translation_key = "charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, store, entry_id, name):
        super().__init__(store, entry_id, name, "charging")

    @property
    def is_on(self) -> bool | None:
        return self.store.fields.get("charging")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_binary_sensor.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dspico/binary_sensor.py tests/test_binary_sensor.py
git commit -m "feat: add presence and charging binary sensors"
```

---

## Task 9: Sensors (battery, rtc, rssi, identity, last_seen)

**Files:**
- Modify: `custom_components/dspico/sensor.py`
- Modify: `custom_components/dspico/data.py` (expose `last_seen`)
- Test: `tests/test_sensor.py`

- [ ] **Step 1: Add a `last_seen` property to the store**

In `custom_components/dspico/data.py`, add this property after `available`:

```python
    @property
    def last_seen(self) -> datetime | None:
        return self._last_seen
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_sensor.py`:

```python
"""Tests for DSpico sensors."""
import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dspico.const import CONF_NAME, CONF_WEBHOOK_ID, DOMAIN


@pytest.fixture
async def setup_entry(hass):
    assert await async_setup_component(hass, "webhook", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DSi Quarto",
        data={CONF_NAME: "DSi Quarto", CONF_WEBHOOK_ID: "abc123"},
        unique_id="abc123",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_sensor_values(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await client.post(
        "/api/webhook/abc123",
        json={
            "device": "dsi",
            "battery": {"level": 80, "charging": True},
            "rtc": "2026-05-27T14:32:10",
            "identity": {"nickname": "Hudson", "color": 4, "language": "pt"},
            "wifi": {"rssi": -57, "ssid": "99lab"},
            "uptime_s": 134,
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get("sensor.dsi_quarto_battery").state == "80"
    assert hass.states.get("sensor.dsi_quarto_wifi_signal").state == "-57"
    assert hass.states.get("sensor.dsi_quarto_nickname").state == "Hudson"
    assert hass.states.get("sensor.dsi_quarto_color").state == "4"
    assert hass.states.get("sensor.dsi_quarto_language").state == "pt"


async def test_missing_field_is_unknown(hass, hass_client_no_auth, setup_entry):
    client = await hass_client_no_auth()
    await client.post("/api/webhook/abc123", json={"device": "dsi"})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.dsi_quarto_battery").state == "unknown"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_sensor.py -v`
Expected: FAIL — sensors not created.

- [ ] **Step 4: Write the implementation**

Replace `custom_components/dspico/sensor.py`:

```python
"""Sensors for DSpico."""
from __future__ import annotations

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
from homeassistant.util import dt as dt_util

from . import DspicoConfigEntry
from .const import CONF_NAME
from .entity import DspicoEntity


@dataclass(frozen=True, kw_only=True)
class DspicoSensorDescription(SensorEntityDescription):
    """Describes a DSpico sensor and how to read its value from fields."""


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
            # Naive console-local ISO string -> aware datetime in HA's tz.
            parsed = dt_util.parse_datetime(value)
            if parsed is None:
                return None
            return parsed.replace(tzinfo=dt_util.get_default_time_zone())
        return value
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_sensor.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add custom_components/dspico/sensor.py custom_components/dspico/data.py tests/test_sensor.py
git commit -m "feat: add battery, rtc, wifi, identity and last_seen sensors"
```

---

## Task 10: Translations and strings

**Files:**
- Create: `custom_components/dspico/strings.json`
- Create: `custom_components/dspico/translations/en.json`
- Create: `custom_components/dspico/translations/pt-BR.json`
- Test: `tests/test_translations.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_translations.py`:

```python
"""Tests that translation files cover every entity translation_key."""
import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "custom_components" / "dspico"

EXPECTED_SENSORS = {
    "battery",
    "wifi_signal",
    "rtc",
    "nickname",
    "color",
    "language",
    "last_seen",
}
EXPECTED_BINARY = {"presence", "charging"}


def _load(name):
    return json.loads((BASE / name).read_text())


def test_strings_and_translations_match():
    for fname in ("strings.json", "translations/en.json", "translations/pt-BR.json"):
        data = _load(fname)
        assert set(data["entity"]["sensor"]) == EXPECTED_SENSORS, fname
        assert set(data["entity"]["binary_sensor"]) == EXPECTED_BINARY, fname
        assert "user" in data["config"]["step"], fname
        assert "confirm" in data["config"]["step"], fname
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_translations.py -v`
Expected: FAIL — files missing.

- [ ] **Step 3: Write `strings.json`**

Create `custom_components/dspico/strings.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "DSpico",
        "description": "Add a Nintendo DSi running the ds-ha-bridge app. A webhook will be created next.",
        "data": { "name": "Name" }
      },
      "confirm": {
        "title": "Webhook created",
        "description": "Put this webhook URL in dspico_ha.cfg on the DSpico SD card:\n\n{webhook_url}"
      }
    }
  },
  "entity": {
    "binary_sensor": {
      "presence": { "name": "Presence" },
      "charging": { "name": "Charging" }
    },
    "sensor": {
      "battery": { "name": "Battery" },
      "wifi_signal": { "name": "Wi-Fi signal" },
      "rtc": { "name": "Console clock" },
      "nickname": { "name": "Nickname" },
      "color": { "name": "Favourite colour" },
      "language": { "name": "Language" },
      "last_seen": { "name": "Last seen" }
    }
  }
}
```

- [ ] **Step 4: Write `translations/en.json`**

Create `custom_components/dspico/translations/en.json` with the **same content** as `strings.json` from Step 3 (copy it verbatim).

- [ ] **Step 5: Write `translations/pt-BR.json`**

Create `custom_components/dspico/translations/pt-BR.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "DSpico",
        "description": "Adicione um Nintendo DSi rodando o app ds-ha-bridge. Um webhook será criado em seguida.",
        "data": { "name": "Nome" }
      },
      "confirm": {
        "title": "Webhook criado",
        "description": "Coloque esta URL de webhook no dspico_ha.cfg do cartão SD do DSpico:\n\n{webhook_url}"
      }
    }
  },
  "entity": {
    "binary_sensor": {
      "presence": { "name": "Presença" },
      "charging": { "name": "Carregando" }
    },
    "sensor": {
      "battery": { "name": "Bateria" },
      "wifi_signal": { "name": "Sinal Wi-Fi" },
      "rtc": { "name": "Relógio do console" },
      "nickname": { "name": "Apelido" },
      "color": { "name": "Cor favorita" },
      "language": { "name": "Idioma" },
      "last_seen": { "name": "Visto por último" }
    }
  }
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_translations.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add custom_components/dspico/strings.json custom_components/dspico/translations tests/test_translations.py
git commit -m "feat: add strings and en + pt-BR translations"
```

---

## Task 11: Full suite, HACS metadata, and CI

**Files:**
- Create: `hacs.json`
- Create: `.github/workflows/validate.yml`
- Modify: `README.md`

- [ ] **Step 1: Run the entire test suite**

Run: `.venv/bin/pytest -v`
Expected: all tests PASS (no failures, no errors).

- [ ] **Step 2: Create the HACS metadata**

Create `hacs.json`:

```json
{
  "name": "DSpico",
  "render_readme": true,
  "homeassistant": "2024.12.0"
}
```

- [ ] **Step 3: Create the CI workflow**

Create `.github/workflows/validate.yml`:

```yaml
name: Validate

on:
  push:
  pull_request:

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration

  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-test.txt
      - run: pytest -v
```

- [ ] **Step 4: Document the GitHub repo topics requirement**

Append to `README.md`:

```markdown
## HACS publishing

For the HACS validation action to pass, the GitHub repository must have
**topics** set (e.g. `home-assistant`, `hacs`, `integration`, `nintendo-ds`,
`dspico`). Set them under the repo's "About" gear on GitHub — the HACS action
fails without them.

## Install (manual)

1. Copy `custom_components/dspico/` into your HA `config/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "DSpico".
4. Enter a name; HA shows the webhook URL. Put that URL in `dspico_ha.cfg`
   on the DSpico SD card (see the ds-ha-bridge README).
```

- [ ] **Step 5: Commit**

```bash
git add hacs.json .github/workflows/validate.yml README.md
git commit -m "ci: add hassfest, HACS and pytest workflow plus HACS metadata"
```

---

## Self-Review (completed during planning)

**Spec coverage:** webhook transport (Tasks 1,6) · entities battery/charging/presence/rtc/rssi/nickname/color/language/last_seen (Tasks 8,9) · availability watchdog/timeout (Tasks 4,8) · JSON contract validation incl. 400s (Tasks 3,6) · config flow + webhook URL (Task 5, README) · pt-BR + en translations (Task 10) · HACS + hassfest + tests (Task 11). All §1–§6 spec items map to a task.

**Placeholder scan:** none — every code step contains full code; placeholder platform modules in Task 6 are explicitly replaced in Tasks 8–9.

**Type consistency:** `DspicoData(hass, entry_id, interval)`, `.update(fields)`, `.fields`, `.available`, `.last_seen`, `.set_offline_callback`, `.shutdown` used identically across Tasks 4/6/7/8/9. `DspicoEntity(store, entry_id, device_name, key)` signature consistent in Tasks 7/8/9. Flat field keys (`battery_level`, `charging`, `rtc`, `nickname`, `color`, `language`, `rssi`, `ssid`, `uptime_s`) match `parse_payload` output from Task 3. `SIGNAL_UPDATE.format(entry_id)` consistent in Tasks 4/6/7. Entity ids (`binary_sensor.dsi_quarto_presence`, etc.) follow `has_entity_name` + device name "DSi Quarto" used in tests.

---

## Build Log — deviations from the original plan

Captured during subagent-driven execution. Code is the source of truth; the
task bodies above were synced inline where marked, others are recorded here.

1. **const.py** — `PLATFORMS` uses the `Platform` enum; `CONF_NAME`/`CONF_WEBHOOK_ID`
   are re-exported from `homeassistant.const`; `Final` annotations added. *(synced inline)*
2. **schema.py** — hardened beyond the plan: a `_strict_int` validator rejects
   `bool` (an `int` subclass), string length caps on device/fw/rtc/nickname/
   language/ssid, and `extra=vol.REMOVE_EXTRA` (forward-compatible: unknown keys
   are dropped, not rejected). `fw`/`ssid`/`uptime_s` are parsed but not yet
   surfaced as entities (noted in code). *(synced inline)*
3. **config_flow.py** — two-step flow: `user` collects the name, `confirm` shows
   the generated webhook URL via `description_placeholders` (falls back to a
   relative path when no HA base URL is configured) so the user can copy it into
   `dspico_ha.cfg`. *(synced inline; `strings.json` gained a `confirm` step)*
4. **__init__.py** — the HA webhook module is imported as `ha_webhook`, because the
   local `webhook.py` submodule shadows the bare name `webhook` in the package
   namespace. Unload order corrected (unload platforms first, then unregister +
   `shutdown()` only if successful). *(synced inline)*
5. **webhook.py** — the store update + dispatch is wrapped in a guard returning
   HTTP 500 (with `_LOGGER.exception`) on unexpected errors. *(synced inline)*
6. **data.py — availability is watchdog-driven (NOT synced inline above).** The
   `available` property is `return self._available`, a flag set `True` in
   `update()` and `False` in `_handle_timeout()`. The original time-delta check
   was removed: the `async_call_later` watchdog is the single source of truth.
   (`_handle_timeout` intentionally does not null `_cancel_watchdog`, so a manual
   call in tests still lets `shutdown()` cancel the real pending timer.)
7. **sensor.py — value_fn pattern (NOT synced inline above).** `DspicoSensorDescription`
   carries a `value_fn: Callable[[DspicoData], ...]`; `native_value` is a single
   delegation. `_field(key)` closures cover the plain fields; `_rtc` parses the
   naive ISO string and stamps the HA default tz (fold=0 assumed during DST
   overlap, documented in code). `color` got `icon="mdi:palette"`.
8. **Test infrastructure (NOT synced inline above):**
   - `setup.cfg` added with `asyncio_mode = auto` and `testpaths = tests`.
   - `tests/conftest.py` makes `enable_custom_integrations` autouse only for tests
     that use `hass` (so pure-sync tests don't pull in the async fixture), plus a
     session-scoped `_prewarm_pycares_shutdown_thread` fixture that avoids a
     `verify_cleanup` false positive from pycares' lazily-started daemon thread.
   - Test fixtures that arm the watchdog unload the entry / call `shutdown()` on
     teardown to avoid lingering-timer failures.
   - **Translations (Task 10) were implemented before sensors (Task 9)** because
     entity_ids slug from the translated name; the sensor tests resolve entity_ids
     via the entity registry by `unique_id` (`{entry_id}_{key}`) rather than
     hardcoding slugified ids.

**Result:** 11 tasks, 29 tests passing; final holistic review concluded "ready to merge".
