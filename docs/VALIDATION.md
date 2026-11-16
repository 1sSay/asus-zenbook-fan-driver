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

Historical hardware observations supplied by the owner, from the prototype:
HealthyTable 8, two fan readings, full duty on both fans, verified automatic
restoration; peaks 7700/8694 RPM. This refactor has **not** run against EC.

Release acceptance on the actual laptop remains outstanding: monitoring must
leave mode/PWM unchanged; test-max, cancellation, restore-auto, stop/restart,
worker/supervisor crash recovery, suspend/resume, upgrade and removal. Verify
both mode readback and the absence of competing EC programs. CI/mock tests do
not replace these hardware checks. No hardware-qualified release is claimed.
