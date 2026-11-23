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
int read_register(unsigned char address) {
    const unsigned char payload[] = {0x02, address, 0x00};
    return read_command(0xdd, payload, sizeof(payload));
}

int select_fan(int index, int count) {
    if (count != 2 || index < 0 || index >= count) {
        fprintf(stderr, "Fan selector restricted to indices 0 and 1 of this two-fan model.\n");
        return -1;
    }
    unsigned char status = inb(STATUS_PORT);
    if (status == 0xff || (status & 1)) {
        fprintf(stderr, "ASUS EC unavailable or pending response before selection. Stopping.\n");
        return -1;
    }
    /* The only register write in the monitoring path: select the telemetry target. */
    const unsigned char payload[] = {0x82, 0x32, (unsigned char)index};
    if (send_byte(STATUS_PORT, 0xff) || send_byte(STATUS_PORT, 0xdd)) return -1;
    for (size_t i = 0; i < sizeof(payload); ++i)
        if (send_byte(DATA_PORT, payload[i])) return -1;
    if (wait_status(2, 0)) return -1;
    struct timespec delay = {.tv_sec = 0, .tv_nsec = 20000000};
    while (nanosleep(&delay, &delay) && errno == EINTR) {}
    return 0;
}

