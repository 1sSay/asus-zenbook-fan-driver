/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay
 * Protocol references: Keyitdev (GPLv3+), Karmel0x (MIT). See docs/PROVENANCE.md.
 */
#ifndef HEALTHYFAN_H
#define HEALTHYFAN_H
#include <stddef.h>
#include <signal.h>
#define DATA_PORT 0x25c
#define STATUS_PORT 0x25d
extern volatile sig_atomic_t interrupted;
void pause_poll(void);
int wait_status(unsigned char mask, int set);
int send_byte(unsigned short port, unsigned char value);
int read_command(unsigned char command, const unsigned char *payload, size_t length);
int read_register(unsigned char address);
int select_fan(int index, int count);
int read_rpm(void);
int read_pair(int rpms[2]);
int supported_model(void);
int verified_controller(void);
int write_control(unsigned char reg, unsigned char value);
int restore_auto(void);
int set_profile(unsigned char duty);
int delay_ms(long milliseconds);
int run_max(void);
#define SAMPLE_COUNT 8
struct measurement {
    int before[2];
    int samples[SAMPLE_COUNT][2];
    int peaks[2];
    int completed;
    int worker_restored;
};

int measure(struct measurement *data);
void on_signal(int sig);
#endif
