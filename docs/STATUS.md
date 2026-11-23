<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Public telemetry, schema version 1

The service atomically publishes `/run/asus-fan-rpm/status.json` (0644).
Consumers must validate both timestamps (at most ten seconds old, not in the
future) and the current boot ID before using any field. Unknown optional fields
may be ignored. Existing `updated_at` and `fan_rpms` remain compatible.

| Field | Meaning |
| --- | --- |
| `schema_version` | 1; additive extensions are permitted |
| `updated_at`, `updated_monotonic`, `boot_id` | Publication time and boot identity |
| `fan_rpms` | Exactly two integers or nulls, Fan 1 / Fan 2; zero is valid |
| `error` | Current telemetry/operation/lifecycle error, or null |
| `control.mode` | `auto`, `manual` or `unknown`; worker readback or verified control result, never inferred from RPM |
| `control.profile` | `quiet`, `balanced`, `performance`, or null (including firmware automatic mode) |
| `control.temperature_c`, `control.duty`, `control.curve` | Current profile temperature, last verified duty and fixed curve; absent values are null/empty |
| `active_operation` | Accepted serialized command, or null |
| `last_control` | Last control result: command, ok, updated_at, error; null before any result |
| `last_recovery` | Last verified recovery attempt: ok, updated_at, error; null if none is known |
| `control_error`, `recovery_error` | Retained errors, independently of the current telemetry error |

A successful poll refreshes RPM/mode but cannot clear a recovery error. Only an
explicit worker-confirmed restoration, or confirmed startup lease recovery,
clears it. Successful profile control clears the last control error; it does not
clear a previous recovery error. A failed operation may have `control_error`
while `last_recovery.ok` is true. The journal retains detailed protocol causes;
the worker returns its command-level error through the service to clients.

Startup begins with unknown mode and no selected profile. Same-boot control and
recovery history is carried across service restarts; previous-boot history is
ignored. An outstanding lease starts with an unverified-recovery error. The
worker must recover it before polling; readback of auto plus removal of the
lease confirms that startup recovery. Restart never reactivates a saved profile.
On stop, RPM becomes null and mode unknown; a remaining lease is an error.
A stopped worker's exit alone is not treated as proof of automatic mode.

Reading the mode adds a read-only worker transaction. Monitoring still writes
only the fan selector. CLI and desktop clients read public files; neither opens
EC ports. `status` exits nonzero for any published telemetry/control/recovery
error. `doctor` displays the same retained errors.
