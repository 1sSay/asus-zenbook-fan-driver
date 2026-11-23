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
static int curve_duty(const char *line) {
 if(!strcmp(line,"set-80\n")) return 80;
 if(!strcmp(line,"set-100\n")) return 100;
 if(!strcmp(line,"set-120\n")) return 120;
 if(!strcmp(line,"set-140\n")) return 140;
 if(!strcmp(line,"set-153\n")) return 153;
 if(!strcmp(line,"set-160\n")) return 160;
 if(!strcmp(line,"set-180\n")) return 180;
 if(!strcmp(line,"set-200\n")) return 200;
 if(!strcmp(line,"set-217\n")) return 217;
 if(!strcmp(line,"set-255\n")) return 255;
 return -1;
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
     else {
       int mode=read_register(0x31);
       printf("{\"ok\":true,\"fan_rpms\":[%d,%d],\"mode\":\"%s\"}\n",rpm[0],rpm[1],
              mode==0 ? "auto" : mode==1 ? "manual" : "unknown");
     }
     continue;
   }
   if(!strcmp(line,"max\n")) {
     int lease=read_register(0x31)==0 ? open(LEASE,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600) : -1;
     if(lease>=0) { close(lease); result=run_max(); }
     else if(access(LEASE,F_OK)==0) (void)restore_auto();
     auto_ok=read_register(0x31)==0;
     if(auto_ok) unlink(LEASE);
   }
   else if(!strcmp(line,"auto\n")) {
     result=restore_auto(); auto_ok=result==0; if(auto_ok) unlink(LEASE);
   }
   else if(curve_duty(line) >= 0) {
     unsigned char duty = (unsigned char)curve_duty(line);
     int mode=read_register(0x31);
     int lease=mode==0 ? open(LEASE,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600) : -1;
     if(lease>=0) { close(lease); result=set_profile(duty); }
     else if(mode==1 && access(LEASE,F_OK)==0) result=set_profile(duty);
     if(result) {
       auto_ok=restore_auto()==0;
       if(auto_ok) unlink(LEASE);
     }
   }
   else {
     puts("{\"ok\":false,\"error\":\"invalid control command\"}");
     continue;
   }
   printf("{\"ok\":%s,\"auto_restored\":%s,\"error\":%s}\n",result==0?"true":"false",auto_ok?"true":"false",result==0 ? "null" : "\"EC control failed; inspect journal for recovery details\"");
   interrupted=0;
 }
 /* A named profile also owns a lease; stopping must restore it. */
 int cleanup_failed=0;
 if(access(LEASE,F_OK)==0) {
   if(!verified_controller() || restore_auto()) cleanup_failed=1;
   else if(unlink(LEASE)) cleanup_failed=1;
 }
 ioperm(DATA_PORT,2,0); close(lock); return cleanup_failed;
}
