#include "telemetry.h"
#include "battmap.h"
#include "identity.h"

#include <nds.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

void telemetry_collect(telemetry_t *t, const char *device_name,
                       int rssi, const char *ssid, int uptime_s) {
    memset(t, 0, sizeof(*t));

    snprintf(t->device, sizeof(t->device), "%s", device_name);
    snprintf(t->fw, sizeof(t->fw), "%s", DS_HA_BRIDGE_FW);

    /* Battery: libnds getBatteryLevel() returns raw (level nibble + 0x80). */
    int raw = getBatteryLevel();
    t->battery_level = batt_to_percent(raw);
    t->charging = batt_is_charging(raw);

    /* RTC via newlib time() (libnds wires this to the console RTC). */
    time_t now = time(NULL);
    struct tm *lt = localtime(&now);
    if (lt) {
        strftime(t->rtc, sizeof(t->rtc), "%Y-%m-%dT%H:%M:%S", lt);
    } else {
        t->rtc[0] = '\0';
    }

    /* Firmware user settings: PersonalData is a libnds macro to the user
     * settings region. name is UTF-16 (nameLen units), theme = favourite
     * colour, language = language byte. */
    nickname_to_ascii((const unsigned short *)PersonalData->name,
                      PersonalData->nameLen, t->nickname, sizeof(t->nickname));
    t->color = PersonalData->theme;
    if (t->color < 0 || t->color > 15) {
        t->color = TLM_UNKNOWN_INT; /* drop an out-of-range colour, don't 400 */
    }
    snprintf(t->language, sizeof(t->language), "%s",
             language_code(PersonalData->language));

    /* Wi-Fi values supplied by caller (from the wifi module). */
    t->rssi = rssi;
    if (ssid) {
        snprintf(t->ssid, sizeof(t->ssid), "%s", ssid);
    }

    t->uptime_s = uptime_s;
}
