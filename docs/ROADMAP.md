<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Remaining work

## Owner decision — 2026-11-23

The owner identifies the laptop as UM425Q and reports normal operation. Further
hardware, graphical-session and package-lifecycle testing is deferred so that
software and release preparation can proceed. This is a user report, not a new
record of DMI/EC readback or a completed acceptance procedure. Keep the exact
existing model/version/fan-count checks.

## Issue coverage

| Issue | Software delivery | Deferred acceptance |
| --- | --- | --- |
| #1 Compatibility/monitoring | Exact allowlist, two-fan telemetry, doctor | Exact DMI/controller readback and monitoring on the laptop |
| #2 Recovery/lifecycle | Bounded test, supervisor, manual lease, profile-stop recovery, persistent errors | Laptop cancellation/crashes, restart and sleep/resume |
| #3 Temperature control | Fixed curves, k10temp, hysteresis/ramp-down, thermal/sensor fallback | Intermediate PWM behavior and curve/thermal tuning |
| #4 Named profiles | Quiet, balanced, performance, CLI/status, restart never reactivates a profile | Validation of the candidate settings through #3 |
| #5 Arch package | Recipe/.SRCINFO, optional desktop dependencies, staged install, pinned source and local AUR bundle | Fresh-container dependency resolution and live install/upgrade/removal/migration |
| #6 Desktop interface | Standalone Tk client, telemetry, mode/profile/errors, authorized actions | Actual desktop session |
| #7 Doctor | Read-only checks, JSON/text, documented exit codes | Installed-system acceptance is covered by #5 |
| #8 Public status | Versioned schema, retained errors, confirmed/unknown mode, restart history | Hardware recovery confirmation through #2 |
| #9 Desktop authorization | Narrow helper/polkit policy, fresh admin authentication, fixed commands | Actual polkit agent/session |

The implementation is delivered in PR #10. Completed software does not imply
that the deferred acceptance checkboxes passed. Keep acceptance issues open
until their remaining evidence is recorded; #7/#8 may close with the PR.

## Publication preparation

The local bundle contains source archive, SHA256SUMS, source commit metadata,
release notes and an `aur/` directory containing only PKGBUILD, .SRCINFO and
packaging LICENSE. It neither creates/moves tags nor uploads anything.

Before an approved experimental publication, review the exact bundle and keep
all deferred-validation limitations in the release notes. Hardware qualification
is a separate claim; the owner's normal-operation report alone does not replace
the documented acceptance procedure. See packaging/PUBLISHING.md.
