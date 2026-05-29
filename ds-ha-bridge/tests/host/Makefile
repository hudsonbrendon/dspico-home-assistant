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

.PHONY: test clean $(TESTS)

test: $(TESTS)

define TEST_RULE
$(1):
	@echo "== $(1) =="
	@$(CC) $(CFLAGS) -o /tmp/dshb_$(1) test_$(1).c $($(1)_SRC) && /tmp/dshb_$(1)
endef

$(foreach t,$(TESTS),$(eval $(call TEST_RULE,$(t))))

clean:
	rm -f /tmp/dshb_*
