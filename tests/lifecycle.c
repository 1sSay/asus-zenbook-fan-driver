/* SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (C) 2026 1sSay */
/* Protocol and cleanup tests; no root or hardware required. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <sys/io.h>
#include <time.h>
#include "fan.h"
#include <stdio.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>
struct mock_state {
 int selected, mode, duty[2], pending, reply, command, used;
 int control_writes, inject_read_failure, reject_auto;
 unsigned char payload[3];
 pid_t worker_pid;
};
static struct mock_state *state;
#define selected (state->selected)
#define mode (state->mode)
#define duty (state->duty)
#define pending (state->pending)
#define reply (state->reply)
#define command (state->command)
#define used (state->used)
#define control_writes (state->control_writes)
#define inject_read_failure (state->inject_read_failure)
#define reject_auto (state->reject_auto)
#define payload (state->payload)
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
                if(value==1) state->worker_pid=getpid();
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
int delay_ms(long ms) {
 struct timespec d={0,ms*10000};
 while(nanosleep(&d,&d)) if(interrupted) return -1;
 return interrupted ? -1 : 0;
}
static void pause_test(void) { struct timespec d={0,1000000}; nanosleep(&d,NULL); }
static void test_case(int fault) {
 memset(state,0,sizeof(*state)); interrupted=0;
 pid_t supervisor=fork(); assert(supervisor>=0);
 if(supervisor==0) {
   struct sigaction a={.sa_handler=on_signal}; sigemptyset(&a.sa_mask);
   sigaction(SIGTERM,&a,NULL);
   _exit(run_max()==0 ? 0 : 1);
 }
 for(int i=0;i<1000 && !state->worker_pid;i++) pause_test();
 assert(state->worker_pid>0);
 if(fault==1) assert(kill(state->worker_pid,SIGKILL)==0);
 if(fault==2) assert(kill(supervisor,SIGTERM)==0);
 if(fault==3) assert(kill(supervisor,SIGKILL)==0);
 if(fault==4) assert(kill(state->worker_pid,SIGSTOP)==0);
 int status; assert(waitpid(supervisor,&status,0)==supervisor);
 for(int i=0;i<1000 && mode!=0;i++) pause_test();
 assert(mode==0);
 if(fault==0) assert(WIFEXITED(status) && WEXITSTATUS(status)==0);
 else if(fault!=3) assert(WIFEXITED(status) && WEXITSTATUS(status)==1);
}
int main(void) {
 state=mmap(NULL,sizeof(*state),PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
 assert(state!=MAP_FAILED);
 for(int fault=0;fault<=4;fault++) test_case(fault);
 puts("PASS: real fork/reap, worker crash, supervisor signal/death, stopped-worker deadline; simulated EC only");
 return 0;
}
