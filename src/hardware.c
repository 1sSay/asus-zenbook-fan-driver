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
int supported_model(void) {
    char model[256];
    FILE *file = fopen("/sys/class/dmi/id/product_name", "r");
    if (!file) return 0;
    int ok = fgets(model, sizeof(model), file) != NULL;
    fclose(file);
    if (!ok) return 0;
    model[strcspn(model, "\r\n")] = '\0';
    return !strcmp(model, "Zenbook UX425QA_UM425QA") ||
           !strcmp(model, "ZenBook UX425QA_UM425QA");
}

int verified_controller(void) { const unsigned char p[]={0x50}; return read_command(0xbb,p,1)==8 && read_register(0x30)==2; }
