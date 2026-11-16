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
void pause_poll(void) {
    struct timespec delay = {.tv_sec = 0, .tv_nsec = 100000};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
}

int wait_status(unsigned char mask, int set) {
    for (int i = 0; i < 1000; ++i) {
        unsigned char status = inb(STATUS_PORT);
        if (status == 0xff) {
            fprintf(stderr, "ASUS EC port unavailable (status=0xff). Stopping.\n");
            return -1;
        }
        if (!!(status & mask) == set) return 0;
        pause_poll();
    }
    fprintf(stderr, "ASUS EC timeout (mask=0x%02x, wanted=%d). Stopping.\n", mask, set);
    return -1;
}

int send_byte(unsigned short port, unsigned char value) {
    if (wait_status(2, 0)) return -1;
    outb(value, port);
    return 0;
}

int read_command(unsigned char command, const unsigned char *payload, size_t length) {
    unsigned char status = inb(STATUS_PORT);
    if (status == 0xff) {
        fprintf(stderr, "ASUS EC port unavailable (status=0xff). No commands sent.\n");
        return -1;
    }
    /* Do not drain an unknown pending response: another client may own it. */
    if (status & 1) {
        fprintf(stderr, "ASUS EC has a pending response. Stopping without draining it.\n");
        return -1;
    }
    if (send_byte(STATUS_PORT, 0xff) || send_byte(STATUS_PORT, command)) return -1;
    for (size_t i = 0; i < length; ++i)
        if (send_byte(DATA_PORT, payload[i])) return -1;
    if (wait_status(1, 1)) return -1;
    return inb(DATA_PORT);
}

