<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# asus-zenbook-fan-driver 0.1.0

Experimental standalone Linux **userspace driver** for ASUS Zenbook
UX425QA/UM425QA (Ryzen 7 5800H APU), x86_64, HealthyTable 8, exactly two fans.
It is not a kernel module. Other Zenbooks are unsupported and rejected.
DMI product name must be exactly `Zenbook UX425QA_UM425QA` or
`ZenBook UX425QA_UM425QA`. No model override exists.

The root service exclusively owns raw EC port access and a lifetime lock shared
with the old prototype. Clients do not use raw I/O. Ordinary monitoring changes
only the telemetry fan selector, never PWM or cooling mode. Fan 1 and Fan 2
cool the shared APU; indices have no established CPU/GPU or left/right mapping.

## Build and use

Requires Linux x86_64, a C11 compiler, make, Python 3. On Arch install
`base-devel python`; runtime dependencies are `glibc python systemd`.

```
make
make check
make DESTDIR="$PWD/stage" install
```

Build, tests and staged install require neither root nor hardware. Install uses
`/usr`, including `/usr/lib/systemd/system/`. Build/package steps never access EC,
run a legacy installer, modify the live system or enable services.

After installing the package (explicit administrator actions):

```
asus-zenbook-fan-driver doctor
asus-zenbook-fan-driver doctor --json
sudo systemctl daemon-reload
sudo systemctl enable --now asus-zenbook-fan-driver.service
asus-zenbook-fan-driver status
asus-zenbook-fan-driver status --json
asus-zenbook-fan-driver watch --json
sudo asus-zenbook-fan-driver quiet
sudo asus-zenbook-fan-driver balanced
sudo asus-zenbook-fan-driver performance
sudo asus-zenbook-fan-driver restore-auto
sudo asus-zenbook-fan-driver test-max
journalctl -u asus-zenbook-fan-driver.service
```

`quiet` uses 80/100/120/140/153 duty from 0/50/60/70/80 °C and is capped at
60%. `balanced` uses 100/120/153/180/200 from 0/50/60/70/80 °C
and is capped at about 78%. `performance` uses 140/160/180/200/217 from 0/45/55/65/75 °C and is
capped at 85%. All profiles read the Ryzen
`k10temp` CPU sensor and use only those fixed points; users cannot select
arbitrary PWM values. A temperature rise increases cooling immediately. A
temperature fall must clear a 3 °C hysteresis band; it then reduces one fixed
curve point at most every 15 seconds, preventing rapid back-and-forth PWM
writes around a threshold. `restore-auto` returns control to the firmware. The
selected profile, CPU temperature, current duty and complete curve are shown in
`control` in JSON status. At 95 °C or above, named profiles are refused and
active profile control returns to verified firmware cooling. These candidate
curves and the threshold still require hardware acceptance. A missing/invalid CPU sensor or failed curve update returns control
to the firmware automatically. Profile changes are root-only and create a
recovery lease before manual mode; a failed change, service restart or
`restore-auto` verifies a return to firmware automatic mode.

Control commands use a root-only UNIX socket with an additional SO_PEERCRED UID
check. A maximum test is a fixed bounded operation: global manual mode, full
duty on both fans, five seconds settling and eight samples. It cannot set
arbitrary PWM, fan-off or a temperature curve. Disconnecting the client does not
extend the test. An explicit restore request interrupts a running maximum test,
then serializes restoration after it. Control results are JSON; samples are
logged to the journal. A failed test returns nonzero even if recovery succeeded.

## Read-only diagnostics (`doctor`)

Run `asus-zenbook-fan-driver doctor` as an ordinary user before hardware
acceptance or when troubleshooting an installed package. Use `doctor --json`
for scripts; `--help` lists all commands and diagnostic exit codes. It never
starts/enables the service, opens the control socket, invokes the worker,
accesses raw EC or changes mode/PWM. No root or hardware test is required.
Before service activation it is normal to report an inactive service and
missing telemetry; installing the files alone cannot produce a healthy report.

Checks include x86_64 architecture, the exact DMI allowlist above, installed
CLI/worker/service/unit/sleep hook files and their required read/execute access,
systemd unit load/active/substate/result, and public telemetry. Missing or
unreadable DMI is **unknown**, distinct from an unsupported model. The systemd
query has a five-second timeout; a missing manager, missing `systemctl`, denied
query or incomplete response is explicitly inconclusive. An inactive, failed,
starting or missing unit is a problem even when telemetry is still fresh.

Telemetry must be a valid JSON object with two integer/null readings, finite
numeric wall/monotonic timestamps no more than ten seconds old and not in the
future, and the current boot ID. Zero RPM is valid; null readings are a problem.
Missing, malformed and stale telemetry are reported separately from access
failures. Valid fresh public `error`, `control_error` and `recovery_error`
fields are shown when present. The current service publishes only `error`;
absent separate control/recovery fields appear as **Not published**, and do not
establish successful recovery or the absence of past failures. `doctor` does
not inspect root-only lease files or reconstruct control history.

Diagnostic exit codes (a detected problem takes precedence over unknown checks):

| Code | Meaning |
| --- | --- |
| 0 | All required checks passed at the time of inspection. |
| 1 | At least one problem was detected. |
| 2 | No detected problem, but a required check is inconclusive. Also used by argparse for invalid arguments. |

JSON output uses `schema_version: 1`, `exit_code`, `checks` (objects containing
`name`, `state`, `detail`) and `limits`. States are `ok`, `problem`, `unknown`
and informational `info`; details may be strings or structured objects.
A successful report is an installation/telemetry snapshot, not hardware
acceptance: DMI does not verify HealthyTable 8 or the physical fan count.
The command cannot detect all competing EC software and does not attempt a
process scan or acquire the worker lock. That lock coordinates only this
project and the old prototype; firmware and unrelated tools remain outside it.

## Recovery and lifecycle

The worker and its maximum-test supervisor share one lock and never concurrently
issue EC transactions. Each transaction has bounded polling. The maximum worker
attempts verified restoration on success, errors and signals; its supervisor
kills/reaps it on interruption or the roughly 25-second deadline, then attempts
and verifies restoration itself. Killing the supervisor alone leaves the bounded
worker's cleanup. No process can guarantee recovery after killing all protective
processes, OS failure, competing EC software or hardware failure.

A root-owned manual-lease marker is written before entering manual mode. A
restart preserves the runtime directory and recovers an outstanding lease only
after checking the supported controller again. Ordinary startup without a lease
does not change cooling mode. Stop signals reach the supervisor first
(`KillMode=mixed`); systemd allows 40 seconds for cleanup. Manual state and
recovery failure are never silently treated as valid RPM data.

The system-sleep hook synchronously stops the service before suspend/hibernate
and starts it after wake only if it was active. Stopping during a test requests
recovery; waking reopens and revalidates the controller. These hooks cannot veto
forced kernel sleep and have not yet been hardware-validated. Do not force sleep
or kill all service processes during a test. Suspend/resume testing of this
refactor remains a release gate. If restoration cannot be verified, run
`restore-auto` while the service is running; if that fails, reboot. Do not assume
PWM 0 restores automatic mode.

Do not run other direct EC programs at the same time. The lock coordinates this
project and the old prototype, not firmware or unrelated EC tools. Kernel
lockdown or missing CAP_SYS_RAWIO may deny access; there is no /dev/mem fallback.

## Telemetry and desktop clients

`/run/asus-fan-rpm/status.json` (root-owned, 0644) is atomically replaced about
every three seconds. Compatibility fields remain `updated_at` (Unix seconds)
and `fan_rpms` (two integers or nulls). Errors publish nulls, never fake zeroes;
zero RPM is valid. Additional fields describe errors, boot ID and monotonic age.
CLI rejects malformed data, future/stale timestamps, a different boot and data
older than ten seconds. A stopped service leaves null telemetry and preserves any failed-recovery lease
until successful recovery or reboot. Runtime files live only in /run.

Existing Quickshell remains a client without modifications: temperatures stay
in the bar; RPM stays in the resources popup. It already accepts the compatibility
fields and rejects telemetry older than ten seconds. No Quickshell code is part
of this driver repository.

The standalone desktop client shows telemetry and authorizes profile changes
through polkit. Install optional `tk`/`polkit` and a desktop authentication agent;
launch **ASUS Zenbook fans** from the menu. See [desktop setup](docs/DESKTOP.md)
and the [public status contract](docs/STATUS.md).

## Migration, upgrade and removal

Before migration, back up installed legacy unit and `/usr/local/libexec/asus-fan-rpm/`
if present. Stop/disable `asus-fan-rpm.service`. Install this package and explicitly
enable the new service. Units conflict to prevent simultaneous daemons. Do not
run the old maximum-test binary once the new service owns the lock.

Before upgrade or removal, run `restore-auto` if a maximum test is active, then
`sudo systemctl stop asus-zenbook-fan-driver.service`. Upgrade using pacman,
`daemon-reload`, then start the service. To remove, disable the service and
`sudo pacman -R asus-zenbook-fan-driver`; daemon-reload afterwards. Removing an
active service with raw file deletion is not supported. After verified recovery,
stopped-service runtime files may be removed with `sudo rm -r /run/asus-fan-rpm`. The package never
automatically enables the service. Keep legacy backups until migration is tested.
To roll back, stop/disable the new service before restoring/enabling the old one.

## Validation boundaries

Mock tests: selector-only monitoring, protocol decoding, unavailable/pending/busy
EC, invalid indices, bounded timeouts, full duty, allowlist rejection, read errors,
interruption and verified/failed auto recovery; malformed/stale telemetry,
zero RPM and peer UID policy. See `docs/VALIDATION.md` for the executed checks.

Historical hardware tests of the prototype on one laptop confirmed reading both
indices, maximum duty and verified return to automatic mode. Observed peaks
were 7700 RPM (Fan 1) and 8694 RPM (Fan 2), **measurements of that unit, not rated
limits**. No hardware access is performed by this refactor's build/tests. The new
service, process lifecycle, installation and suspend/resume must be validated on
the laptop before calling 0.1.0 hardware-qualified.

GPL-3.0-or-later; provenance and reference notices: `docs/PROVENANCE.md`.
Packaging files are separately 0BSD. Public release and AUR publication require
owner approval; staging in a private repository is not AUR publication.
