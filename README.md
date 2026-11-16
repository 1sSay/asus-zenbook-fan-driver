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
sudo systemctl daemon-reload
sudo systemctl enable --now asus-zenbook-fan-driver.service
asus-zenbook-fan-driver status
asus-zenbook-fan-driver status --json
asus-zenbook-fan-driver watch --json
sudo asus-zenbook-fan-driver test-max
sudo asus-zenbook-fan-driver restore-auto
journalctl -u asus-zenbook-fan-driver.service
```

Control commands use a root-only UNIX socket with an additional SO_PEERCRED UID
check. A maximum test is a fixed bounded operation: global manual mode, full
duty on both fans, five seconds settling and eight samples. It cannot set
arbitrary PWM, fan-off or a temperature curve. Disconnecting the client does not
extend the test. An explicit restore request interrupts a running maximum test,
then serializes restoration after it. Control results are JSON; samples are
logged to the journal. A failed test returns nonzero even if recovery succeeded.

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
