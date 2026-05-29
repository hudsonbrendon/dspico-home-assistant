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

    /* CRLF + indented key + indented comment + no trailing newline */
    config_t f;
    CHECK(config_parse("  host=h\r\n\t# comment\r\npath=/p\r\ndevice_name=x", &f) == 0);
    CHECK_STR(f.host, "h");
    CHECK_STR(f.path, "/p");
    CHECK_STR(f.device_name, "x");

    /* malformed numbers fall back to defaults */
    config_t g;
    CHECK(config_parse("host=h\npath=/p\ndevice_name=x\nport=abc\ninterval_sec=0\n", &g) == 0);
    CHECK(g.port == 8123);
    CHECK(g.interval_sec == 30);

    /* a line without '=' is skipped cleanly */
    config_t h2;
    CHECK(config_parse("garbage\nhost=h\npath=/p\ndevice_name=x\n", &h2) == 0);
    CHECK_STR(h2.host, "h");
    DONE();
}
