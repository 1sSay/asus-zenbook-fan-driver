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
int measure(struct measurement *data) {
    if (read_register(0x31) != 0 || read_pair(data->before) || interrupted) return -1;
    /* Mode is GLOBAL. Re-select each fan after enabling manual mode. */
    if (write_control(0x31, 1) || read_register(0x31) != 1) return -1;
    for (int index = 0; index < 2; ++index) {
        if (interrupted || select_fan(index, 2) || write_control(0x35, 255)) return -1;
        int duty = read_register(0x35);
        if (duty < 250 || duty > 255) {
            fprintf(stderr, "Full duty readback failed for fan %d: %d.\n", index, duty);
            return -1;
        }
    }
    fprintf(stderr, "Both fans at full duty; waiting 5 seconds for spin-up.\n");
    if (delay_ms(5000)) return -1;
    for (int sample = 0; sample < SAMPLE_COUNT; ++sample) {
        if (read_register(0x31) != 1 || read_pair(data->samples[sample])) return -1;
        for (int index = 0; index < 2; ++index) {
            if (data->samples[sample][index] > data->peaks[index])
                data->peaks[index] = data->samples[sample][index];
        }
        fprintf(stderr, "Sample %d/%d: %d / %d RPM\n", sample + 1, SAMPLE_COUNT,
                data->samples[sample][0], data->samples[sample][1]);
        if (sample + 1 < SAMPLE_COUNT && delay_ms(1000)) return -1;
    }
    data->completed = 1;
    return 0;
}

int run_max(void) {
    int result = 1;
    int channel[2];
    if (pipe(channel)) { perror("pipe"); return 1; }
    pid_t worker = fork();
    if (worker < 0) { perror("fork"); close(channel[0]); close(channel[1]); return 1; }
    if (worker == 0) {
        close(channel[0]);
        struct measurement data = {0};
        int measured = measure(&data);
        data.worker_restored = restore_auto() == 0;
        ssize_t sent = write(channel[1], &data, sizeof(data));
        close(channel[1]);
        _exit(measured == 0 && data.worker_restored && sent == sizeof(data) ? 0 : 1);
    }
    close(channel[1]);
    /* Supervisor holds the shared lock and I/O permissions while worker runs.
     * It kills/reaps the worker BEFORE cleanup to avoid competing EC writes. */
    int status = 0, reaped = 0;
    for (int tick = 0; tick < 250; ++tick) {
        pid_t state = waitpid(worker, &status, WNOHANG);
        if (state == worker) { reaped = 1; break; }
        if (state < 0 && errno != EINTR) break;
        if (interrupted) break;
        (void)delay_ms(100);
    }
    if (!reaped) {
        fprintf(stderr, "Test interrupted or 25-second deadline reached; restoring automatic mode.\n");
        (void)kill(worker, SIGKILL);
        while (waitpid(worker, &status, 0) < 0 && errno == EINTR) {}
    }
    int restored = restore_auto() == 0;
    struct measurement data = {0};
    ssize_t received = read(channel[0], &data, sizeof(data));
    close(channel[0]);
    if (restored && reaped && !interrupted && WIFEXITED(status) && WEXITSTATUS(status) == 0 &&
        received == sizeof(data) && data.completed && data.worker_restored) {
        result = 0;
    } else {
        fprintf(stderr, "No valid maximum result. Automatic mode verified: %s.\n", restored ? "yes" : "NO");
    }
    return result;
}
