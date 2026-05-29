#include "json.h"
#include <stdio.h>
#include <string.h>

/* Append src to dst (offset *pos within cap), escaping JSON string chars.
 * Returns 0 on success, -1 on overflow. */
static int append_escaped(char *dst, size_t cap, size_t *pos, const char *src) {
    for (const char *s = src; *s; s++) {
        char esc[3];
        int len;
        if (*s == '"' || *s == '\\') {
            esc[0] = '\\';
            esc[1] = *s;
            len = 2;
        } else {
            esc[0] = *s;
            len = 1;
        }
        if (*pos + (size_t)len >= cap) {
            return -1;
        }
        memcpy(dst + *pos, esc, (size_t)len);
        *pos += (size_t)len;
    }
    return 0;
}

static int append_raw(char *dst, size_t cap, size_t *pos, const char *src) {
    size_t len = strlen(src);
    if (*pos + len >= cap) {
        return -1;
    }
    memcpy(dst + *pos, src, len);
    *pos += len;
    return 0;
}

int json_build(char *buf, size_t bufsize, const telemetry_t *t) {
    size_t pos = 0;

#define RAW(s)   do { if (append_raw(buf, bufsize, &pos, (s))) return -1; } while (0)
#define ESC(s)   do { if (append_escaped(buf, bufsize, &pos, (s))) return -1; } while (0)
#define NUM(n)   do { char _b[16]; snprintf(_b, sizeof(_b), "%d", (n)); RAW(_b); } while (0)

    RAW("{\"device\":\"");
    ESC(t->device);
    RAW("\"");

    if (t->fw[0]) {
        RAW(",\"fw\":\"");
        ESC(t->fw);
        RAW("\"");
    }

    if (t->battery_level != TLM_UNKNOWN_INT || t->charging != TLM_UNKNOWN_INT) {
        RAW(",\"battery\":{");
        int first = 1;
        if (t->battery_level != TLM_UNKNOWN_INT) {
            RAW("\"level\":");
            NUM(t->battery_level);
            first = 0;
        }
        if (t->charging != TLM_UNKNOWN_INT) {
            if (!first) RAW(",");
            RAW("\"charging\":");
            RAW(t->charging ? "true" : "false");
        }
        RAW("}");
    }

    if (t->rtc[0]) {
        RAW(",\"rtc\":\"");
        ESC(t->rtc);
        RAW("\"");
    }

    if (t->nickname[0] || t->color != TLM_UNKNOWN_INT || t->language[0]) {
        RAW(",\"identity\":{");
        int first = 1;
        if (t->nickname[0]) {
            RAW("\"nickname\":\"");
            ESC(t->nickname);
            RAW("\"");
            first = 0;
        }
        if (t->color != TLM_UNKNOWN_INT) {
            if (!first) RAW(",");
            RAW("\"color\":");
            NUM(t->color);
            first = 0;
        }
        if (t->language[0]) {
            if (!first) RAW(",");
            RAW("\"language\":\"");
            ESC(t->language);
            RAW("\"");
        }
        RAW("}");
    }

    if (t->rssi <= 0 || t->ssid[0]) {
        RAW(",\"wifi\":{");
        int first = 1;
        if (t->rssi <= 0) {
            RAW("\"rssi\":");
            NUM(t->rssi);
            first = 0;
        }
        if (t->ssid[0]) {
            if (!first) RAW(",");
            RAW("\"ssid\":\"");
            ESC(t->ssid);
            RAW("\"");
        }
        RAW("}");
    }

    if (t->uptime_s != TLM_UNKNOWN_INT) {
        RAW(",\"uptime_s\":");
        NUM(t->uptime_s);
    }

    RAW("}");
    if (pos >= bufsize) {
        return -1;
    }
    buf[pos] = '\0';

#undef RAW
#undef ESC
#undef NUM
    return (int)pos;
}
