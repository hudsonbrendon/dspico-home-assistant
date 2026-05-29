#ifndef DS_HA_BRIDGE_HTTPPOST_H
#define DS_HA_BRIDGE_HTTPPOST_H

/* POST `body` to http://host:port/path. Returns the HTTP status code
 * (e.g. 200), or a negative value on socket/connection error. */
int http_post(const char *host, int port, const char *path, const char *body);

#endif
