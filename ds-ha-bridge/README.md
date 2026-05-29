# ds-ha-bridge

Nintendo DSi homebrew that reports telemetry to Home Assistant (the `dspico`
integration). Runs on a DSi via the DSpico flashcart.

## Requirements

- A **DSi** (or 3DS in DSi mode). The original DS is not supported (no WPA2).
- Wi-Fi already configured in the DSi **System Settings -> Internet -> Advanced
  Setup** (this is the WPA2 connection the app reuses).
- The `dspico` Home Assistant integration installed and added, so you have a
  webhook URL.

## Build

**Docker (no local toolchain install needed) — recommended.** From the repo root:

```bash
docker run --rm -v "$PWD/ds-ha-bridge":/project -w /project \
  skylyrac/blocksds:dev-latest make
```

**Native BlocksDS.** Install BlocksDS and make sure `BLOCKSDS` is exported (the
Wonderful install sets it to `/opt/wonderful/thirdparty/blocksds/core`; the
standalone install uses `/opt/blocksds/core`), then run `make` in `ds-ha-bridge/`.

Either way produces `ds-ha-bridge.nds` (~224 KB). The ROM build also runs in CI
(the `ds-rom` job).

## Install

1. Copy `ds-ha-bridge.nds` to the DSpico SD card.
2. Copy `dspico_ha.cfg.example` to the SD root as `dspico_ha.cfg` and edit
   `host`, `path` (the webhook path from HA), and `device_name`.
3. Launch `ds-ha-bridge` from Pico Launcher.

## Tests

- Pure C units: `cd tests/host && make test`.
- Integration: build the ROM, run it (melonDS with networking, or real
  hardware) against a running HA, and confirm entities populate.

## Limitation

The DS runs one app at a time. This bridge reports **only while it is the
foreground app** -- launching a retail game stops telemetry until you return to
the bridge.
