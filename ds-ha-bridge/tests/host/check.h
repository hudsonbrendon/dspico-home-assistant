#ifndef CHECK_H
#define CHECK_H
#include <stdio.h>
#include <string.h>

static int _check_fails = 0;

#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);       \
            _check_fails++;                                              \
        }                                                                \
    } while (0)

#define CHECK_STR(a, b)                                                  \
    do {                                                                 \
        if (strcmp((a), (b)) != 0) {                                     \
            printf("FAIL %s:%d  \"%s\" != \"%s\"\n",                     \
                   __FILE__, __LINE__, (a), (b));                        \
            _check_fails++;                                              \
        }                                                                \
    } while (0)

#define DONE()                                                           \
    do {                                                                 \
        if (_check_fails) {                                              \
            printf("%d failure(s)\n", _check_fails);                     \
            return 1;                                                    \
        }                                                                \
        printf("ok\n");                                                  \
        return 0;                                                        \
    } while (0)

#endif
