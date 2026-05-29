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
