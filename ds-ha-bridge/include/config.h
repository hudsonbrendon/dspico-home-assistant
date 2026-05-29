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
