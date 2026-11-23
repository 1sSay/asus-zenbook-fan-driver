<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Contributing

Keep changes standalone. Do not submit private desktop configuration/history,
ASUS executables, firmware, Windows drivers or memory/EC dumps. Authored source
uses GPL-3.0-or-later SPDX headers; packaging uses 0BSD.

Preserve exact DMI/controller/fan-count checks and Fan 1 / Fan 2 labels. Only the
service worker may access EC. Monitoring must not write cooling mode or PWM.
Control APIs must remain narrow, authorized and serialized; never add arbitrary
register access, a model bypass or a generic privileged command executor.

Build and verify software with `make check` and a staged install:

```
make check
make DESTDIR="$PWD/stage" install
```

These checks use fake hardware and do not start a live service. Do not run
hardware or maximum tests without the owner's explicit authorization. Describe
exactly what was checked and what remains unverified in the PR. Changes to a
source candidate require a new pinned archive/checksum; do not modify an
already published release archive. See docs/STATUS.md for the client contract
and packaging/PUBLISHING.md for release preparation.

Report problems using the issue template. For security-sensitive issues, avoid
posting exploit details or private logs publicly; use GitHub's private security
reporting if enabled, otherwise request a private reporting channel from the
maintainer without disclosing the sensitive material.
