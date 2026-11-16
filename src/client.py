#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Unprivileged telemetry client; root-only bounded control requests."""
import argparse
import json
import math
from pathlib import Path
import socket
import time

STATUS = Path('/run/asus-fan-rpm/status.json')


def status(path=STATUS, now=None, monotonic=None):
    try:
        data = json.loads(path.read_text())
        age = (time.time() if now is None else now) - data['updated_at']
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        mono_age = (time.monotonic() if monotonic is None else monotonic) - data['updated_monotonic']
        values = data['fan_rpms']
        if (data['boot_id'] != boot or not math.isfinite(age) or not 0 <= age <= 10
                or not math.isfinite(mono_age) or not 0 <= mono_age <= 10):
            raise ValueError('Stale telemetry')
        if not isinstance(values, list) or len(values) != 2 or any(
                v is not None and (type(v) is not int or not 0 <= v <= 20000) for v in values):
            raise ValueError('Invalid telemetry')
        return data
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'fan_rpms': [None, None], 'error': str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'watch', 'test-max', 'restore-auto'])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.command in ('test-max', 'restore-auto'):
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(40)
            connection.connect('/run/asus-fan-rpm/control.sock')
            connection.sendall(b'max\n' if args.command == 'test-max' else b'auto\n')
            response = connection.makefile('r').readline(8192)
            result = json.loads(response)
        print(json.dumps(result))
        return 0 if result.get('ok') else 1
    while True:
        data = status()
        if args.json:
            print(json.dumps(data), flush=True)
        else:
            print(' / '.join(f'Fan {i+1}: {v} RPM' if v is not None else f'Fan {i+1}: unavailable'
                             for i, v in enumerate(data['fan_rpms'])), flush=True)
            if data.get('error'):
                print('Error: ' + str(data['error']), flush=True)
        if args.command != 'watch':
            return 1 if data.get('error') else 0
        time.sleep(3)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
