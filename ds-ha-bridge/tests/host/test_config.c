#include "check.h"
#include "config.h"

int main(void) {
    const char *text =
        "# DSpico bridge config\n"
        "host=192.168.31.150\n"
        "port=8123\n"
        "path=/api/webhook/abc123\n"
        "interval_sec=15\n"
        "device_name=dsi-quarto\n"
        "\n";
    config_t c;
    CHECK(config_parse(text, &c) == 0);
    CHECK_STR(c.host, "192.168.31.150");
    CHECK(c.port == 8123);
    CHECK_STR(c.path, "/api/webhook/abc123");
    CHECK(c.interval_sec == 15);
    CHECK_STR(c.device_name, "dsi-quarto");

    /* defaults when omitted */
    config_t d;
    CHECK(config_parse("host=h\npath=/p\ndevice_name=x\n", &d) == 0);
    CHECK(d.port == 8123);
    CHECK(d.interval_sec == 30);

    /* missing required host/path/device_name -> error */
    config_t e;
    CHECK(config_parse("port=8123\n", &e) != 0);
    DONE();
}
