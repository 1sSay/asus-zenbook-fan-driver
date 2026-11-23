#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Unprivileged telemetry client; root-only bounded control requests."""
import argparse
import json
import math
import os
import platform
from pathlib import Path
import socket
import subprocess
import time

STATUS = Path('/run/asus-fan-rpm/status.json')


class TelemetryError(ValueError):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def read_telemetry(path=STATUS, now=None, monotonic=None,
                   boot_path=Path('/proc/sys/kernel/random/boot_id')):
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise TelemetryError('invalid', 'Telemetry must be a JSON object')
    try:
        for key in ('updated_at', 'updated_monotonic'):
            if type(data[key]) not in (int, float) or not math.isfinite(data[key]):
                raise ValueError('Invalid timestamp')
        values = data['fan_rpms']
        if not isinstance(values, list) or len(values) != 2 or any(
                v is not None and (type(v) is not int or not 0 <= v <= 20000) for v in values):
            raise ValueError('Invalid fan readings')
        if not isinstance(data['boot_id'], str) or not data['boot_id']:
            raise ValueError('Invalid boot ID')
        for key in ('error', 'control_error', 'recovery_error'):
            if data.get(key) is not None and not isinstance(data[key], str):
                raise ValueError('Invalid ' + key)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise TelemetryError('invalid', 'Invalid telemetry: ' + str(exc)) from exc
    control = data.get('control')
    if control is not None:
        if not isinstance(control, dict) or control.get('mode') not in (
                'auto', 'manual', 'unknown', 'quiet', 'balanced', 'performance'):
            raise TelemetryError('invalid', 'Invalid control state')
        curve = control.get('curve', [])
        if not isinstance(curve, list) or any(
                not isinstance(point, dict) or type(point.get('from_c')) not in (int, float)
                or not math.isfinite(point['from_c']) or type(point.get('duty')) is not int
                or not 0 <= point['duty'] <= 255 for point in curve):
            raise TelemetryError('invalid', 'Invalid control curve')
    age = (time.time() if now is None else now) - data['updated_at']
    mono_age = (time.monotonic() if monotonic is None else monotonic) - data['updated_monotonic']
    if (data['boot_id'] != boot_path.read_text().strip()
            or not 0 <= age <= 10 or not 0 <= mono_age <= 10):
        raise TelemetryError('stale', 'Stale telemetry (age, future timestamp or different boot)')
    return data


def status(path=STATUS, now=None, monotonic=None):
    try:
        return read_telemetry(path, now, monotonic)
    except (OSError, ValueError, TypeError) as exc:
        return {'fan_rpms': [None, None], 'error': str(exc)}


SUPPORTED_MODELS = ('Zenbook UX425QA_UM425QA', 'ZenBook UX425QA_UM425QA')
COMPONENTS = (
    ('usr/bin/asus-zenbook-fan-driver', True),
    ('usr/lib/asus-zenbook-fan-driver/service.py', True),
    ('usr/lib/asus-zenbook-fan-driver/ec-worker', True),
    ('usr/lib/systemd/system/asus-zenbook-fan-driver.service', False),
    ('usr/lib/systemd/system-sleep/asus-zenbook-fan-driver', True),
)
DOCTOR_LIMITS = (
    'Read-only checks; no service start, control socket or raw EC access.',
    'DMI match does not verify HealthyTable 8 or the physical fan count.',
    'Competing EC programs are not detected; the shared lock cannot cover unrelated tools.',
    'Only currently published errors are visible; absent control/recovery fields do not prove recovery.',
)


def doctor(root=Path('/'), machine=None, run=None, now=None, monotonic=None):
    """Inspect public files and systemd only; root/run/clocks allow hardware-free tests."""
    checks = []

    def add(name, state, detail):
        checks.append({'name': name, 'state': state, 'detail': detail})

    arch = platform.machine() if machine is None else machine
    add('architecture', 'ok' if arch == 'x86_64' else 'problem', arch)
    try:
        # Match the worker's exact first-line comparison, without trimming spaces.
        model = (root / 'sys/class/dmi/id/product_name').read_text().split('\n', 1)[0].split('\r', 1)[0]
        add('model', 'ok' if model in SUPPORTED_MODELS else 'problem', model)
    except (OSError, UnicodeError) as exc:
        add('model', 'unknown', 'DMI unavailable: ' + str(exc))

    for name, executable in COMPONENTS:
        path = root / name
        try:
            path.stat()
            if not path.is_file():
                add(name, 'problem', 'Not a regular file')
            elif not os.access(path, os.R_OK | (os.X_OK if executable else 0)):
                add(name, 'problem', 'Required read/execute permission unavailable')
            else:
                add(name, 'ok', 'Installed')
        except FileNotFoundError:
            add(name, 'problem', 'Missing installed component')
        except OSError as exc:
            add(name, 'unknown', str(exc))

    if not (root / 'run/systemd/system').is_dir():
        add('service', 'unknown', 'No running systemd manager detected')
    else:
        try:
            result = (subprocess.run if run is None else run)(
                ['systemctl', '--system', 'show', 'asus-zenbook-fan-driver.service',
                 '--property=LoadState', '--property=ActiveState', '--property=SubState',
                 '--property=Result'], capture_output=True, text=True, timeout=5,
                env={**os.environ, 'LC_ALL': 'C'})
            if result.returncode:
                add('service', 'unknown', 'systemctl query failed: ' + result.stderr.strip())
            else:
                properties = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
                service_state = properties.get('ActiveState')
                if properties.get('LoadState') and properties['LoadState'] != 'loaded':
                    add('service', 'problem', properties)
                elif not all(properties.get(key) for key in ('LoadState', 'ActiveState', 'SubState', 'Result')):
                    add('service', 'unknown', 'Incomplete systemctl response')
                else:
                    healthy = (properties['LoadState'] == 'loaded' and service_state == 'active'
                               and properties.get('SubState') == 'running'
                               and properties.get('Result') == 'success')
                    add('service', 'ok' if healthy else 'problem', properties)
        except (OSError, subprocess.TimeoutExpired) as exc:
            add('service', 'unknown', 'systemctl unavailable: ' + str(exc))

    telemetry_path = root / 'run/asus-fan-rpm/status.json'
    try:
        data = read_telemetry(telemetry_path, now, monotonic,
                              root / 'proc/sys/kernel/random/boot_id')
        add('telemetry', 'ok', 'Valid and fresh (at most 10 seconds, same boot)')
        add('fan_readings', 'problem' if None in data['fan_rpms'] else 'ok',
            dict(zip(('Fan 1', 'Fan 2'), data['fan_rpms'])))
        for key in ('error', 'control_error', 'recovery_error'):
            add(key, 'problem' if data.get(key) else 'ok' if key in data else 'info',
                data.get(key) or ('No current error reported' if key in data else 'Not published'))
    except FileNotFoundError as exc:
        add('telemetry', 'problem', 'Required telemetry/boot file missing: ' + str(exc))
    except TelemetryError as exc:
        add('telemetry', 'problem', exc.kind + ': ' + str(exc))
    except (ValueError, UnicodeError) as exc:
        add('telemetry', 'problem', 'invalid: ' + str(exc))
    except OSError as exc:
        add('telemetry', 'unknown', 'Telemetry inaccessible: ' + str(exc))
    code = 1 if any(c['state'] == 'problem' for c in checks) else (
        2 if any(c['state'] == 'unknown' for c in checks) else 0)
    return {'schema_version': 1, 'exit_code': code, 'checks': checks,
            'limits': list(DOCTOR_LIMITS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        'doctor: read-only installation, model, service and telemetry diagnostics; no root needed. '
        'Exit codes: 0 checks passed, 1 problem found, 2 inconclusive (also argument errors). '
        'A detected problem takes precedence over inconclusive checks.'))
    parser.add_argument('command', choices=['status', 'watch', 'doctor', 'quiet', 'balanced', 'performance', 'test-max', 'restore-auto'])
    parser.add_argument('--json', action='store_true', help='print machine-readable JSON')
    args = parser.parse_args()
    if args.command == 'doctor':
        report = doctor()
        if args.json:
            print(json.dumps(report))
        else:
            print('Doctor: ' + {0: 'checks passed', 1: 'problems found', 2: 'inconclusive'}[report['exit_code']])
            for check in report['checks']:
                print(f"[{check['state'].upper()}] {check['name']}: {check['detail']}")
            for limit in report['limits']:
                print('Note: ' + limit)
        return report['exit_code']
    if args.command in ('quiet', 'balanced', 'performance', 'test-max', 'restore-auto'):
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(40)
            connection.connect('/run/asus-fan-rpm/control.sock')
            command = {'test-max': 'max', 'restore-auto': 'auto'}.get(args.command, args.command)
            connection.sendall((command + '\n').encode())
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
            for key in ('control_error', 'recovery_error'):
                if data.get(key):
                    print(key.replace('_', ' ').capitalize() + ': ' + data[key], flush=True)
            if not data.get('error'):
                print('Mode: ' + str((data.get('control') or {}).get('mode', 'unknown')), flush=True)
                print('Profile: ' + str((data.get('control') or {}).get('profile') or 'none'), flush=True)
                curve = (data.get('control') or {}).get('curve', [])
                if curve:
                    print('Curve: ' + ', '.join(f">={item['from_c']}°C: {item['duty']}/255"
                                               for item in curve), flush=True)
        if args.command != 'watch':
            return 1 if any(data.get(key) for key in ('error', 'control_error', 'recovery_error')) else 0
        time.sleep(3)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc))
