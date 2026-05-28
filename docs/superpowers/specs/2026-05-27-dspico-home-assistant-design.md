# DSpico / Nintendo DSi → Home Assistant — Design

**Date:** 2026-05-27
**Status:** Approved (brainstorming)
**Author:** Hudson Brendon

## Summary

Bring live telemetry from a Nintendo DSi (running the **DSpico** open-source
flashcart) into Home Assistant. The DSpico cartridge is an RP2040-based device
with **no wireless radio of its own**, so the only network path is the
console's own Wi-Fi. We therefore build:

1. **`ds-ha-bridge`** — a Nintendo DS homebrew app (`.nds`) launched from the
   DSpico's Pico Launcher. It connects to Wi-Fi using the DSi's stored WPA2
   settings, reads the telemetry libnds exposes, and `POST`s a JSON payload to
   a Home Assistant webhook on a fixed interval.
2. **`dspico`** — a Home Assistant custom integration (config-flow, HACS-ready)
   that registers a webhook, ingests the JSON, and exposes the data as
   entities. Presence/availability is derived from a heartbeat timeout.

The two components are independent deliverables joined by **one JSON contract**
(§4).

## Feasibility constraints (recon findings)

- **DSpico = RP2040 flashcart, no Wi-Fi/BT radio.** USB + dev port exist but
  are for PC flashing and are physically covered while the cart is inserted.
  The cart cannot reach the network on its own.
- **Only network path = the console's Wi-Fi** via libnds/dswifi homebrew.
- **Console is a DSi/DSi XL.** In DSi mode the dswifi DSi driver
  (`WIFI_ATTEMPT_DSI_MODE`) supports Open/WEP/**WPA2**. `WFC_CONNECT` connects
  to the APs stored in firmware; on DSi those are the "Advanced Setup"
  (WPA2-capable) connection slots. So
  `Wifi_InitDefault(WFC_CONNECT | WIFI_ATTEMPT_DSI_MODE)` reuses the WPA2
  network already configured in the DSi's Internet settings — no credentials in
  homebrew.
- **Hard limitation — foreground only.** The DS runs one app at a time. The
  bridge reports only while it is the foreground app. The moment a real game is
  launched from Pico Launcher, the bridge stops running and telemetry stops.
  This integration therefore models *"DSi powered on with the bridge running,
  plus battery / clock / identity"* — **not** *"which game is being played."*
- **Telemetry available via libnds:** battery level (DSi is granular vs the
  original DS's high/low → 15/3), charging flag, RTC date/time, firmware
  `PersonalData` (nickname, favourite colour, language), Wi-Fi RSSI/SSID.

## Architecture & data flow

```
Nintendo DSi
  └─ DSpico (Pico Launcher) ──launches──> ds-ha-bridge (.nds)
        │  reads battery / RTC / identity / RSSI
        │  HTTP POST application/json, every interval_sec
        ▼
  http://<HA_HOST>:8123/api/webhook/<webhook_id>   (plain HTTP, LAN)
        │
        ▼
  Home Assistant — custom_component `dspico`
        webhook handler → validate JSON → update runtime state
                        → async_dispatcher_send → entities
        watchdog (async_track_point_in_time) → mark offline after timeout
```

Transport is plain HTTP over the LAN (no TLS). This matches the existing
KOReader/Kindle "REST bridge" pattern and avoids TLS overhead on the DS.

## Component 1 — `ds-ha-bridge` (Nintendo DS homebrew)

**Toolchain:** BlocksDS SDK (libnds + dswifi + libfat). Build target: `.nds`.

| File | Responsibility |
|------|----------------|
| `source/main.c` | Boot video/console UI; init config, Wi-Fi, telemetry; main loop (read → serialize → POST → sleep `interval_sec`); on-screen status lines; exit on START+SELECT. |
| `source/config.c` / `.h` | Read `/dspico_ha.cfg` from SD (libfat). Keys: `host`, `port`, `path`, `interval_sec`, `device_name`. Pure C, parseable on host for tests. |
| `source/wifi.c` / `.h` | `wifi_connect()` → `Wifi_InitDefault(WFC_CONNECT | WIFI_ATTEMPT_DSI_MODE)`; `wifi_is_connected()`; `wifi_rssi()`; `wifi_ssid()`. |
| `source/telemetry.c` / `.h` | Gather into a `telemetry_t` struct: battery level → 0–100% (map libnds `getBatteryLevel()`), `charging`, RTC via libnds time, `PersonalData` nickname/colour/language, RSSI, `uptime_s`. |
| `source/json.c` / `.h` | Serialize `telemetry_t` to the §4 payload with `snprintf` into a fixed buffer (no heap). Pure C, host-testable. |
| `source/httppost.c` / `.h` | Raw lwIP BSD socket: resolve host, TCP connect, send `POST <path> HTTP/1.1` + headers + body, read the HTTP status line, close. Return status code (or negative on socket error). |
| `Makefile` | BlocksDS makefile producing `ds-ha-bridge.nds`. |
| `dspico_ha.cfg.example` | Documented sample config. |
| `README.md` | Build + install (copy `.nds` and `dspico_ha.cfg` to SD), DSi Internet setup note. |

### DS app behaviour
- Config missing/invalid → print message, halt loop (no crash).
- Wi-Fi connect fails → show error, retry every 10 s.
- POST fails (socket error or non-2xx) → show last error + HTTP code, continue
  at next interval (never crash).
- Screen shows: connection state, last POST result + code, battery %, uptime.

### Battery mapping
libnds `getBatteryLevel()` on DSi returns a small-integer scale. `telemetry.c`
maps it to a 0–100 percentage with an explicit lookup table (defined in the
implementation plan), and reports `charging` from the DSi power register bit.

## Component 2 — `dspico` (Home Assistant custom integration)

**Layout:** `custom_components/dspico/`

| File | Responsibility |
|------|----------------|
| `manifest.json` | `domain: dspico`, `iot_class: local_push`, `config_flow: true`, `dependencies: ["webhook"]`, codeowners, version. **Keys ordered to satisfy hassfest.** |
| `const.py` | `DOMAIN`, signal names, config keys, defaults (e.g. `DEFAULT_INTERVAL = 30`, `TIMEOUT_FACTOR = 3`). |
| `__init__.py` | `async_setup_entry`: build runtime data, `webhook.async_register`, forward to `sensor`/`binary_sensor`. `async_unload_entry`: `webhook.async_unregister` + unload platforms. |
| `config_flow.py` | User step asks `name`; generate `webhook_id` (`webhook.async_generate_id`); unique_id = `webhook_id`; final step shows the webhook URL via `webhook.async_generate_url`. Allows multiple DS instances. |
| `webhook.py` | `async_handle_webhook`: parse + voluptuous-validate JSON; update runtime `DspicoData`; set `last_seen = utcnow()`; `async_dispatcher_send`; (re)schedule offline watchdog. Invalid → HTTP 400, logged at debug. |
| `data.py` | `DspicoData` dataclass: latest payload fields + `last_seen` + `available`; watchdog via `async_track_point_in_time`, flips `available=False` after `interval * TIMEOUT_FACTOR`. |
| `entity.py` | `DspicoEntity` base: `device_info` from entry; `available` from runtime; subscribes to dispatcher signal. |
| `sensor.py` | `battery` (%, `device_class=battery`), `rtc` (`device_class=timestamp`), `wifi_rssi` (`device_class=signal_strength`, dBm), `nickname` / `color` / `language` (`entity_category=diagnostic`), `last_seen` (`device_class=timestamp`). |
| `binary_sensor.py` | `presence` (`device_class=connectivity`, on while heartbeat fresh), `charging` (`device_class=battery_charging`). |
| `strings.json`, `translations/en.json`, `translations/pt-BR.json` | UI strings. |

**Repo extras (HACS):** `hacs.json`, repository **topics** set on GitHub (HACS
gotcha), `.github/workflows/` for hassfest + HACS validation + pytest.

### Entity availability
`presence` is `on` and other entities are `available` while a POST has arrived
within `interval * TIMEOUT_FACTOR`; otherwise `presence` is `off` and the
watchdog marks entities unavailable. A field absent from a payload renders that
entity `unknown` without affecting presence.

## 4. JSON contract (DS ⇄ HA)

```json
{
  "device": "dsi-quarto",
  "fw": "ds-ha-bridge 0.1.0",
  "battery": { "level": 80, "charging": true },
  "rtc": "2026-05-27T14:32:10",
  "identity": { "nickname": "Hudson", "color": 4, "language": "pt" },
  "wifi": { "rssi": -57, "ssid": "99lab" },
  "uptime_s": 134
}
```

- `device` (string): from `device_name` in `dspico_ha.cfg`; stable id for the HA device.
- `battery.level` (int 0–100), `battery.charging` (bool).
- `rtc` (string): local naive ISO-8601 `YYYY-MM-DDTHH:MM:SS` from the console RTC.
- `identity.nickname` (string), `identity.color` (int 0–15), `identity.language` (string 2-letter).
- `wifi.rssi` (int dBm, negative), `wifi.ssid` (string).
- `uptime_s` (int): seconds since the bridge app started.

Optional/missing keys are tolerated by the HA side; only the presence of a
valid POST drives availability.

## 5. Error handling (summary)

| Side | Condition | Behaviour |
|------|-----------|-----------|
| DS | config missing/invalid | message on screen, loop halts, no crash |
| DS | Wi-Fi connect fails | on-screen error, retry every 10 s |
| DS | POST fails / non-2xx | show code, continue next interval, never crash |
| HA | invalid JSON / schema | HTTP 400, debug log, payload ignored |
| HA | field missing | that entity `unknown`, presence still updates |
| HA | no POST within timeout | `presence` → off, entities unavailable |

## 6. Testing strategy

- **DS app:** `json.c` and `config.c` are written as dependency-free C so they
  compile with host `gcc` for unit tests (serializer output, config parsing,
  edge cases). Network/telemetry code is verified by manual integration in the
  **melonDS** emulator (host networking via libslirp) against a local HA, with
  real DSi hardware as the authoritative check.
- **HA integration:** `pytest-homeassistant-custom-component`, TDD:
  config-flow creates entry + webhook; webhook handler updates entities;
  schema validation rejects bad payloads (400); presence flips off after the
  timeout; entities map payload fields correctly.

## 7. Scope & decomposition note

Two subsystems (DS homebrew app, HA integration) share one JSON contract and
are specced together. The implementation plan separates them into independent
task groups; the HA integration is testable end-to-end with a mocked POST
before the DS app exists, and the DS app's pure-C units are testable on the
host. A future repo split (`dspico` HACS integration vs `ds-ha-bridge`
homebrew) is possible but not required for the MVP.

## 8. Out of scope (YAGNI)

- Detecting which retail game is running (impossible while the bridge is not foreground).
- RP2040 firmware fork / USB host bridge (Approach B — needs hardware mod).
- MQTT transport, TLS, HA REST-API token auth.
- Original DS (Phat/Lite) WEP support — console is a DSi.
- Controlling the DS from HA (power, input) — telemetry is one-way.
