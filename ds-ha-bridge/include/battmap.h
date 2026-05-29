#ifndef DS_HA_BRIDGE_BATTMAP_H
#define DS_HA_BRIDGE_BATTMAP_H

/* Convert a libnds getBatteryLevel() raw value to 0..100 percent. */
int batt_to_percent(int raw);

/* Return 1 if the charging bit (0x80) is set, else 0. */
int batt_is_charging(int raw);

#endif
