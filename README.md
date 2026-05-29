# dspico-home-assistant

Telemetria do Nintendo DSi (via flashcart DSpico) para o Home Assistant.

- `custom_components/dspico/` — integração HA (config-flow, webhook, HACS)
- `ds-ha-bridge/` — app homebrew DS (BlocksDS) que faz POST da telemetria

Ver `docs/superpowers/specs/` para o design.

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
