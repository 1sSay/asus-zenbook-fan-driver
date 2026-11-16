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

#define LEASE "/run/asus-fan-rpm/manual-lease"
volatile sig_atomic_t interrupted, stopping;
static void signal_handler(int sig) { interrupted=1; if(sig!=SIGUSR1) stopping=1; }
int delay_ms(long milliseconds) {
 struct timespec d={milliseconds/1000,(milliseconds%1000)*1000000};
 while(nanosleep(&d,&d)) if(errno!=EINTR || interrupted) return -1;
 return interrupted ? -1 : 0;
}
int main(int argc, char **argv) {
 if(argc!=2 || strcmp(argv[1],"--service-worker")) return 2;
 if(!supported_model() || geteuid()!=0) { fputs("Unsupported model or missing root\n",stderr); return 1; }
 int lock=open("/run/lock/asus-fan-rpm-probe.lock",O_CREAT|O_RDWR|O_NOFOLLOW,0600);
 if(lock<0 || flock(lock,LOCK_EX|LOCK_NB) || ioperm(DATA_PORT,2,1)) return 1;
 struct sigaction a={.sa_handler=signal_handler}; sigemptyset(&a.sa_mask);
 sigaction(SIGTERM,&a,NULL); sigaction(SIGINT,&a,NULL); sigaction(SIGHUP,&a,NULL); sigaction(SIGUSR1,&a,NULL);
 a.sa_flags=SA_RESTART; sigaction(SIGUSR1,&a,NULL);
 signal(SIGPIPE,SIG_IGN);
 setvbuf(stdout,NULL,_IOLBF,0);
 /* Recover only an outstanding lease created by this service, never ordinary monitoring. */
 if(access(LEASE,F_OK)==0) {
   if(!verified_controller() || restore_auto()) return 1;
   if(unlink(LEASE)) return 1;
 }
 char line[32];
 while(!stopping && fgets(line,sizeof(line),stdin)) {
   if(stopping) break;
   interrupted=0;
   int result=1, auto_ok=0, rpm[2];
   if(!verified_controller()) { puts("{\"ok\":false,\"error\":\"unsupported controller or EC failure\"}"); continue; }
   if(!strcmp(line,"poll\n")) {
     if(read_pair(rpm)) puts("{\"ok\":false,\"error\":\"EC read failed\"}");
     else printf("{\"ok\":true,\"fan_rpms\":[%d,%d]}\n",rpm[0],rpm[1]);
     continue;
   }
   if(!strcmp(line,"max\n")) {
     int lease=read_register(0x31)==0 ? open(LEASE,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600) : -1;
     if(lease>=0) { close(lease); result=run_max(); }
     auto_ok=read_register(0x31)==0;
     if(auto_ok) unlink(LEASE);
   }
   else if(!strcmp(line,"auto\n")) {
     result=restore_auto(); auto_ok=result==0; if(auto_ok) unlink(LEASE);
   }
   printf("{\"ok\":%s,\"auto_restored\":%s}\n",result==0?"true":"false",auto_ok?"true":"false");
   interrupted=0;
 }
 ioperm(DATA_PORT,2,0); close(lock); return 0;
}
