#ifndef DS_HA_BRIDGE_JSON_H
#define DS_HA_BRIDGE_JSON_H

#include <stddef.h>
#include "telemetry_types.h"

/* Serialize telemetry into buf. Returns bytes written (excl. NUL), or -1 if
 * the buffer is too small. */
int json_build(char *buf, size_t bufsize, const telemetry_t *t);

#endif
