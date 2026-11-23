/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
/* Exercise the real command loop with fake permissions/controller/lease I/O. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/io.h>
#include <unistd.h>
#include "fan.h"
static int lease, mode, fail_restore, stop_profile, restores, controls;
static int mock_open(const char *path, int flags, ...) {
    if (strstr(path, "manual-lease")) {
        assert(flags & O_EXCL);
        if (lease) return -1;
        lease = 1;
    } else assert(strstr(path, "/run/lock/"));
    return 100;
}
static int mock_access(const char *path, int flags) {
    assert(strstr(path, "manual-lease") && flags == F_OK);
    return lease ? 0 : -1;
}
static int mock_unlink(const char *path) {
    assert(strstr(path, "manual-lease"));
    lease = 0;
    return 0;
}
static int mock_close(int fd) { assert(fd == 100); return 0; }
static int mock_flock(int fd, int operation) { assert(fd == 100 && operation); return 0; }
static int mock_ioperm(unsigned long from, unsigned long count, int enable) {
    assert(from == DATA_PORT && count == 2 && (enable == 0 || enable == 1)); return 0;
}
static uid_t mock_geteuid(void) { return 0; }
#define open mock_open
#define access mock_access
#define unlink mock_unlink
#define close mock_close
#define flock mock_flock
#define ioperm mock_ioperm
#define geteuid mock_geteuid
#define main worker_main
#include "../src/worker.c"
#undef main
#undef close
int supported_model(void) { return 1; }
int verified_controller(void) { return 1; }
int read_register(unsigned char reg) { assert(reg == 0x31); return mode; }
int read_pair(int rpms[2]) { rpms[0] = 0; rpms[1] = 1234; return 0; }
int restore_auto(void) { ++restores; if (fail_restore) return -1; mode = 0; return 0; }
int run_max(void) { return restore_auto(); }
int set_profile(unsigned char duty) {
    assert(lease && duty == 153); ++controls; mode = 1;
    if (stop_profile) raise(SIGTERM);
    return 0;
}
static void run_case(const char *commands, int initial_lease, int fail, int stop, int expected) {
    FILE *input = tmpfile(), *output = tmpfile();
    assert(input && output);
    fputs(commands, input); rewind(input); fflush(stdout);
    int saved_in = dup(STDIN_FILENO), saved_out = dup(STDOUT_FILENO);
    assert(dup2(fileno(input), STDIN_FILENO) >= 0 && dup2(fileno(output), STDOUT_FILENO) >= 0);
    clearerr(stdin);
    lease = initial_lease; mode = initial_lease; fail_restore = fail;
    stop_profile = stop; restores = controls = 0; stopping = interrupted = 0;
    char *args[] = {"worker", "--service-worker", NULL};
    assert(worker_main(2, args) == expected);
    fflush(stdout);
    if (initial_lease) assert(restores >= 1);
    else if (strstr(commands, "set-153")) assert(controls == 1 && restores == 1);
    else assert(controls == 0 && restores == 0); /* Monitoring never writes mode/PWM. */
    assert(lease == (fail ? 1 : 0));
    if (!fail) assert(mode == 0);
    assert(dup2(saved_in, STDIN_FILENO) >= 0 && dup2(saved_out, STDOUT_FILENO) >= 0);
    close(saved_in); close(saved_out); fclose(input); fclose(output);
}
int main(void) {
    run_case("poll\n", 0, 0, 0, 0);
    run_case("set-153\n", 0, 0, 0, 0); /* EOF restores a profile. */
    run_case("set-153\n", 0, 0, 1, 0); /* SIGTERM restores a profile. */
    run_case("set-153\n", 0, 1, 0, 1); /* Failed cleanup retains the lease. */
    run_case("poll\n", 1, 0, 0, 0); /* Restart recovery precedes polling. */
    run_case("poll\n", 1, 1, 0, 1);
    puts("PASS: worker profile EOF/signal cleanup, failed recovery lease, startup recovery, read-only polling");
    return 0;
}
