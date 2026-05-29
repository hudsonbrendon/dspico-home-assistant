#include "wifi.h"
#include "telemetry_types.h"

#include <dswifi9.h>
#include <nds.h>
#include <string.h>

int wifi_up(void) {
    /* WIFI_ATTEMPT_DSI_MODE selects the WPA2-capable DSi driver;
     * WFC_CONNECT connects to the AP stored in firmware (the DSi
     * "Advanced Setup" WPA2 slot when running in DSi mode). */
    if (!Wifi_InitDefault(WFC_CONNECT | WIFI_ATTEMPT_DSI_MODE)) {
        return 0;
    }
    return Wifi_AssocStatus() == ASSOCSTATUS_ASSOCIATED;
}

int wifi_is_connected(void) {
    return Wifi_AssocStatus() == ASSOCSTATUS_ASSOCIATED;
}

int wifi_rssi(void) {
    /* Best-effort: report the signal of the matching AP in the scan list.
     * Wifi_GetAPData fills level (0..255 vendor units); convert to a rough
     * dBm estimate. If unavailable, return the unknown sentinel. */
    Wifi_AccessPoint ap;
    if (Wifi_GetData(WIFIGETDATA_RSSI, sizeof(ap), (unsigned char *)&ap) < 0) {
        return TLM_UNKNOWN_RSSI;
    }
    /* dswifi level 0..0xD0-ish; map to ~ -90..-30 dBm. */
    int level = ap.rssi & 0xFF;
    if (level <= 0) {
        return TLM_UNKNOWN_RSSI;
    }
    int dbm = -90 + (level * 60) / 255;
    if (dbm > 0) {
        dbm = 0;
    }
    return dbm;
}

void wifi_ssid(char *out, int outsize) {
    Wifi_AccessPoint ap;
    if (Wifi_GetData(WIFIGETDATA_RSSI, sizeof(ap), (unsigned char *)&ap) < 0) {
        out[0] = '\0';
        return;
    }
    int n = ap.ssid_len;
    if (n >= outsize) {
        n = outsize - 1;
    }
    memcpy(out, ap.ssid, n);
    out[n] = '\0';
}

/*
 * API note: dswifi's exact getter for the *connected* AP's RSSI/SSID varies by
 * version. If WIFIGETDATA_RSSI / Wifi_AccessPoint.rssi differ in your BlocksDS
 * build, the safe fallback is to return TLM_UNKNOWN_RSSI and out[0]='\0' here --
 * the HA side already renders those as "unknown" and presence still works.
 * Confirm and adjust this file when building against the BlocksDS dswifi headers.
 */
