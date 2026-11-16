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
int write_control(unsigned char reg, unsigned char value) {
    /* Narrow allowlist: auto/manual mode and FULL duty only. */
    if (!((reg == 0x31 && value <= 1) || (reg == 0x35 && value == 255)))
        return -1;
    unsigned char status = inb(STATUS_PORT);
    if (status == 0xff || (status & 1)) return -1;
    const unsigned char payload[] = {0x82, reg, value};
    if (send_byte(STATUS_PORT, 0xff) || send_byte(STATUS_PORT, 0xdd)) return -1;
    for (size_t i = 0; i < sizeof(payload); ++i)
        if (send_byte(DATA_PORT, payload[i])) return -1;
    if (wait_status(2, 0)) return -1;
    /* Finish the transaction even if a termination signal has arrived. */
    struct timespec delay = {.tv_sec = 0, .tv_nsec = 20000000};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
    return 0;
}

int restore_auto(void) {
    for (int attempt = 0; attempt < 3; ++attempt) {
        /* After our worker stops, discard only bounded leftover replies from
         * our transaction, so a delayed read cannot block emergency restore. */
        for (int i = 0; i < 8; ++i) {
            unsigned char status = inb(STATUS_PORT);
            if (status == 0xff || !(status & 1)) break;
            (void)inb(DATA_PORT);
        }
        if (write_control(0x31, 0) == 0 && read_register(0x31) == 0) {
            fprintf(stderr, "Automatic cooling restored and verified.\n");
            return 0;
        }
    }
    fprintf(stderr, "ERROR: automatic cooling could not be verified. Run --restore-auto; if it fails, reboot.\n");
    return -1;
}

int read_pair(int rpms[2]) {
 for(int i=0;i<2;i++) { if (select_fan(i,2)) return -1; rpms[i]=read_rpm(); if(rpms[i]<0) return -1; } return 0;
}
