/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc != 2 || (strcmp(argv[1], "quiet") && strcmp(argv[1], "balanced") &&
                     strcmp(argv[1], "performance") && strcmp(argv[1], "restore-auto"))) {
        fputs("Expected exactly one named profile or restore-auto\n", stderr);
        return 2;
    }
    if (geteuid() != 0) {
        fputs("Administrator authorization required through pkexec\n", stderr);
        return 1;
    }
    /* No shell, client-supplied path, environment import, UID or worker API.
     * pkexec authenticates its caller; the service verifies our kernel UID. */
    execl("/usr/bin/python3", "python3", "-I",
          "/usr/lib/asus-zenbook-fan-driver/client.py", argv[1], (char *)NULL);
    perror("Cannot execute installed control client");
    return 1;
}
