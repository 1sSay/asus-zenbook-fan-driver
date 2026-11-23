/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
#include <sys/io.h>
#include <time.h>
unsigned char fake_inb(unsigned short port);
void fake_outb(unsigned char value, unsigned short port);
int fake_nanosleep(const struct timespec *request, struct timespec *remaining);
#define inb fake_inb
#define outb fake_outb
#define nanosleep fake_nanosleep
