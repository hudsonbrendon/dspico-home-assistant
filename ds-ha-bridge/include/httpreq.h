#ifndef DS_HA_BRIDGE_HTTPREQ_H
#define DS_HA_BRIDGE_HTTPREQ_H

#include <stddef.h>

/* Build a full HTTP/1.1 POST request into buf. Returns length (excl. NUL),
 * or -1 if the buffer is too small. */
int http_build_request(char *buf, size_t bufsize, const char *host, int port,
                       const char *path, const char *body);

#endif
