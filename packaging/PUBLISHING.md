<!-- SPDX-License-Identifier: 0BSD -->
# Publication checklist (not executed)

The GitHub repository is deliberately private. Do not publish the desktop-config
repository or its history. The standalone repository contains only reviewed
utility files, tests, documentation, CI and packaging.

1. Review [the current publication audit](AUDIT.md) and keep deferred hardware,
   desktop and package-lifecycle acceptance explicit in an experimental release.
   Finish hardware acceptance listed in README and docs/VALIDATION.md before
   claiming a hardware-qualified release. Resolve any known recovery failures.
2. Obtain explicit owner approval to make the standalone repository public,
   create the GitHub release, and push AUR. The preparation tag alone does not
   publish a release. If changes are needed before publication, regenerate the
   candidate tag/archive and both checksums, then repeat the clean build.
3. Verify the package name is still free in AUR/Arch; the 2026-11-16 GitHub,
   AUR RPC and Arch package searches returned zero matches. No command with this
   name was installed on the preparation host. GitHub repository name is now
   reserved by the private repository.
4. Upload the exact locally tested `<bundle>/asus-zenbook-fan-driver-0.1.1.tar.gz`
   to release `v0.1.1`. Do not substitute GitHub's automatic source archive: the
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

The v0.1.0 preparation tag is historical. Use the pinned source commit from the
latest candidate record or prepare a new local bundle below. Do not upload the
old tagged archive as if it contained current changes.

## Prepared release description

Experimental 0.1.1: restricted userspace HealthyTable driver for the tested
Zenbook UX425QA/UM425QA model and controller v8. Root service owns EC, clients
read public telemetry. Includes bounded full-duty test, verified automatic
recovery, Arch recipe and mock/process tests. Fan 1 / Fan 2 only. Includes fixed candidate temperature curves, a read-only doctor, retained
recovery diagnostics and a standalone polkit-authorized desktop client. No DKMS,
kernel module, arbitrary PWM or ASUS binaries.

Historical prototype readings were hardware-tested; the refactor's hardware
lifecycle acceptance is pending. This limitation must remain in release notes
unless replaced by a dated, real hardware validation record.

## Candidate updates

`make dist` archives the fixed version tag by default. For an updated candidate
use `make DIST_REF=<reviewed-source-commit> dist` and regenerate the recipe and
.SRCINFO checksums together. Packaging remains export-ignored. The 2026-11-16
validation describes the older candidate only; repeat the clean Arch build and
public-download verification for the final approved archive. Do not move the
existing preparation tag or upload its archive as if it contained later fixes.

The desktop client adds optional `tk` and `polkit`; verify its policy, helper
(0755, no setuid/file capabilities), desktop entry and authentication agent in
the installed package. Hardware, live upgrade/removal and graphical session
acceptance remain explicit local steps.

## One-command local bundle

From an Arch development checkout with Git, Python, gzip and makepkg installed:

```
python3 packaging/prepare.py --ref HEAD
```

Commit source changes first. The command resolves HEAD to a full immutable
commit and creates a new `dist/candidate-<commit>/` directory. It includes the
exact reproducible source archive, SHA256SUMS, candidate.json with source commit,
RELEASE-NOTES.md, and an `aur/` directory with PKGBUILD/.SRCINFO/LICENSE. The
recipe checksum and generated metadata refer to the archive in that bundle.
The current locally reviewed packaging recipe is used; review it with the
chosen source version. Existing output directories are never overwritten.

This command does not build/test/install the package, access hardware, create
or move tags, change repository visibility, upload a release or push to AUR.
It prepares reviewable files. To publish later, use that exact bundle and obtain
owner approval for the selected external actions. Source changes after bundle
creation require a new bundle; packaging-only edits do not alter its archive.

## Deferred acceptance

On 2026-11-23 the owner reported normal operation on a UM425Q and deferred
further testing. Continue preparation with the experimental qualification and
limitations from CHANGELOG.md; do not mark hardware/GUI/package acceptance as
passed. No new tests on the laptop, active service or desktop are authorized.
