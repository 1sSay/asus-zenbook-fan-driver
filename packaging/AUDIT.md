<!-- SPDX-License-Identifier: 0BSD -->
# AUR readiness audit — 2026-11-23

Status: the standalone repository is public and experimental 0.1.1 is published
with explicit owner approval. The source downloads anonymously with the expected
SHA256. AUR submission awaits owner registration/key setup. See VALIDATION.md.
No live installation, service activation or hardware test was done.

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
* Before publication, anonymous GitHub repository and release-asset requests
  returned HTTP 404. After owner approval and publication, both are accessible;
  the source asset downloads with HTTP 200 and the expected SHA256.
* PKGBUILD uses an x86_64 source build, SPDX licenses, declared runtime and
  optional desktop dependencies, build/check/package functions and DESTDIR.
  It does not enable/start the service or install to the live root.
* `makepkg --printsrcinfo` exactly matches packaging/.SRCINFO. Both SHA256
  entries match their inputs: the published source commit
  `77dfbfc344d86fd7f5ad82facabea3b1204be589` and packaging/LICENSE.
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

1. Completed: source commit `77dfbfc344d86fd7f5ad82facabea3b1204be589`,
   reproducible 0.1.1 bundle, updated PKGBUILD/.SRCINFO and clean Arch build.
   See VALIDATION.md for the exact archive hash and namcap findings.
2. Live package lifecycle/GUI/hardware acceptance remains deferred; it must not
   be claimed from the clean-container build.
3. Completed: explicit owner approval for public conversion, release upload and
   AUR push; public repository and experimental v0.1.1 with the exact source asset
   and SHA256SUMS. Final empty-cache Arch validation uses the public download URL.
   Experimental/deferred acceptance limitations remain in the release notes.
4. Verify the owner's AUR account/public SSH key and access, recheck name
   availability, regenerate .SRCINFO with makepkg, and review the AUR diff.
   On branch master, submit only PKGBUILD, .SRCINFO and the packaging LICENSE.
   No application Git history, source archive or built package belongs in AUR.

The follow-up preparation completed clean-container/namcap checks and attempted
AUR authentication (rejected publickey). The owner has no AUR account yet; a
dedicated key pair was generated locally and the public half provided for
registration. No private key was read, committed or uploaded. No AUR push has
been done. See PUBLISHING.md and VALIDATION.md.
