#include "check.h"
#include "json.h"
#include <string.h>

static int contains(const char *hay, const char *needle) {
    return strstr(hay, needle) != NULL;
}

int main(void) {
    char buf[512];

    telemetry_t full = {0};
    strcpy(full.device, "dsi-quarto");
    strcpy(full.fw, "ds-ha-bridge 0.1.0");
    full.battery_level = 80;
    full.charging = 1;
    strcpy(full.rtc, "2026-05-27T14:32:10");
    strcpy(full.nickname, "Hudson");
    full.color = 4;
    strcpy(full.language, "pt");
    full.rssi = -57;
    strcpy(full.ssid, "99lab");
    full.uptime_s = 134;

    int n = json_build(buf, sizeof(buf), &full);
    CHECK(n > 0);
    CHECK(contains(buf, "\"device\":\"dsi-quarto\""));
    CHECK(contains(buf, "\"battery\":{\"level\":80,\"charging\":true}"));
    CHECK(contains(buf, "\"rtc\":\"2026-05-27T14:32:10\""));
    CHECK(contains(buf, "\"nickname\":\"Hudson\""));
    CHECK(contains(buf, "\"color\":4"));
    CHECK(contains(buf, "\"language\":\"pt\""));
    CHECK(contains(buf, "\"rssi\":-57"));
    CHECK(contains(buf, "\"ssid\":\"99lab\""));
    CHECK(contains(buf, "\"uptime_s\":134"));

    /* minimal: only device known */
    telemetry_t min = {0};
    strcpy(min.device, "dsi");
    min.battery_level = TLM_UNKNOWN_INT;
    min.charging = TLM_UNKNOWN_INT;
    min.color = TLM_UNKNOWN_INT;
    min.rssi = TLM_UNKNOWN_RSSI;
    min.uptime_s = TLM_UNKNOWN_INT;
    n = json_build(buf, sizeof(buf), &min);
    CHECK(n > 0);
    CHECK(contains(buf, "\"device\":\"dsi\""));
    CHECK(!contains(buf, "battery"));
    CHECK(!contains(buf, "identity"));
    CHECK(!contains(buf, "wifi"));
    CHECK(!contains(buf, "uptime_s"));

    /* escaping */
    telemetry_t esc = {0};
    strcpy(esc.device, "a\"b\\c");
    esc.battery_level = TLM_UNKNOWN_INT;
    esc.charging = TLM_UNKNOWN_INT;
    esc.color = TLM_UNKNOWN_INT;
    esc.rssi = TLM_UNKNOWN_RSSI;
    esc.uptime_s = TLM_UNKNOWN_INT;
    n = json_build(buf, sizeof(buf), &esc);
    CHECK(contains(buf, "\"device\":\"a\\\"b\\\\c\""));

    /* partial battery: level known, charging unknown -> only level */
    telemetry_t pb = {0};
    strcpy(pb.device, "dsi");
    pb.battery_level = 42;
    pb.charging = TLM_UNKNOWN_INT;
    pb.color = TLM_UNKNOWN_INT;
    pb.rssi = TLM_UNKNOWN_RSSI;
    pb.uptime_s = TLM_UNKNOWN_INT;
    json_build(buf, sizeof(buf), &pb);
    CHECK(contains(buf, "\"battery\":{\"level\":42}"));
    CHECK(!contains(buf, "charging"));

    /* rssi == 0 is a valid reading and must be emitted */
    telemetry_t r0 = {0};
    strcpy(r0.device, "dsi");
    r0.battery_level = TLM_UNKNOWN_INT;
    r0.charging = TLM_UNKNOWN_INT;
    r0.color = TLM_UNKNOWN_INT;
    r0.rssi = 0;
    r0.uptime_s = TLM_UNKNOWN_INT;
    json_build(buf, sizeof(buf), &r0);
    CHECK(contains(buf, "\"wifi\":{\"rssi\":0}"));

    /* control characters are escaped -> valid JSON */
    telemetry_t ctl = {0};
    strcpy(ctl.device, "a\nb");
    ctl.battery_level = TLM_UNKNOWN_INT;
    ctl.charging = TLM_UNKNOWN_INT;
    ctl.color = TLM_UNKNOWN_INT;
    ctl.rssi = TLM_UNKNOWN_RSSI;
    ctl.uptime_s = TLM_UNKNOWN_INT;
    json_build(buf, sizeof(buf), &ctl);
    CHECK(contains(buf, "\"device\":\"a\\nb\""));
    DONE();
}
