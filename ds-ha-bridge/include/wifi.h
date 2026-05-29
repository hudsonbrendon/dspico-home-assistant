#ifndef DS_HA_BRIDGE_WIFI_H
#define DS_HA_BRIDGE_WIFI_H

/* Bring up Wi-Fi using the console's stored connection (DSi mode -> WPA2).
 * Blocks until associated or failed. Returns 1 on success, 0 on failure. */
int wifi_up(void);

/* True if currently associated. */
int wifi_is_connected(void);

/* RSSI in dBm of the connected AP (<=0), or TLM_UNKNOWN_RSSI if unavailable. */
int wifi_rssi(void);

/* Copy the connected SSID into out (NUL-terminated); out[0]='\0' if unknown. */
void wifi_ssid(char *out, int outsize);

#endif
