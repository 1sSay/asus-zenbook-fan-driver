<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Release notes

## 0.1.1 — experimental release candidate

* Clarify GPL-3.0-or-later licensing, retained third-party notices and the
  separate 0BSD packaging license; install the licensing guide.
* Refresh the release source and AUR recipe without moving the historical
  v0.1.0 preparation tag.
* Hardware, graphical-session and live package-lifecycle acceptance remain
  deferred. The functionality and limitations below also apply to 0.1.1.

## 0.1.0 — historical preparation candidate (not published)

Standalone Linux userspace fan driver for the exact supported Zenbook
UX425QA/UM425QA DMI names, HealthyTable 8 and two fans. The owner reports a
UM425Q laptop working normally; this does not broaden the controller allowlist.

* Public Fan 1 / Fan 2 telemetry, status/watch CLI and read-only doctor.
* Quiet, balanced and performance profiles using fixed duty points, temperature
  hysteresis and gradual ramp-down. At 95 °C, return to firmware cooling.
* Root-only control socket, fixed bounded maximum test, verified restoration and
  manual-lease recovery. Stopping a named profile also attempts restoration.
* Separate confirmed/unknown mode and selected profile; retained control and
  recovery errors, including across same-boot service restarts.
* Standalone unprivileged Tk desktop client. Profile changes and restore-auto
  use a narrow polkit-authorized helper; test-max remains in the root CLI.
* systemd unit and sleep hook, Arch recipe, source archive and local AUR bundle
  preparation. No automatic service enablement, ASUS binaries or kernel module.

Hardware, graphical-session and live package-lifecycle acceptance are deferred
at the owner's request. Automated simulated-controller tests and staged/local
package builds cover software behavior only. Intermediate PWM, crash recovery
and suspend/resume of this refactor are not claimed hardware-qualified. An
unavailable temperature sensor or control error attempts verified firmware
recovery; if restoration cannot be verified, use restore-auto, then reboot if
necessary. Read README before enabling the service.

No release has been published. Repository visibility change, release upload and
AUR push each require explicit owner approval.
