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
