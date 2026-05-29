#ifndef DS_HA_BRIDGE_TELEMETRY_H
#define DS_HA_BRIDGE_TELEMETRY_H

#include "telemetry_types.h"

/* Firmware version string embedded in payloads. */
#define DS_HA_BRIDGE_FW "ds-ha-bridge 0.1.0"

/* Populate `t` from hardware. `device_name` comes from config; `rssi`/`ssid`
 * come from the wifi module (pass current values, or TLM_UNKNOWN_RSSI/""),
 * `uptime_s` from the caller's session timer. */
void telemetry_collect(telemetry_t *t, const char *device_name,
                       int rssi, const char *ssid, int uptime_s);

#endif
