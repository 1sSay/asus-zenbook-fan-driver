<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Standalone desktop client

On Arch install the package plus optional `tk` and `polkit`, and enable your
desktop's polkit authentication agent. Launch **ASUS Zenbook fans** from the
application menu, or run:

```
python3 -I /usr/lib/asus-zenbook-fan-driver/gui.py
```

The GUI runs as your ordinary desktop user. It displays Fan 1 / Fan 2, mode,
profile and retained errors. Invalid/stale/stopped telemetry is unavailable;
0 RPM remains a valid measurement. No private panel configuration is needed.

Each profile/restore action invokes `pkexec --disable-internal-agent` with the
fixed installed `control-helper`. The polkit policy allows only the active
session to request fresh administrator authentication, with no retained grant.
Inactive/other sessions are denied. Cancellation, missing agent, unavailable
polkit and missing service are reported without enabling a profile. A timeout
or closed window cannot retract a command already accepted by the service;
use restore-auto if its result is uncertain.

The compiled helper is a normal 0755 executable, never setuid and with no file
capabilities. It requires effective UID 0 and exactly one of `quiet`, `balanced`,
`performance`, `restore-auto`; it executes the fixed installed Python client in
isolated mode. It accepts no UID, executable path, worker command or arbitrary
arguments. pkexec verifies the requesting process; the service separately checks
SO_PEERCRED. `PKEXEC_UID` and user-provided identity are never trusted. There is
no GUI authorization for test-max. The existing root CLI is unchanged.

The policy is installed under `/usr/share/polkit-1/actions/`; the helper/client
under `/usr/lib/asus-zenbook-fan-driver/`. The service remains the sole owner of
raw I/O; its socket stays 0600. See the official
[pkexec reference](https://www.freedesktop.org/software/polkit/docs/latest/pkexec.1.html)
for authentication-agent behavior and exit codes 126/127.

Automated tests validate the helper's fixed execution arguments and rejection
paths, policy defaults, authorization adapter outcomes and telemetry rendering.
They do not exercise a real graphical session or administrator authentication.
Validate those after installation before accepting the desktop integration.
