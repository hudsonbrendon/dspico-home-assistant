#include "check.h"
#include "battmap.h"

int main(void) {
    /* DSi nibble steps */
    CHECK(batt_to_percent(0x0) == 0);
    CHECK(batt_to_percent(0x1) == 5);
    CHECK(batt_to_percent(0x2) == 25);
    CHECK(batt_to_percent(0x3) == 50);
    CHECK(batt_to_percent(0x4) == 75);
    CHECK(batt_to_percent(0x5) == 100);
    CHECK(batt_to_percent(0xF) == 100); /* DS "full" */
    CHECK(batt_to_percent(0x3 | 0x80) == 50); /* charging bit ignored for % */

    /* charging flag */
    CHECK(batt_is_charging(0x80 | 0x3) == 1);
    CHECK(batt_is_charging(0x3) == 0);

    /* clamp */
    CHECK(batt_to_percent(0x6) == 100);
    DONE();
}
