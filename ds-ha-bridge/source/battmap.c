#include "battmap.h"

#define CHARGING_BIT 0x80

int batt_is_charging(int raw) {
    return (raw & CHARGING_BIT) ? 1 : 0;
}

int batt_to_percent(int raw) {
    int level = raw & 0x0F;
    switch (level) {
        case 0x0: return 0;
        case 0x1: return 5;
        case 0x2: return 25;
        case 0x3: return 50;
        case 0x4: return 75;
        case 0x5: return 100;
        case 0xF: return 100; /* DS full */
        default:  return 100; /* clamp unexpected high values */
    }
}
