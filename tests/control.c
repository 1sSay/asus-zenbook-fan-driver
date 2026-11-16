/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
/* Protocol and cleanup tests; no root or hardware required. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <sys/io.h>
#include <time.h>
#include "fan.h"
#include <stdio.h>
static int selected, mode, duty[2], pending, reply, command, used;
static int control_writes, inject_read_failure, reject_auto;
static unsigned char payload[3];

unsigned char fake_inb(unsigned short port) {
    if (port == STATUS_PORT) return pending;
    assert(port == DATA_PORT && pending);
    pending = 0;
    return reply;
}

void fake_outb(unsigned char value, unsigned short port) {
    if (port == STATUS_PORT) {
        assert(value == 0xff || value == 0xbb || value == 0xdd);
        command = value;
        used = 0;
        return;
    }
    assert(port == DATA_PORT && used < 3);
    payload[used++] = value;
    if (command == 0xbb) {
        assert(used == 1 && value == 0x50);
        reply = 8;
        pending = 1;
    } else if (used == 3) {
        assert(command == 0xdd);
        int reg = payload[1];
        if (payload[0] == 0x82) {
            assert(reg == 0x31 || reg == 0x32 || reg == 0x35);
            if (reg == 0x32) { assert(value <= 1); selected = value; }
            if (reg == 0x31) {
                assert(value <= 1);
                if (!reject_auto || value != 0) mode = value;
                ++control_writes;
            }
            if (reg == 0x35) {
                assert(mode == 1 && value == 255);
                duty[selected] = value;
                ++control_writes;
            }
        } else {
            assert(payload[0] == 0x02 && value == 0);
            if (inject_read_failure && mode && reg == 0x34) return;
            int rpm = duty[selected] == 255 ? (selected == 0 ? 6100 : 6500) : 4200;
            switch (reg) {
                case 0x30: reply = 2; break;
                case 0x31: reply = mode; break;
                case 0x33: reply = rpm & 255; break;
                case 0x34: reply = rpm >> 8; break;
                case 0x35: reply = duty[selected]; break;
                default: assert(0);
            }
            pending = 1;
        }
    }
}

int fake_nanosleep(const struct timespec *request, struct timespec *remaining) {
    (void)request;
    (void)remaining;
    return 0;
}

volatile sig_atomic_t interrupted;
void on_signal(int sig) { (void)sig; interrupted=1; }
int delay_ms(long ms) { (void)ms; return interrupted ? -1 : 0; }
int main(void) {
    struct measurement data = {0};
    assert(measure(&data) == 0);
    assert(data.completed && mode == 1 && duty[0] == 255 && duty[1] == 255);
    assert(data.before[0] == 4200 && data.before[1] == 4200);
    assert(data.peaks[0] == 6100 && data.peaks[1] == 6500);
    assert(restore_auto() == 0 && mode == 0);
    int before = control_writes;
    assert(write_control(0x35, 0) == -1);
    assert(write_control(0x35, 128) == -1);
    assert(write_control(0x32, 1) == -1);
    assert(write_control(0x31, 2) == -1);
    assert(control_writes == before);
    inject_read_failure = 1;
    data = (struct measurement){0};
    assert(measure(&data) == -1 && !data.completed);
    assert(restore_auto() == 0 && mode == 0);
    inject_read_failure = 0;
    on_signal(SIGTERM);
    before = control_writes;
    assert(measure(&data) == -1 && control_writes == before);
    /* Restoration is allowed even with the interrupt flag set. */
    mode = 1;
    assert(restore_auto() == 0 && mode == 0);
    interrupted = 0;
    mode = 1;
    reject_auto = 1;
    assert(restore_auto() == -1);
    reject_auto = 0;
    assert(restore_auto() == 0);
    puts("PASS: full duty on both fans, measurement, control allowlist, read failure, interruption, verified auto restoration and failed restoration detection");
    return 0;
}
