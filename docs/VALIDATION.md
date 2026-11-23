<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Validation record

2026-11-16, x86_64 Linux:

* `make check`: actual modular C protocol and control implementations linked to
  simulated EC I/O; Python telemetry age, corruption, zero RPM and UID policy
  tests. No root or hardware required.
* Real process lifecycle against simulated EC: worker SIGKILL, supervisor
  SIGTERM/SIGKILL, stopped-worker deadline and normal completion; all recover
  mode 0. Timings are scaled for testing; EC is simulated in shared memory.
* Real Python daemon process with fake hardware worker: UNIX socket permissions,
  denied unknown request, zero RPM publication and SIGTERM shutdown.
* `make DESTDIR=stage install`: only staged `/usr` paths, no service activation.
* Clean Arch package build: see `packaging/VALIDATION.md` for the separately
  recorded container build result. Cached release source is checksum-verified;
  the GitHub release download URL remains unavailable until public publication.

2026-11-18, doctor implementation, x86_64 Linux:

* `make check`: three simulated-EC C executables and 14 Python tests passed,
  including ten doctor tests using temporary files and mocked systemctl output.
  Doctor cases cover exact DMI spelling/unsupported models and architecture,
  missing/denied DMI, missing components and permissions, stopped/failed/starting
  and missing units, unavailable systemd/systemctl, timeout/query failure,
  missing/malformed/stale/future/wrong-boot telemetry, zero/null RPM, public
  error fields, exit-code precedence, JSON/text output and help.
* The existing fake-service integration test needs permission to bind a local
  UNIX socket; the suite passed outside the restricted sandbox. No raw EC or
  real maximum test was run. Doctor tests reject socket/worker creation and
  verify the only subprocess request is a bounded read-only `systemctl show`.
* `make DESTDIR=/tmp/asus-doctor-stage.culsjx install` passed. Inspected the
  staged file list and ran staged CLI `--help`; doctor and JSON help are present.
  No live service was started/enabled and no package release was rebuilt.

Historical hardware observations supplied by the owner, from the prototype:
HealthyTable 8, two fan readings, full duty on both fans, verified automatic
restoration; peaks 7700/8694 RPM. This refactor has **not** run against EC.

Release acceptance on the actual laptop remains outstanding: monitoring must
leave mode/PWM unchanged; test-max, cancellation, restore-auto, stop/restart,
worker/supervisor crash recovery, suspend/resume, upgrade and removal. Verify
both mode readback and the absence of competing EC programs. CI/mock tests do
not replace these hardware checks. No hardware-qualified release is claimed.

## 2026-11-23 candidate preparation

* Integrated doctor with current main, retaining all profile commands.
* `make check`: five C executables (protocol, control, maximum lifecycle,
  worker command loop/lease cleanup, authorization helper) and 29 Python tests
  passed. Service integration used a fake worker and a temporary UNIX socket;
  the sandbox needed a local-socket exception. No real EC or maximum test.
* Worker tests cover profile EOF/SIGTERM cleanup, failed cleanup retaining its
  lease, startup recovery before polling and selector-only monitoring.
* State tests cover persistent recovery errors after successful polling and
  same-boot restart, previous-boot exclusion, startup lease recovery, active
  operations, failed control with successful recovery, sensor/thermal refusal,
  balanced curve and malformed public control data.
* Desktop tests cover authorized/denied/cancelled/unavailable authorization,
  missing service, invalid command rejection, zero/null RPM, visible recovery
  errors, policy defaults and the helper's fixed isolated execution arguments.
* Staged install under `/tmp/asus-fan-review-stage`, staged CLI help and
  `systemd-analyze verify` passed; no service start or live installation.
* Added named balanced curve and 95 °C firmware fallback. These are candidate
  parameters, not hardware-qualified settings.

Still outstanding: real desktop agent/GUI acceptance; clean-container package
lifecycle for this updated candidate; all previously listed hardware gates.
Public conversion, release upload and AUR push were not performed.
