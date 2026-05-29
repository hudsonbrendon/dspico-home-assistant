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

1. Install BlocksDS and `export BLOCKSDS=/opt/blocksds/core`.
2. `make` -> produces `ds-ha-bridge.nds`.

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
