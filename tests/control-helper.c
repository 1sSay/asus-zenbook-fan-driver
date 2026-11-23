/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
static int uid, executed;
static uid_t mock_geteuid(void) { return uid; }
static int mock_execl(const char *path, const char *arg, ...) {
    assert(!strcmp(path, "/usr/bin/python3") && !strcmp(arg, "python3"));
    va_list args; va_start(args, arg);
    assert(!strcmp(va_arg(args, char *), "-I"));
    assert(!strcmp(va_arg(args, char *), "/usr/lib/asus-zenbook-fan-driver/client.py"));
    assert(!strcmp(va_arg(args, char *), "balanced"));
    assert(va_arg(args, char *) == NULL);
    va_end(args); ++executed; return -1;
}
#define geteuid mock_geteuid
#define execl mock_execl
#define main helper_main
#include "../src/control-helper.c"
#undef main
int main(void) {
    char *valid[] = {"helper", "balanced", NULL};
    uid = 1000; assert(helper_main(2, valid) == 1 && executed == 0);
    uid = 0; assert(helper_main(2, valid) == 1 && executed == 1);
    const char *bad[] = {"test-max", "max", "set-255", "poll", "auto", "--help", "/bin/sh", "quiet;sh", ""};
    for (unsigned i = 0; i < sizeof(bad)/sizeof(*bad); ++i) {
        char *args[] = {"helper", (char *)bad[i], NULL};
        assert(helper_main(2, args) == 2 && executed == 1);
    }
    assert(helper_main(1, valid) == 2 && executed == 1);
    assert(helper_main(3, valid) == 2 && executed == 1);
    return 0;
}
