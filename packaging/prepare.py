#!/usr/bin/python3
# SPDX-License-Identifier: 0BSD
# Copyright (C) 2026 1sSay
"""Prepare a local release/AUR bundle; never upload, tag, install or access EC."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True, help='reviewed source commit or tag')
    parser.add_argument('--output', type=Path, help='new output directory (must not exist)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    commit = run(['git', 'rev-parse', '--verify', args.ref + '^{commit}'], cwd=root, text=True).strip()
    # A source bundle always represents committed content. Packaging itself is
    # export-ignored; the locally reviewed recipe is copied separately.
    recipe = (root / 'packaging/PKGBUILD').read_text()
    version = re.search(r'^pkgver=([0-9]+\.[0-9]+\.[0-9]+)$', recipe, re.M)
    if version is None:
        parser.error('PKGBUILD must contain a plain numeric semantic pkgver')
    version = version[1]
    output = (args.output or root / 'dist' / ('candidate-' + commit[:12])).resolve()
    if output.exists():
        parser.error('Output already exists; choose a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.candidate-', dir=output.parent) as temporary:
        directory = Path(temporary)
        name = f'asus-zenbook-fan-driver-{version}.tar.gz'
        archive = run(['git', 'archive', '--format=tar',
                       f'--prefix=asus-zenbook-fan-driver-{version}/', commit], cwd=root)
        compressed = run(['gzip', '-n', '-c'], input=archive)
        digest = hashlib.sha256(compressed).hexdigest()
        (directory / name).write_bytes(compressed)
        aur = directory / 'aur'
        aur.mkdir()
        recipe, count = re.subn(r"(sha256sums=\(')[0-9a-f]{64}",
                                lambda match: match[1] + digest, recipe, count=1)
        if count != 1:
            parser.error('Could not update source checksum in PKGBUILD')
        (aur / 'PKGBUILD').write_text(recipe)
        (aur / 'LICENSE').write_bytes((root / 'packaging/LICENSE').read_bytes())
        (aur / '.SRCINFO').write_bytes(run(['makepkg', '--printsrcinfo'], cwd=aur))
        (directory / 'SHA256SUMS').write_text(digest + '  ' + name + '\n')
        (directory / 'candidate.json').write_text(json.dumps({
            'version': version, 'source_commit': commit, 'archive': name, 'sha256': digest,
            'hardware_acceptance': 'deferred', 'desktop_acceptance': 'deferred',
            'publication': 'requires explicit owner approval',
        }, indent=2) + '\n')
        notes = run(['git', 'show', commit + ':CHANGELOG.md'], cwd=root)
        (directory / 'RELEASE-NOTES.md').write_bytes(notes)
        directory.rename(output)
    print(output)
    print('Source commit: ' + commit)
    print('SHA256: ' + digest)
    print('Local files only; no tag, publication, installation or hardware access.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
