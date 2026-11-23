<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Provenance and license audit — 2026-11-16

Primary license: GPL-3.0-or-later. Copyright (C) 2026 1sSay.
The separate `packaging/` recipes and packaging license are 0BSD.

The source was extracted file by file from the author's private prototype
(commit 7629cb7bc7d0e51e0fab7bf6fd6dbfd52ef5f341): RPM probe, bounded
maximum test, collector, and mock-controller tests. No private repository
history, desktop configuration, diagnostics dumps or research binaries are
included. The extraction and refactor retain those files' logic and tests;
this is not a clean-room implementation.

Sources inspected and compared against the prototype:

* [Keyitdev/asus-fan-control-ec](https://github.com/Keyitdev/asus-fan-control-ec),
  commit `71fa54b5c3856797bcde4cbdebbed9a49454a42e`, GPLv3+,
  Copyright (C) 2026 Keyitdev. Compared `src/ec.c`, `src/healthy.c`,
  `src/common.h`, `HOW-IT-WORKS.md`, and `LICENSE`.
  The port addresses, command bytes, HealthyTable registers, polling interval,
  poll count and settling delay agree. The upstream general-purpose transport
  drains replies and retries transactions; this implementation rejects pending
  responses for normal reads and reads RPM high/low/high to reject torn samples.
  No large verbatim C function was found. These observations do not establish
  that every small idiom is independently authored: prior protocol research
  informed the prototype. GPL-3.0-or-later is compatible with incorporating
  GPLv3+ material, including any such adaptation. Upstream attribution retained.
* [Darren80/AsusFanControlEnhanced](https://github.com/Darren80/AsusFanControlEnhanced),
  investigated commit `7599bdf90db3560a7a381b81ca3b2b965952bf56`, MIT,
  Copyright (c) 2023 Karmel0x. Compared `AsusControl.cs`, `AsusWinIO64.cs`
  and `LICENSE`. They expose fan count, fan index, RPM, test mode and PWM APIs.
  The earlier research also recorded static inspection of the bundled
  AsusWinIO64.dll. That binary is not included or fetched by this project.
  No C# implementation is copied. MIT notice is retained in
  `LICENSE.MIT-reference` conservatively; MIT permits GPL distribution when
  its notice is preserved. Its repository license is not asserted to license
  ASUS proprietary DLLs, firmware or Windows drivers.

Protocol facts are not automatically copied code. Conversely, the matching
constants and earlier research do not justify a claim of total independence.
Only authored Linux source, tests and documentation are shipped. No DLL,
Windows driver, firmware, ACPI dump or ASUS binary is included.

## Protocol used

Only x86 I/O ports data `0x25c`, status `0x25d`; preamble `0xff`.
Version is `BB 50`; table reads `DD 02 <reg> 00`, writes `DD 82 <reg> <value>`.
Registers: fan count `30`, global manual mode `31`, selector `32`, RPM low/high
`33/34`, duty `35`. Supported version is exactly 8 and count exactly 2.
Monitoring writes only selector 0 or 1, leaving 1 selected after a full sample.
The mode affects both fans. Control exposes only mode 0/1, the fixed profile
duties and bounded full duty 255; there is no generic write API or bypass.
Automatic mode is write 0 to register 31 followed by readback 0, never PWM 0.
See [../LICENSES.md](../LICENSES.md) for the license grant and file scopes.
