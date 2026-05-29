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
        size_t llen = linelen;
        while (llen > 0 && (*line == ' ' || *line == '\t')) {
            line++;
            llen--;
        }

        if (llen > 0 && line[0] != '#') {
            const char *eq = memchr(line, '=', llen);
            if (eq) {
                size_t keylen = (size_t)(eq - line);
                const char *val = eq + 1;
                size_t vallen = llen - keylen - 1;

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
