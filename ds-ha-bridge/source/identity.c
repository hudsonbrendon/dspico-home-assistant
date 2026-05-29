#include "identity.h"

void nickname_to_ascii(const unsigned short *utf16, int len,
                       char *out, size_t outsize) {
    if (outsize == 0) {
        return;
    }
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
