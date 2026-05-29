#include "check.h"
#include "telemetry_types.h"

int main(void) {
    telemetry_t t = {0};
    t.battery_level = 50;
    CHECK(t.battery_level == 50);
    CHECK(TLM_UNKNOWN_INT == -1);
    DONE();
}
