# ds-ha-bridge (Nintendo DSi homebrew) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Nintendo DS homebrew app (`ds-ha-bridge.nds`) that runs on a DSi via the DSpico flashcart, connects to Wi-Fi with the DSi's stored WPA2 settings, reads telemetry, and `POST`s JSON to a Home Assistant webhook on an interval.

**Architecture:** Pure C transforms (config parsing, JSON serialization, battery mapping, name/language conversion, HTTP request building) are isolated from libnds so they compile and unit-test on the host with `gcc`. A thin libnds layer (Wi-Fi, RTC, firmware user data, lwIP sockets, UI, SD config) wires the pure transforms to hardware and is verified manually in the melonDS emulator and on real hardware.

**Tech Stack:** C, BlocksDS SDK (libnds + dswifi + libfat), lwIP BSD sockets; host `gcc` + a tiny assert harness for unit tests.

This plan is one of two; the other is `2026-05-27-dspico-ha-integration.md` (the HA side). They share the JSON contract in `docs/superpowers/specs/2026-05-27-dspico-home-assistant-design.md` §4. **Build and pass the HA plan first** — you can then point this app at a real, running webhook for integration testing.

**Prerequisites:** Install BlocksDS (`https://blocksds.skylyrac.net/docs/setup/options/`) and export `BLOCKSDS` (default `/opt/blocksds/core`). A host C compiler (`gcc` or `clang`). melonDS with networking for integration testing.

---

## File Structure

| File | Responsibility | Host-testable |
|------|----------------|:---:|
| `ds-ha-bridge/include/telemetry_types.h` | Plain `telemetry_t` struct (no libnds). | n/a |
| `ds-ha-bridge/source/config.c` + `include/config.h` | Parse `key=value` config text into `config_t`. | ✅ |
| `ds-ha-bridge/source/json.c` + `include/json.h` | Serialize `telemetry_t` to the §4 JSON. | ✅ |
| `ds-ha-bridge/source/battmap.c` + `include/battmap.h` | Map raw battery register → percent + charging. | ✅ |
| `ds-ha-bridge/source/identity.c` + `include/identity.h` | UTF-16 name → ASCII; language code → 2-letter. | ✅ |
| `ds-ha-bridge/source/httpreq.c` + `include/httpreq.h` | Build the raw HTTP POST request string. | ✅ |
| `ds-ha-bridge/source/wifi.c` + `include/wifi.h` | Connect via stored DSi WPA2 settings; status; RSSI. | manual |
| `ds-ha-bridge/source/telemetry.c` + `include/telemetry.h` | Fill `telemetry_t` from libnds (battery/RTC/identity/wifi). | manual |
| `ds-ha-bridge/source/httppost.c` + `include/httppost.h` | lwIP socket: connect, send request, read status. | manual |
| `ds-ha-bridge/source/main.c` | UI, config load (libfat), main loop. | manual |
| `ds-ha-bridge/Makefile` | BlocksDS build → `ds-ha-bridge.nds`. | n/a |
| `ds-ha-bridge/tests/host/check.h` | Tiny assert harness. | n/a |
| `ds-ha-bridge/tests/host/test_*.c` | One host test per pure module. | n/a |
| `ds-ha-bridge/tests/host/Makefile` | Build + run all host tests. | n/a |
| `ds-ha-bridge/dspico_ha.cfg.example` | Sample SD config. | n/a |
| `ds-ha-bridge/README.md` | Build/install/DSi-setup/test docs. | n/a |

---

## Task 1: Repo scaffold, plain struct, and host test harness

**Files:**
- Create: `ds-ha-bridge/include/telemetry_types.h`
- Create: `ds-ha-bridge/tests/host/check.h`
- Create: `ds-ha-bridge/tests/host/test_smoke.c`
- Create: `ds-ha-bridge/tests/host/Makefile`

- [ ] **Step 1: Create the plain telemetry struct (no libnds)**

Create `ds-ha-bridge/include/telemetry_types.h`:

```c
#ifndef DS_HA_BRIDGE_TELEMETRY_TYPES_H
#define DS_HA_BRIDGE_TELEMETRY_TYPES_H

/* Sentinels for "unknown": ints use the documented value, strings use "". */
#define TLM_UNKNOWN_INT (-1)
#define TLM_UNKNOWN_RSSI (1) /* valid RSSI is <= 0 dBm; >0 means unknown */

typedef struct {
    char device[32];      /* required, from config device_name */
    char fw[32];          /* firmware string, e.g. "ds-ha-bridge 0.1.0" */
    int  battery_level;   /* 0..100, or TLM_UNKNOWN_INT */
    int  charging;        /* 0/1, or TLM_UNKNOWN_INT */
    char rtc[20];         /* "YYYY-MM-DDTHH:MM:SS" or "" */
    char nickname[24];    /* ASCII, or "" */
    int  color;           /* 0..15, or TLM_UNKNOWN_INT */
    char language[3];     /* "en" etc, or "" */
    int  rssi;            /* dBm (<=0), or TLM_UNKNOWN_RSSI */
    char ssid[34];        /* or "" */
    int  uptime_s;        /* >=0, or TLM_UNKNOWN_INT */
} telemetry_t;

#endif
```

- [ ] **Step 2: Create the assert harness**

Create `ds-ha-bridge/tests/host/check.h`:

```c
#ifndef CHECK_H
#define CHECK_H
#include <stdio.h>
#include <string.h>

static int _check_fails = 0;

#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);       \
            _check_fails++;                                              \
        }                                                                \
    } while (0)

#define CHECK_STR(a, b)                                                  \
    do {                                                                 \
        if (strcmp((a), (b)) != 0) {                                     \
            printf("FAIL %s:%d  \"%s\" != \"%s\"\n",                     \
                   __FILE__, __LINE__, (a), (b));                        \
            _check_fails++;                                              \
        }                                                                \
    } while (0)

#define DONE()                                                           \
    do {                                                                 \
        if (_check_fails) {                                              \
            printf("%d failure(s)\n", _check_fails);                     \
            return 1;                                                    \
        }                                                                \
        printf("ok\n");                                                  \
        return 0;                                                        \
    } while (0)

#endif
```

- [ ] **Step 3: Write a smoke test**

Create `ds-ha-bridge/tests/host/test_smoke.c`:

```c
#include "check.h"
#include "telemetry_types.h"

int main(void) {
    telemetry_t t = {0};
    t.battery_level = 50;
    CHECK(t.battery_level == 50);
    CHECK(TLM_UNKNOWN_INT == -1);
    DONE();
}
```

- [ ] **Step 4: Create the host test Makefile**

Create `ds-ha-bridge/tests/host/Makefile`:

```make
CC      ?= gcc
CFLAGS  := -std=c11 -Wall -Wextra -O0 -g -I. -I../../include
SRCDIR  := ../../source

# Each test binary: name -> extra source modules it links (besides its test_*.c)
TESTS := smoke config json battmap identity httpreq

smoke_SRC    :=
config_SRC   := $(SRCDIR)/config.c
json_SRC     := $(SRCDIR)/json.c
battmap_SRC  := $(SRCDIR)/battmap.c
identity_SRC := $(SRCDIR)/identity.c
httpreq_SRC  := $(SRCDIR)/httpreq.c

.PHONY: test clean
test:
	@set -e; for t in $(TESTS); do \
		echo "== $$t =="; \
		$(CC) $(CFLAGS) -o /tmp/dshb_$$t test_$$t.c $($${t}_SRC) && /tmp/dshb_$$t; \
	done

clean:
	rm -f /tmp/dshb_*
```

- [ ] **Step 5: Run the smoke test**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=smoke
```
Expected: prints `== smoke ==` then `ok`.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/telemetry_types.h ds-ha-bridge/tests/host
git commit -m "chore: scaffold ds-ha-bridge with host test harness"
```

---

## Task 2: Config parser (pure)

**Files:**
- Create: `ds-ha-bridge/include/config.h`
- Create: `ds-ha-bridge/source/config.c`
- Create: `ds-ha-bridge/tests/host/test_config.c`

Parses `key=value` lines (`#` comments and blank lines ignored). Unknown keys
are ignored. Defaults: `port=8123`, `interval_sec=30`.

- [ ] **Step 1: Write the failing test**

Create `ds-ha-bridge/tests/host/test_config.c`:

```c
#include "check.h"
#include "config.h"

int main(void) {
    const char *text =
        "# DSpico bridge config\n"
        "host=192.168.31.150\n"
        "port=8123\n"
        "path=/api/webhook/abc123\n"
        "interval_sec=15\n"
        "device_name=dsi-quarto\n"
        "\n";
    config_t c;
    CHECK(config_parse(text, &c) == 0);
    CHECK_STR(c.host, "192.168.31.150");
    CHECK(c.port == 8123);
    CHECK_STR(c.path, "/api/webhook/abc123");
    CHECK(c.interval_sec == 15);
    CHECK_STR(c.device_name, "dsi-quarto");

    /* defaults when omitted */
    config_t d;
    CHECK(config_parse("host=h\npath=/p\ndevice_name=x\n", &d) == 0);
    CHECK(d.port == 8123);
    CHECK(d.interval_sec == 30);

    /* missing required host/path/device_name -> error */
    config_t e;
    CHECK(config_parse("port=8123\n", &e) != 0);
    DONE();
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=config
```
Expected: compile error (`config.h` not found).

- [ ] **Step 3: Write the header**

Create `ds-ha-bridge/include/config.h`:

```c
#ifndef DS_HA_BRIDGE_CONFIG_H
#define DS_HA_BRIDGE_CONFIG_H

typedef struct {
    char host[64];
    int  port;
    char path[128];
    int  interval_sec;
    char device_name[32];
} config_t;

/* Parse config text. Returns 0 on success, non-zero if a required key
 * (host, path, device_name) is missing. */
int config_parse(const char *text, config_t *out);

#endif
```

- [ ] **Step 4: Write the implementation**

Create `ds-ha-bridge/source/config.c`:

```c
#include "config.h"
#include <stdlib.h>
#include <string.h>

static void copy_trimmed(char *dst, size_t dstsize, const char *src, size_t len) {
    while (len > 0 && (src[len - 1] == '\r' || src[len - 1] == ' ' ||
                       src[len - 1] == '\t')) {
        len--;
    }
    if (len >= dstsize) {
        len = dstsize - 1;
    }
    memcpy(dst, src, len);
    dst[len] = '\0';
}

int config_parse(const char *text, config_t *out) {
    memset(out, 0, sizeof(*out));
    out->port = 8123;
    out->interval_sec = 30;

    const char *p = text;
    while (*p) {
        const char *eol = strchr(p, '\n');
        size_t linelen = eol ? (size_t)(eol - p) : strlen(p);
        const char *line = p;

        if (linelen > 0 && line[0] != '#') {
            const char *eq = memchr(line, '=', linelen);
            if (eq) {
                size_t keylen = (size_t)(eq - line);
                const char *val = eq + 1;
                size_t vallen = linelen - keylen - 1;

                char key[32];
                copy_trimmed(key, sizeof(key), line, keylen);

                if (strcmp(key, "host") == 0) {
                    copy_trimmed(out->host, sizeof(out->host), val, vallen);
                } else if (strcmp(key, "port") == 0) {
                    char buf[16];
                    copy_trimmed(buf, sizeof(buf), val, vallen);
                    out->port = atoi(buf);
                } else if (strcmp(key, "path") == 0) {
                    copy_trimmed(out->path, sizeof(out->path), val, vallen);
                } else if (strcmp(key, "interval_sec") == 0) {
                    char buf[16];
                    copy_trimmed(buf, sizeof(buf), val, vallen);
                    out->interval_sec = atoi(buf);
                } else if (strcmp(key, "device_name") == 0) {
                    copy_trimmed(out->device_name, sizeof(out->device_name),
                                 val, vallen);
                }
            }
        }
        if (!eol) {
            break;
        }
        p = eol + 1;
    }

    if (out->host[0] == '\0' || out->path[0] == '\0' ||
        out->device_name[0] == '\0') {
        return 1;
    }
    if (out->interval_sec <= 0) {
        out->interval_sec = 30;
    }
    if (out->port <= 0) {
        out->port = 8123;
    }
    return 0;
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=config
```
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/config.h ds-ha-bridge/source/config.c ds-ha-bridge/tests/host/test_config.c
git commit -m "feat(ds): config parser with defaults and required-key validation"
```

---

## Task 3: JSON serializer (pure)

**Files:**
- Create: `ds-ha-bridge/include/json.h`
- Create: `ds-ha-bridge/source/json.c`
- Create: `ds-ha-bridge/tests/host/test_json.c`

Serializes a `telemetry_t` to the §4 contract. Unknown fields (sentinels / empty
strings) are omitted; nested objects are dropped entirely when all their members
are unknown. Strings are escaped for `"` and `\`.

- [ ] **Step 1: Write the failing test**

Create `ds-ha-bridge/tests/host/test_json.c`:

```c
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
    DONE();
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=json
```
Expected: compile error (`json.h` not found).

- [ ] **Step 3: Write the header**

Create `ds-ha-bridge/include/json.h`:

```c
#ifndef DS_HA_BRIDGE_JSON_H
#define DS_HA_BRIDGE_JSON_H

#include <stddef.h>
#include "telemetry_types.h"

/* Serialize telemetry into buf. Returns bytes written (excl. NUL), or -1 if
 * the buffer is too small. */
int json_build(char *buf, size_t bufsize, const telemetry_t *t);

#endif
```

- [ ] **Step 4: Write the implementation**

Create `ds-ha-bridge/source/json.c`:

```c
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
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=json
```
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/json.h ds-ha-bridge/source/json.c ds-ha-bridge/tests/host/test_json.c
git commit -m "feat(ds): JSON serializer with field omission and escaping"
```

---

## Task 4: Battery mapping (pure)

**Files:**
- Create: `ds-ha-bridge/include/battmap.h`
- Create: `ds-ha-bridge/source/battmap.c`
- Create: `ds-ha-bridge/tests/host/test_battmap.c`

libnds `getBatteryLevel()` returns a raw value: low nibble = level, bit `0x80` =
charging. The DSi level nibble ranges 0..15 with the meaningful steps documented
below; the DS reports only 3 (low) or 15 (full). This pure mapping converts the
raw value to 0..100 and a charging flag. **The exact DSi step values must be
confirmed on hardware (Task 7 manual step); the table here is the unit under
test and the single place to adjust.**

- [ ] **Step 1: Write the failing test**

Create `ds-ha-bridge/tests/host/test_battmap.c`:

```c
#include "check.h"
#include "battmap.h"

int main(void) {
    /* DSi nibble steps */
    CHECK(batt_to_percent(0x0) == 0);
    CHECK(batt_to_percent(0x1) == 5);
    CHECK(batt_to_percent(0x2) == 25);
    CHECK(batt_to_percent(0x3) == 50);
    CHECK(batt_to_percent(0x4) == 75);
    CHECK(batt_to_percent(0x5) == 100);
    CHECK(batt_to_percent(0xF) == 100); /* DS "full" */
    CHECK(batt_to_percent(0x3 | 0x80) == 50); /* charging bit ignored for % */

    /* charging flag */
    CHECK(batt_is_charging(0x80 | 0x3) == 1);
    CHECK(batt_is_charging(0x3) == 0);

    /* clamp */
    CHECK(batt_to_percent(0x6) == 100);
    DONE();
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=battmap
```
Expected: compile error (`battmap.h` not found).

- [ ] **Step 3: Write the header**

Create `ds-ha-bridge/include/battmap.h`:

```c
#ifndef DS_HA_BRIDGE_BATTMAP_H
#define DS_HA_BRIDGE_BATTMAP_H

/* Convert a libnds getBatteryLevel() raw value to 0..100 percent. */
int batt_to_percent(int raw);

/* Return 1 if the charging bit (0x80) is set, else 0. */
int batt_is_charging(int raw);

#endif
```

- [ ] **Step 4: Write the implementation**

Create `ds-ha-bridge/source/battmap.c`:

```c
#include "battmap.h"

#define CHARGING_BIT 0x80

int batt_is_charging(int raw) {
    return (raw & CHARGING_BIT) ? 1 : 0;
}

int batt_to_percent(int raw) {
    int level = raw & 0x0F;
    switch (level) {
        case 0x0: return 0;
        case 0x1: return 5;
        case 0x2: return 25;
        case 0x3: return 50;
        case 0x4: return 75;
        case 0x5: return 100;
        case 0xF: return 100; /* DS full */
        default:  return 100; /* clamp unexpected high values */
    }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=battmap
```
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/battmap.h ds-ha-bridge/source/battmap.c ds-ha-bridge/tests/host/test_battmap.c
git commit -m "feat(ds): battery raw->percent mapping and charging flag"
```

---

## Task 5: Identity helpers (pure)

**Files:**
- Create: `ds-ha-bridge/include/identity.h`
- Create: `ds-ha-bridge/source/identity.c`
- Create: `ds-ha-bridge/tests/host/test_identity.c`

The DSi firmware nickname is UTF-16; we narrow to ASCII (non-ASCII → `?`). The
firmware language byte maps to a 2-letter code.

- [ ] **Step 1: Write the failing test**

Create `ds-ha-bridge/tests/host/test_identity.c`:

```c
#include "check.h"
#include "identity.h"

int main(void) {
    unsigned short name[] = {'H', 'u', 'd', 's', 'o', 'n'};
    char out[24];
    nickname_to_ascii(name, 6, out, sizeof(out));
    CHECK_STR(out, "Hudson");

    unsigned short accented[] = {'C', 0x00E9, 'u'}; /* 'é' -> '?' */
    nickname_to_ascii(accented, 3, out, sizeof(out));
    CHECK_STR(out, "C?u");

    /* truncation respects buffer */
    unsigned short longn[] = {'A','A','A','A','A'};
    char small[3];
    nickname_to_ascii(longn, 5, small, sizeof(small));
    CHECK_STR(small, "AA");

    CHECK_STR(language_code(0), "ja");
    CHECK_STR(language_code(1), "en");
    CHECK_STR(language_code(2), "fr");
    CHECK_STR(language_code(3), "de");
    CHECK_STR(language_code(4), "it");
    CHECK_STR(language_code(5), "es");
    CHECK_STR(language_code(6), "zh");
    CHECK_STR(language_code(99), "");
    DONE();
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=identity
```
Expected: compile error (`identity.h` not found).

- [ ] **Step 3: Write the header**

Create `ds-ha-bridge/include/identity.h`:

```c
#ifndef DS_HA_BRIDGE_IDENTITY_H
#define DS_HA_BRIDGE_IDENTITY_H

#include <stddef.h>

/* Narrow a UTF-16 nickname of `len` units into an ASCII C-string in `out`
 * (NUL-terminated, never overflows `outsize`). Non-ASCII -> '?'. */
void nickname_to_ascii(const unsigned short *utf16, int len,
                       char *out, size_t outsize);

/* DSi firmware language byte -> 2-letter code; "" if unknown. */
const char *language_code(int lang);

#endif
```

- [ ] **Step 4: Write the implementation**

Create `ds-ha-bridge/source/identity.c`:

```c
#include "identity.h"

void nickname_to_ascii(const unsigned short *utf16, int len,
                       char *out, size_t outsize) {
    size_t o = 0;
    for (int i = 0; i < len && o + 1 < outsize; i++) {
        unsigned short c = utf16[i];
        out[o++] = (c >= 0x20 && c < 0x7F) ? (char)c : '?';
    }
    out[o] = '\0';
}

const char *language_code(int lang) {
    switch (lang) {
        case 0: return "ja";
        case 1: return "en";
        case 2: return "fr";
        case 3: return "de";
        case 4: return "it";
        case 5: return "es";
        case 6: return "zh";
        case 7: return "ko";
        default: return "";
    }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=identity
```
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/identity.h ds-ha-bridge/source/identity.c ds-ha-bridge/tests/host/test_identity.c
git commit -m "feat(ds): nickname UTF-16->ASCII and language code mapping"
```

---

## Task 6: HTTP request builder (pure)

**Files:**
- Create: `ds-ha-bridge/include/httpreq.h`
- Create: `ds-ha-bridge/source/httpreq.c`
- Create: `ds-ha-bridge/tests/host/test_httpreq.c`

Builds a complete HTTP/1.1 POST request string (headers + body) with a correct
`Content-Length`. The socket code in Task 9 only sends this buffer.

- [ ] **Step 1: Write the failing test**

Create `ds-ha-bridge/tests/host/test_httpreq.c`:

```c
#include "check.h"
#include "httpreq.h"
#include <string.h>

static int contains(const char *h, const char *n) { return strstr(h, n) != NULL; }

int main(void) {
    char buf[512];
    const char *body = "{\"device\":\"dsi\"}";
    int n = http_build_request(buf, sizeof(buf),
                               "192.168.31.150", 8123,
                               "/api/webhook/abc123", body);
    CHECK(n > 0);
    CHECK(contains(buf, "POST /api/webhook/abc123 HTTP/1.1\r\n"));
    CHECK(contains(buf, "Host: 192.168.31.150:8123\r\n"));
    CHECK(contains(buf, "Content-Type: application/json\r\n"));
    CHECK(contains(buf, "Content-Length: 16\r\n")); /* strlen(body) == 16 */
    CHECK(contains(buf, "Connection: close\r\n"));
    CHECK(contains(buf, "\r\n\r\n{\"device\":\"dsi\"}"));

    /* overflow guard */
    char tiny[10];
    CHECK(http_build_request(tiny, sizeof(tiny), "h", 80, "/p", body) == -1);
    DONE();
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=httpreq
```
Expected: compile error (`httpreq.h` not found).

- [ ] **Step 3: Write the header**

Create `ds-ha-bridge/include/httpreq.h`:

```c
#ifndef DS_HA_BRIDGE_HTTPREQ_H
#define DS_HA_BRIDGE_HTTPREQ_H

#include <stddef.h>

/* Build a full HTTP/1.1 POST request into buf. Returns length (excl. NUL),
 * or -1 if the buffer is too small. */
int http_build_request(char *buf, size_t bufsize, const char *host, int port,
                       const char *path, const char *body);

#endif
```

- [ ] **Step 4: Write the implementation**

Create `ds-ha-bridge/source/httpreq.c`:

```c
#include "httpreq.h"
#include <stdio.h>
#include <string.h>

int http_build_request(char *buf, size_t bufsize, const char *host, int port,
                       const char *path, const char *body) {
    int n = snprintf(
        buf, bufsize,
        "POST %s HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n"
        "%s",
        path, host, port, strlen(body), body);
    if (n < 0 || (size_t)n >= bufsize) {
        return -1;
    }
    return n;
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test TESTS=httpreq
```
Expected: `ok`.

- [ ] **Step 6: Run the entire host suite**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test
```
Expected: each module prints `ok`.

- [ ] **Step 7: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/httpreq.h ds-ha-bridge/source/httpreq.c ds-ha-bridge/tests/host/test_httpreq.c
git commit -m "feat(ds): HTTP POST request builder with content-length"
```

---

## Task 7: Telemetry collection (libnds glue)

**Files:**
- Create: `ds-ha-bridge/include/telemetry.h`
- Create: `ds-ha-bridge/source/telemetry.c`

Not host-testable (uses libnds). It fills a `telemetry_t` using the pure helpers
from Tasks 4–5. Verified by the on-device manual check at the end of this task.

- [ ] **Step 1: Write the header**

Create `ds-ha-bridge/include/telemetry.h`:

```c
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
```

- [ ] **Step 2: Write the implementation**

Create `ds-ha-bridge/source/telemetry.c`:

```c
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
    nickname_to_ascii(PersonalData->name, PersonalData->nameLen,
                      t->nickname, sizeof(t->nickname));
    t->color = PersonalData->theme;
    snprintf(t->language, sizeof(t->language), "%s",
             language_code(PersonalData->language));

    /* Wi-Fi values supplied by caller (from the wifi module). */
    t->rssi = rssi;
    if (ssid) {
        snprintf(t->ssid, sizeof(t->ssid), "%s", ssid);
    }

    t->uptime_s = uptime_s;
}
```

- [ ] **Step 3: Verify it compiles for the DS**

This requires the full build wired up (Task 11 Makefile). After Task 11, run
`make` in `ds-ha-bridge/` and confirm `telemetry.c` compiles without errors.
Expected: no `getBatteryLevel`/`PersonalData`/`localtime` symbol errors.

**Hardware confirmation note:** On a real DSi, print `getBatteryLevel()`'s raw
value to the screen once and confirm the nibble values match the `battmap.c`
table (Task 4); adjust the table if the observed steps differ. This is the only
place battery semantics live.

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/telemetry.h ds-ha-bridge/source/telemetry.c
git commit -m "feat(ds): collect telemetry from libnds (battery, RTC, identity)"
```

---

## Task 8: Wi-Fi connection (libnds glue)

**Files:**
- Create: `ds-ha-bridge/include/wifi.h`
- Create: `ds-ha-bridge/source/wifi.c`

Connects using the DSi's stored WPA2 settings and reports association status,
RSSI and SSID. Not host-testable; verified in Task 10's integration run.

- [ ] **Step 1: Write the header**

Create `ds-ha-bridge/include/wifi.h`:

```c
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
```

- [ ] **Step 2: Write the implementation**

Create `ds-ha-bridge/source/wifi.c`:

```c
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
```

**API note:** dswifi's exact getter for the *connected* AP's RSSI/SSID varies by
version. If `WIFIGETDATA_RSSI` / `Wifi_AccessPoint.rssi` differ in your BlocksDS
build, the fallback is to send `rssi = TLM_UNKNOWN_RSSI` and `ssid = ""` — the HA
side already renders those as `unknown` and presence still works. Confirm during
Task 10 and adjust this file only.

- [ ] **Step 3: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/wifi.h ds-ha-bridge/source/wifi.c
git commit -m "feat(ds): wifi bring-up via stored DSi WPA2 settings + rssi/ssid"
```

---

## Task 9: HTTP POST over lwIP sockets (libnds glue)

**Files:**
- Create: `ds-ha-bridge/include/httppost.h`
- Create: `ds-ha-bridge/source/httppost.c`

Sends the request built in Task 6 over a TCP socket and returns the HTTP status
code. Not host-testable; verified in Task 10.

- [ ] **Step 1: Write the header**

Create `ds-ha-bridge/include/httppost.h`:

```c
#ifndef DS_HA_BRIDGE_HTTPPOST_H
#define DS_HA_BRIDGE_HTTPPOST_H

/* POST `body` to http://host:port/path. Returns the HTTP status code
 * (e.g. 200), or a negative value on socket/connection error. */
int http_post(const char *host, int port, const char *path, const char *body);

#endif
```

- [ ] **Step 2: Write the implementation**

Create `ds-ha-bridge/source/httppost.c`:

```c
#include "httppost.h"
#include "httpreq.h"

#include <netdb.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int http_post(const char *host, int port, const char *path, const char *body) {
    char request[1024];
    int reqlen = http_build_request(request, sizeof(request), host, port,
                                    path, body);
    if (reqlen < 0) {
        return -1;
    }

    struct hostent *he = gethostbyname(host);
    if (!he) {
        return -2;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return -3;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    memcpy(&addr.sin_addr, he->h_addr_list[0], (size_t)he->h_length);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        closesocket(sock);
        return -4;
    }

    int sent = 0;
    while (sent < reqlen) {
        int w = send(sock, request + sent, reqlen - sent, 0);
        if (w <= 0) {
            closesocket(sock);
            return -5;
        }
        sent += w;
    }

    /* Read just enough to parse the status line: "HTTP/1.1 200 OK". */
    char resp[64];
    int got = recv(sock, resp, sizeof(resp) - 1, 0);
    closesocket(sock);
    if (got <= 0) {
        return -6;
    }
    resp[got] = '\0';

    /* Parse the status code after the first space. */
    char *space = strchr(resp, ' ');
    if (!space) {
        return -7;
    }
    return atoi(space + 1);
}
```

**API note:** On BlocksDS/libnds, lwIP exposes BSD sockets; `closesocket()` is
the dswifi close. If your build uses `close()` for sockets instead, swap the two
`closesocket` calls. Confirm during Task 10.

- [ ] **Step 3: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/include/httppost.h ds-ha-bridge/source/httppost.c
git commit -m "feat(ds): HTTP POST over lwIP sockets returning status code"
```

---

## Task 10: Main loop, UI, and SD config loading

**Files:**
- Create: `ds-ha-bridge/source/main.c`
- Create: `ds-ha-bridge/dspico_ha.cfg.example`

Loads `/dspico_ha.cfg` from the SD via libfat, brings up Wi-Fi, then loops:
collect → serialize → POST → status line → sleep `interval_sec`. Exits on
START+SELECT. Not host-testable; verified in melonDS and on hardware.

- [ ] **Step 1: Write the sample config**

Create `ds-ha-bridge/dspico_ha.cfg.example`:

```text
# Copy to the SD card root as /dspico_ha.cfg and edit.
# Use the webhook URL shown by the Home Assistant "DSpico" integration.
host=192.168.31.150
port=8123
path=/api/webhook/REPLACE_WITH_WEBHOOK_ID
interval_sec=30
device_name=dsi-quarto
```

- [ ] **Step 2: Write main.c**

Create `ds-ha-bridge/source/main.c`:

```c
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
```

- [ ] **Step 3: Build the ROM (after Task 11 Makefile exists)**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge
make
```
Expected: produces `ds-ha-bridge.nds` with no errors. (If a dswifi/socket
symbol mismatch appears, apply the API notes in Tasks 8/9.)

- [ ] **Step 4: Integration test in melonDS**

Run the HA integration locally (`.venv/bin/pytest` green, then a real HA dev
instance with the `dspico` integration added and its webhook URL). Configure
melonDS networking (Config → Wifi → enable, libslirp), put `ds-ha-bridge.nds` +
a `dspico_ha.cfg` (pointing at the HA host) on a virtual SD, and launch.

Expected: the DS shows `OK 200`; in HA, `binary_sensor.<name>_presence` is `on`
and `sensor.<name>_battery` shows a value. Then close the app and confirm
presence flips `off` after `interval_sec * 3`.

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/source/main.c ds-ha-bridge/dspico_ha.cfg.example
git commit -m "feat(ds): main loop, UI, and SD config loading"
```

---

## Task 11: BlocksDS Makefile and README

**Files:**
- Create: `ds-ha-bridge/Makefile`
- Create: `ds-ha-bridge/README.md`

- [ ] **Step 1: Write the BlocksDS Makefile**

Create `ds-ha-bridge/Makefile`:

```make
# ds-ha-bridge — BlocksDS ROM build.
# Requires BlocksDS installed and BLOCKSDS exported (default below).
export BLOCKSDS ?= /opt/blocksds/core

NAME       := ds-ha-bridge
GAME_TITLE := DS HA Bridge
GAME_SUBTITLE := Telemetry to Home Assistant

SOURCEDIRS := source
INCLUDEDIRS := include

# DSi mode is required for WPA2 Wi-Fi.
DSISUPPORT := 1

LIBS    := -ldswifi9 -lfat -lnds9
LIBDIRS := $(BLOCKSDS)/libs/dswifi \
           $(BLOCKSDS)/libs/libfat \
           $(BLOCKSDS)/libs/libnds

include $(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile
```

**Note:** This mirrors the BlocksDS `templates/rom` Makefile. If your BlocksDS
version names variables differently, copy `$BLOCKSDS/../templates/rom/Makefile`
as the base and set `SOURCEDIRS`, `INCLUDEDIRS`, `LIBS`, `LIBDIRS`, and
`DSISUPPORT := 1` as above.

- [ ] **Step 2: Verify the full build**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge
make clean && make
```
Expected: `ds-ha-bridge.nds` is produced. This also validates Tasks 7–10 compile.

- [ ] **Step 3: Re-run the host suite (regression)**

Run:
```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant/ds-ha-bridge/tests/host
make test
```
Expected: every module prints `ok`.

- [ ] **Step 4: Write the README**

Create `ds-ha-bridge/README.md`:

```markdown
# ds-ha-bridge

Nintendo DSi homebrew that reports telemetry to Home Assistant (the `dspico`
integration). Runs on a DSi via the DSpico flashcart.

## Requirements

- A **DSi** (or 3DS in DSi mode). The original DS is not supported (no WPA2).
- Wi-Fi already configured in the DSi **System Settings → Internet → Advanced
  Setup** (this is the WPA2 connection the app reuses).
- The `dspico` Home Assistant integration installed and added, so you have a
  webhook URL.

## Build

1. Install BlocksDS and `export BLOCKSDS=/opt/blocksds/core`.
2. `make` → produces `ds-ha-bridge.nds`.

## Install

1. Copy `ds-ha-bridge.nds` to the DSpico SD card.
2. Copy `dspico_ha.cfg.example` to the SD root as `dspico_ha.cfg` and edit
   `host`, `path` (the webhook path from HA), and `device_name`.
3. Launch `ds-ha-bridge` from Pico Launcher.

## Tests

- Pure C units: `cd tests/host && make test`.
- Integration: see the plan's Task 10 (melonDS + a running HA).

## Limitation

The DS runs one app at a time. This bridge reports **only while it is the
foreground app** — launching a retail game stops telemetry until you return to
the bridge.
```

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/dspico-home-assistant
git add ds-ha-bridge/Makefile ds-ha-bridge/README.md
git commit -m "build(ds): BlocksDS Makefile and README"
```

---

## Self-Review (completed during planning)

**Spec coverage:** Wi-Fi via stored DSi WPA2 settings (Task 8) · telemetry
battery/RTC/identity/RSSI/SSID/uptime (Tasks 4,5,7,8) · JSON contract §4 exactly
(Task 3, matches HA `parse_payload`) · webhook POST transport (Tasks 6,9) · SD
config `host/port/path/interval_sec/device_name` (Tasks 2,10) · on-screen UI +
error handling (config halt, Wi-Fi retry 10s, POST error shown, never crash)
(Task 10) · build (Task 11) · foreground-only limitation documented (README).

**Placeholder scan:** none. Every code step has full code. Hardware-dependent
semantics (battery nibble table, dswifi RSSI/SSID getter, socket close name) are
implemented concretely with explicit "confirm on hardware / adjust here" notes
and a safe `unknown` fallback — not deferred placeholders.

**Type consistency:** `telemetry_t` fields and sentinels (`TLM_UNKNOWN_INT`,
`TLM_UNKNOWN_RSSI`) are used identically in `telemetry_types.h`, `json.c`,
`telemetry.c`, `wifi.c`. `config_t` (`host/port/path/interval_sec/device_name`)
matches between `config.h`, `config.c`, and `main.c`. `json_build(buf,bufsize,t)`,
`http_build_request(buf,bufsize,host,port,path,body)`, `http_post(host,port,path,body)`,
`telemetry_collect(t,device_name,rssi,ssid,uptime_s)`, `wifi_up/_is_connected/_rssi/_ssid`
signatures are consistent across their headers and call sites in `main.c`. The
emitted JSON keys (`device`, `fw`, `battery.level/charging`, `rtc`,
`identity.nickname/color/language`, `wifi.rssi/ssid`, `uptime_s`) match the HA
`TELEMETRY_SCHEMA` exactly.
