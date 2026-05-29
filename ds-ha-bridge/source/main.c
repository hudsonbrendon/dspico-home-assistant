#include "config.h"
#include "httppost.h"
#include "json.h"
#include "telemetry.h"
#include "telemetry_types.h"
#include "wifi.h"

#include <fat.h>
#include <nds.h>
#include <stdio.h>
#include <string.h>

static int read_config_file(const char *path, config_t *cfg) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return -1;
    }
    char buf[1024];
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = '\0';
    return config_parse(buf, cfg);
}

int main(void) {
    consoleDemoInit();
    iprintf("ds-ha-bridge %s\n", DS_HA_BRIDGE_FW);

    if (!fatInitDefault()) {
        iprintf("FAT init failed (no SD?).\n");
        while (1) swiWaitForVBlank();
    }

    config_t cfg;
    int crc = read_config_file("/dspico_ha.cfg", &cfg);
    if (crc != 0) {
        iprintf("Config error (%d).\n", crc);
        iprintf("Need /dspico_ha.cfg with\n");
        iprintf("host, path, device_name.\n");
        while (1) swiWaitForVBlank();
    }
    iprintf("Device: %s\n", cfg.device_name);
    iprintf("Target: %s:%d\n", cfg.host, cfg.port);

    iprintf("Connecting WiFi...\n");
    while (!wifi_up()) {
        iprintf("WiFi failed, retry in 10s\n");
        for (int i = 0; i < 600; i++) swiWaitForVBlank(); /* ~10s @60Hz */
    }
    iprintf("WiFi connected.\n");

    int uptime = 0;
    char last_status[40] = "starting...";

    while (1) {
        char ssid[34];
        wifi_ssid(ssid, sizeof(ssid));

        telemetry_t t;
        telemetry_collect(&t, cfg.device_name, wifi_rssi(), ssid, uptime);

        char body[512];
        int bn = json_build(body, sizeof(body), &t);
        if (bn < 0) {
            snprintf(last_status, sizeof(last_status), "json overflow");
        } else {
            int code = http_post(cfg.host, cfg.port, cfg.path, body);
            if (code == 200) {
                snprintf(last_status, sizeof(last_status), "OK 200");
            } else {
                snprintf(last_status, sizeof(last_status), "POST err %d", code);
            }
        }

        /* Redraw status block. */
        iprintf("\x1b[12;0H"); /* move cursor to row 12 */
        iprintf("Batt: %d%% chg:%d   \n", t.battery_level, t.charging);
        iprintf("RTC : %s\n", t.rtc);
        iprintf("RSSI: %d dBm        \n", t.rssi);
        iprintf("Up  : %ds           \n", uptime);
        iprintf("Last: %s            \n", last_status);
        iprintf("START+SELECT to exit\n");

        /* Sleep interval, polling for exit. */
        for (int i = 0; i < cfg.interval_sec * 60; i++) {
            swiWaitForVBlank();
            scanKeys();
            if ((keysHeld() & (KEY_START | KEY_SELECT)) ==
                (KEY_START | KEY_SELECT)) {
                return 0;
            }
        }
        uptime += cfg.interval_sec;
    }
    return 0;
}
