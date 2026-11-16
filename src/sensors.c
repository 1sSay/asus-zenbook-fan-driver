/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay
 * Protocol references: Keyitdev (GPLv3+), Karmel0x (MIT). See docs/PROVENANCE.md.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/io.h>
#include <fcntl.h>
#include <time.h>
#include <unistd.h>

#include <signal.h>
#include <sys/wait.h>
#include "fan.h"
int read_rpm(void) {
    for (int attempt = 0; attempt < 3; ++attempt) {
        int high = read_register(0x34);
        if (high < 0) return -1;
        int low = read_register(0x33);
        if (low < 0) return -1;
        int high_after = read_register(0x34);
        if (high_after < 0) return -1;
        if (high != high_after) continue;
        int rpm = (high << 8) | low;
        if (rpm > 20000) {
            fprintf(stderr, "Implausible fan speed: %d RPM. Stopping.\n", rpm);
            return -1;
        }
        return rpm;
    }
    fprintf(stderr, "Unstable RPM reading. Stopping.\n");
    return -1;
}

