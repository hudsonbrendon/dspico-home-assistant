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
