<!-- SPDX-License-Identifier: 0BSD -->
# Publication checklist (not executed)

The GitHub repository is deliberately private. Do not publish the desktop-config
repository or its history. The standalone repository contains only reviewed
utility files, tests, documentation, CI and packaging.

1. Finish hardware acceptance listed in README and docs/VALIDATION.md. Resolve
   any recovery failures before claiming a hardware-qualified release.
2. Obtain explicit owner approval to make the standalone repository public,
   create the GitHub release, and push AUR. The preparation tag alone does not
   publish a release. If changes are needed before publication, regenerate the
   candidate tag/archive and both checksums, then repeat the clean build.
3. Verify the package name is still free in AUR/Arch; the 2026-11-16 GitHub,
   AUR RPC and Arch package searches returned zero matches. No command with this
   name was installed on the preparation host. GitHub repository name is now
   reserved by the private repository.
4. Upload the exact locally tested `dist/asus-zenbook-fan-driver-0.1.0.tar.gz`
   to release `v0.1.0`. Do not substitute GitHub's automatic source archive: the
   prepared archive has its own reproducible byte layout and sha256. Once public,
   test PKGBUILD again from an empty source cache to verify the release URL.
5. An AUR account with the owner's **public** SSH key registered is required.
   No password or private key should be pasted into chat. Confirm SSH access
   locally with `ssh -T aur@aur.archlinux.org` after verifying the host key using
   official AUR documentation. Access has not been assumed or configured here.
6. Clone `ssh://aur@aur.archlinux.org/asus-zenbook-fan-driver.git`. Its branch
   must be `master`. Copy only `PKGBUILD`, `.SRCINFO`, and the 0BSD `LICENSE`
   from this directory. Regenerate `.SRCINFO` using `makepkg --printsrcinfo` and
   review its diff, then commit and push **after approval**. Do not upload the
   source archive, built package, application Git history or private files.

For a new local staging checkout use `git init -b master`. A prepared local
AUR checkout is in `dist/aur/` (not part of upstream source or Git history).

## Checking an installation with doctor

For every updated source candidate run `make check`, then stage without root:

```
stage=$(mktemp -d)
make DESTDIR="$stage" install
python3 "$stage/usr/bin/asus-zenbook-fan-driver" --help
```

Staged help must include `doctor` and `--json`. Fixture tests in `make check`
cover the doctor report and CLI output without equipment or a systemd manager.
Running staged `doctor` directly inspects the live `/usr`, `/sys` and `/run`,
not the staged tree; it is not a package-content verification command.
No service should be started for build, check or staged installation.

After an approved real package installation, run the following as an ordinary
user to inspect the installed paths, DMI, manager and public telemetry:

```
asus-zenbook-fan-driver doctor
asus-zenbook-fan-driver doctor --json
```

Before explicit service activation expect inactive/missing telemetry findings.
In a container without a systemd manager expect an inconclusive service check.
Exit 0 means required checks passed, 1 means a detected problem, and 2 means
inconclusive without a detected problem (invalid arguments also use 2).
See README for the JSON schema and safety/visibility limits. A DMI match or
successful report does not replace hardware acceptance or prove EC exclusivity.

These changes do not refresh the prepared v0.1.0 tag/archive/checksums. Follow
step 2 before publishing an updated candidate; packaging remains export-ignored
so archive checksums do not depend on packaging contents.

## Prepared release description

Experimental 0.1.0: restricted userspace HealthyTable driver for the tested
Zenbook UX425QA/UM425QA model and controller v8. Root service owns EC, clients
read public telemetry. Includes bounded full-duty test, verified automatic
recovery, Arch recipe and mock/process tests. Fan 1 / Fan 2 only. No DKMS,
kernel module, arbitrary PWM, temperature curves or ASUS binaries.

Historical prototype readings were hardware-tested; the refactor's hardware
lifecycle acceptance is pending. This limitation must remain in release notes
unless replaced by a dated, real hardware validation record.
