<!-- SPDX-License-Identifier: 0BSD -->
# AUR readiness audit — 2026-11-23

Status: local preparation is usable; publication still has outstanding steps.
No publication, live installation, service activation or hardware test was done.

## Licensing

Keep **GPL-3.0-or-later** for the application: strong distribution copyleft,
compatible with the recorded GPLv3-or-later protocol reference. Root LICENSE is
the complete unmodified GPLv3 text, byte-equivalent after stripping surrounding
whitespace to https://www.gnu.org/licenses/gpl-3.0.txt fetched during this audit.
LICENSES.md now provides the explicit grant, copyright, warranty disclaimer,
file scopes and distribution guidance; README links it and make install ships it.
All source/test files carry GPL-3.0-or-later SPDX identifiers.

Keep the MIT reference notice and upstream attribution. The prior provenance
review is recorded in docs/PROVENANCE.md; this audit does not claim a new
file-by-file comparison against the private prototype. The referenced Keyitdev
LICENSE was fetched read-only and contains GPLv3. Packaging independently uses
0BSD, as encouraged by Arch; the package license array describes the GPL, MIT
and 0BSD material delivered in the package, not a choice of application licenses.

References:

* https://www.gnu.org/licenses/gpl-howto.html
* https://wiki.archlinux.org/title/AUR_submission_guidelines
* https://wiki.archlinux.org/title/Arch_package_guidelines

## Checked

* AUR RPC exact-name lookup: resultcount 0; Arch package exact-name lookup:
  count 0. Name availability must be rechecked immediately before submission.
* Anonymous GitHub repository and release-asset requests both returned HTTP 404.
  This proves no public source download at the configured URL; it does not
  distinguish a private repository from a nonexistent one.
* PKGBUILD uses an x86_64 source build, SPDX licenses, declared runtime and
  optional desktop dependencies, build/check/package functions and DESTDIR.
  It does not enable/start the service or install to the live root.
* `makepkg --printsrcinfo` exactly matches packaging/.SRCINFO. Both SHA256
  entries match their inputs: the pinned source commit
  `153aecc659d5e4b321059e79be252acf4790c4fb` and packaging/LICENSE.
  The archive omits packaging and .gitattributes via export-ignore.
* Tracked paths contain standalone sources, tests, integration and documentation;
  no ASUS binaries, DLLs, Windows drivers, firmware or desktop configuration
  were found. No private repository/history was accessed or imported.
* Reviewed EC entry points: ioperm belongs to the service worker; clients do
  not access EC. Exact DMI spellings, controller 8, count 2 and Fan 1 / Fan 2
  labels remain in place. Monitoring selects fans without mode/PWM writes.
* `make check`: five C suites and 29 Python tests passed. All EC I/O is fake;
  the real production worker is compiled but not executed. After the sandbox
  denied a temporary UNIX socket, the suite passed with that restriction lifted.
* Staged `make DESTDIR=/tmp/asus-fan-aur-audit-stage install` and staged CLI help
  passed. The GPL text, MIT notice and new licensing guide are installed.
  Static `systemd-analyze verify` of the staged unit passed outside the socket
  sandbox; no unit was started or enabled.

## Still required

1. Commit/review the current source changes and prepare a **new** pinned bundle:
   `python3 packaging/prepare.py --ref <reviewed-commit>`. Copy its PKGBUILD and
   .SRCINFO back to packaging together. The currently checked-in sums correctly
   identify the historical candidate, not these new licensing edits. Do not
   reuse the old preparation tag/archive as the updated release.
2. Build the final exact bundle in a clean Arch environment with dependency
   resolution, run namcap, inspect the package and record results. Historical
   clean-container results do not validate today's final candidate. Further
   live package lifecycle/GUI/hardware testing remains deferred by the owner;
   no such acceptance is claimed. Do not run it without authorization.
3. Obtain owner approval for public conversion, release upload and AUR push.
   Publish the exact tested source asset, then build with an empty source cache
   to verify the public URL and checksum. Keep experimental/deferred acceptance
   limitations in release notes; AUR publication does not prove hardware safety.
4. Verify the owner's AUR account/public SSH key and access, recheck name
   availability, regenerate .SRCINFO with makepkg, and review the AUR diff.
   On branch master, submit only PKGBUILD, .SRCINFO and the packaging LICENSE.
   No application Git history, source archive or built package belongs in AUR.

No new clean-container build, namcap run, AUR authentication or push was done
in this audit. See PUBLISHING.md for the publication procedure and
VALIDATION.md for historical candidate records.
