# ds-ha-bridge — BlocksDS ROM build.
# Requires BlocksDS installed and BLOCKSDS exported (default below).
export BLOCKSDS ?= /opt/blocksds/core

NAME       := ds-ha-bridge
GAME_TITLE := DS HA Bridge
GAME_SUBTITLE := Telemetry to Home Assistant

SOURCEDIRS := source
INCLUDEDIRS := include

# DSi mode is required for WPA2 Wi-Fi.
DSISUPPORT := 1

LIBS    := -ldswifi9 -lfat -lnds9
LIBDIRS := $(BLOCKSDS)/libs/dswifi \
           $(BLOCKSDS)/libs/libfat \
           $(BLOCKSDS)/libs/libnds

include $(BLOCKSDS)/sys/default_makefiles/rom_arm9/Makefile
