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
