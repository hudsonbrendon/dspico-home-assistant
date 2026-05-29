#ifndef DS_HA_BRIDGE_TELEMETRY_TYPES_H
#define DS_HA_BRIDGE_TELEMETRY_TYPES_H

/* Sentinels for "unknown": ints use the documented value, strings use "". */
#define TLM_UNKNOWN_INT (-1)
#define TLM_UNKNOWN_RSSI (1) /* valid RSSI is <= 0 dBm; >0 means unknown */

typedef struct {
    char device[32];      /* required, from config device_name */
    char fw[32];          /* firmware string, e.g. "ds-ha-bridge 0.1.0" */
    int  battery_level;   /* 0..100, or TLM_UNKNOWN_INT */
    int  charging;        /* 0/1, or TLM_UNKNOWN_INT */
    char rtc[20];         /* "YYYY-MM-DDTHH:MM:SS" or "" */
    char nickname[24];    /* ASCII, or "" */
    int  color;           /* 0..15, or TLM_UNKNOWN_INT */
    char language[3];     /* "en" etc, or "" */
    int  rssi;            /* dBm (<=0), or TLM_UNKNOWN_RSSI */
    char ssid[34];        /* or "" */
    int  uptime_s;        /* >=0, or TLM_UNKNOWN_INT */
} telemetry_t;

#endif
