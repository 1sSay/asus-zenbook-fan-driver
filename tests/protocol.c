/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
/* Run without root: cc -O2 -Wall -Wextra -Werror tests/asus-fan-rpm-probe.c -o /tmp/test-asus-fan-rpm && /tmp/test-asus-fan-rpm */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <sys/io.h>
#include <time.h>

#include "fan.h"
#include <stdio.h>
static int current_fan, pending, reply, command, payload_count, write_count;
static int forced_status = -1;
static unsigned char payload_bytes[3];

unsigned char fake_inb(unsigned short port) {
    if (port == STATUS_PORT)
        return forced_status >= 0 ? forced_status : pending;
    assert(port == DATA_PORT && pending);
    pending = 0;
    return (unsigned char)reply;
}

void fake_outb(unsigned char value, unsigned short port) {
    ++write_count;
    if (port == STATUS_PORT) {
        assert(value == 0xff || value == 0xbb || value == 0xdd);
        command = value;
        payload_count = 0;
        return;
    }
    assert(port == DATA_PORT);
    assert(payload_count < 3);
    payload_bytes[payload_count++] = value;
    if (command == 0xbb) {
        assert(payload_count == 1 && value == 0x50);
        reply = 8;
        pending = 1;
    } else if (payload_count == 3) {
        assert(command == 0xdd);
        int direction = payload_bytes[0], reg = payload_bytes[1];
        if (direction == 0x82) {
            /* Fail the test on ANY write outside the fan selector. */
            assert(reg == 0x32 && value <= 1);
            current_fan = value;
        } else {
            assert(direction == 0x02 && value == 0);
            int rpm = current_fan == 0 ? 5049 : 4782;
            assert(reg == 0x30 || reg == 0x33 || reg == 0x34);
            reply = reg == 0x30 ? 2 : reg == 0x33 ? rpm & 255 : rpm >> 8;
            pending = 1;
        }
    }
}

int fake_nanosleep(const struct timespec *request, struct timespec *remaining) {
    (void)request;
    (void)remaining;
    return 0;
}

int main(void) {
    const unsigned char version[] = {0x50};
    assert(read_command(0xbb, version, sizeof(version)) == 8);
    assert(read_register(0x30) == 2);
    assert(select_fan(0, 2) == 0 && read_rpm() == 5049);
    assert(select_fan(1, 2) == 0 && read_rpm() == 4782);
    int before = write_count;
    assert(select_fan(-1, 2) == -1);
    assert(select_fan(2, 2) == -1);
    assert(select_fan(0, 3) == -1);
    forced_status = 0xff;
    assert(select_fan(0, 2) == -1);
    assert(read_register(0x30) == -1);
    forced_status = 1;
    assert(select_fan(0, 2) == -1);
    assert(read_register(0x30) == -1);
    forced_status = 2;
    assert(select_fan(0, 2) == -1);
    assert(write_count == before);
    puts("PASS: both fan indices, RPM decoding, selector-only writes, invalid indices, unavailable/busy ports");
    return 0;
}
