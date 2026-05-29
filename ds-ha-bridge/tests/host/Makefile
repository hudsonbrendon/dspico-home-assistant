CC      ?= gcc
CFLAGS  := -std=c11 -Wall -Wextra -O0 -g -I. -I../../include
SRCDIR  := ../../source

# Each test binary: name -> extra source modules it links (besides its test_*.c)
TESTS := smoke config json battmap identity httpreq

smoke_SRC    :=
config_SRC   := $(SRCDIR)/config.c
json_SRC     := $(SRCDIR)/json.c
battmap_SRC  := $(SRCDIR)/battmap.c
identity_SRC := $(SRCDIR)/identity.c
httpreq_SRC  := $(SRCDIR)/httpreq.c

.PHONY: test clean
test:
	@set -e; for t in $(TESTS); do \
		echo "== $$t =="; \
		$(CC) $(CFLAGS) -o /tmp/dshb_$$t test_$$t.c $($${t}_SRC) && /tmp/dshb_$$t; \
	done

clean:
	rm -f /tmp/dshb_*
