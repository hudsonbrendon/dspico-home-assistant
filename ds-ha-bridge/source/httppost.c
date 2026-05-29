#include "httppost.h"
#include "httpreq.h"

#include <netdb.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int http_post(const char *host, int port, const char *path, const char *body) {
    char request[1024];
    int reqlen = http_build_request(request, sizeof(request), host, port,
                                    path, body);
    if (reqlen < 0) {
        return -1;
    }

    struct hostent *he = gethostbyname(host);
    if (!he) {
        return -2;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return -3;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    memcpy(&addr.sin_addr, he->h_addr_list[0], (size_t)he->h_length);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        closesocket(sock);
        return -4;
    }

    int sent = 0;
    while (sent < reqlen) {
        int w = send(sock, request + sent, reqlen - sent, 0);
        if (w <= 0) {
            closesocket(sock);
            return -5;
        }
        sent += w;
    }

    /* Read just enough to parse the status line: "HTTP/1.1 200 OK". */
    char resp[64];
    int got = recv(sock, resp, sizeof(resp) - 1, 0);
    closesocket(sock);
    if (got <= 0) {
        return -6;
    }
    resp[got] = '\0';

    /* Parse the status code after the first space. */
    char *space = strchr(resp, ' ');
    if (!space) {
        return -7;
    }
    return atoi(space + 1);
}

/*
 * API note: on BlocksDS/libnds, lwIP exposes BSD sockets and dswifi provides
 * closesocket(). If your build uses close() for sockets instead, swap the
 * closesocket() calls. Confirm against the BlocksDS dswifi/lwIP headers.
 */
