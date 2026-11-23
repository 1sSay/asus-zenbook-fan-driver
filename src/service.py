#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Single serialized hardware worker, public telemetry, root-only control IPC."""
import json
import os
from pathlib import Path
import glob
import select
import signal
import socket
import struct
import subprocess
import threading
import time

RUNTIME = Path('/run/asus-fan-rpm')
WORKER = '/usr/lib/asus-zenbook-fan-driver/ec-worker'


def validate(data):
    values = data.get('fan_rpms')
    if not data.get('ok') or not isinstance(values, list) or len(values) != 2:
        raise ValueError(data.get('error') or 'EC read failed')
    if any(type(x) is not int or not 0 <= x <= 20000 for x in values):
        raise ValueError('Invalid RPM')
    return values


CURVES = {
    'quiet': ((0, 80), (50, 100), (60, 120), (70, 140), (80, 153)),
    'balanced': ((0, 100), (50, 120), (60, 153), (70, 180), (80, 200)),
    'performance': ((0, 140), (45, 160), (55, 180), (65, 200), (75, 217)),
}
HYSTERESIS_C = 3
MINIMUM_DUTY_CHANGE_SECONDS = 15


def cpu_temperature():
    for name in glob.glob('/sys/class/hwmon/hwmon*/name'):
        try:
            if Path(name).read_text().strip() != 'k10temp':
                continue
            value = int((Path(name).parent / 'temp1_input').read_text().strip())
            if 0 < value < 125000:
                return value / 1000
        except (OSError, ValueError):
            continue
    raise ValueError('AMD k10temp CPU sensor unavailable')


def curve_duty(profile, temperature):
    if profile not in CURVES or not 0 < temperature < 125:
        raise ValueError('Invalid profile or CPU temperature')
    duty = CURVES[profile][0][1]
    for threshold, candidate in CURVES[profile]:
        if temperature < threshold:
            break
        duty = candidate
    return duty


def next_duty(profile, temperature, current_duty, changed_at, now):
    """Return the next safe curve point without chattering around a threshold."""
    target = curve_duty(profile, temperature)
    points = CURVES[profile]
    duties = [duty for _, duty in points]
    if current_duty not in duties:
        return target
    current = duties.index(current_duty)
    target_index = duties.index(target)
    if target_index >= current:
        # Do not delay extra cooling when the CPU heats up.
        return target
    threshold = points[current][0]
    if (now - changed_at >= MINIMUM_DUTY_CHANGE_SECONDS and
            temperature < threshold - HYSTERESIS_C):
        # Decay one fixed curve point at a time, never directly from a hot
        # point to idle. This keeps fan speed changes gradual.
        return duties[current - 1]
    return current_duty


def curve_status(profile):
    if profile not in CURVES:
        return []
    return [{'from_c': threshold, 'duty': duty} for threshold, duty in CURVES[profile]]


def publish(values, error=None, control='unknown', temperature=None, duty=None, path=None, state=None):
    path = RUNTIME / 'status.json' if path is None else path
    data = {'updated_at': time.time(), 'fan_rpms': values, 'error': error,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'updated_monotonic': time.monotonic(),
            'control': {'mode': control, 'temperature_c': temperature, 'duty': duty,
                        'curve': curve_status(control)}}
    data['schema_version'] = 1
    if state is not None:
        data.update(state)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data) + '\n')
    tmp.chmod(0o644)
    os.replace(tmp, path)


def authorized(command, uid):
    return command in ('max', 'auto', 'quiet', 'balanced', 'performance') and uid == 0


class Driver:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.slots = threading.BoundedSemaphore(8)
        self.profile = 'unknown'
        self.mode = 'unknown'
        self.active_operation = None
        self.last_control = None
        self.last_recovery = None
        self.control_error = None
        self.recovery_error = ('Outstanding manual lease; recovery unverified'
                               if (RUNTIME / 'manual-lease').exists() else None)
        self.startup_lease = (RUNTIME / 'manual-lease').exists()
        try:
            previous = json.loads((RUNTIME / 'status.json').read_text())
            boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            if isinstance(previous, dict) and previous.get('boot_id') == boot:
                for field in ('control_error', 'recovery_error', 'last_control', 'last_recovery'):
                    value = previous.get(field)
                    expected = str if field.endswith('error') else dict
                    if value is None or isinstance(value, expected):
                        setattr(self, field, value)
        except (OSError, ValueError):
            pass
        if self.startup_lease:
            self.recovery_error = 'Outstanding manual lease; recovery unverified'
        self.duty = None
        self.duty_changed_at = None
        self.worker = subprocess.Popen([WORKER, '--service-worker'], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, bufsize=0)

    def rpc(self, command):
        # Caller holds lock; exactly one process talks to the EC at a time.
        self.worker.stdin.write((command + '\n').encode())
        deadline = time.monotonic() + (35 if command == 'max' else 8)
        response = bytearray()
        while len(response) < 4096:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.worker.stdout], [], [], remaining)[0]:
                self.shutdown()
                raise TimeoutError('Hardware worker deadline exceeded')
            c = self.worker.stdout.read(1)
            if not c:
                raise RuntimeError('Hardware worker exited')
            if c == b'\n':
                result = json.loads(response)
                if not isinstance(result, dict) or type(result.get('ok')) is not bool:
                    self.shutdown()
                    raise ValueError('Invalid worker response')
                return result
            response.extend(c)
        self.shutdown()
        raise ValueError('Oversized worker response')

    def snapshot(self, values, error=None, temperature=None):
        publish(values, error, self.mode, temperature, self.duty, state={
            'control': {'mode': self.mode, 'profile': self.profile if self.profile in CURVES else None,
                        'temperature_c': temperature, 'duty': self.duty,
                        'curve': curve_status(self.profile)},
            'active_operation': self.active_operation, 'last_control': self.last_control,
            'last_recovery': self.last_recovery, 'control_error': self.control_error,
            'recovery_error': self.recovery_error})

    def record_result(self, command, result):
        ok = result.get('ok') is True
        self.last_control = {'command': command, 'ok': ok, 'updated_at': time.time(),
                             'error': None if ok else result.get('error') or 'Control failed'}
        self.control_error = self.last_control['error']
        if result.get('auto_restored') is True:
            self.mode, self.profile, self.duty = 'auto', 'auto', None
            self.recovery_error = None
            self.last_recovery = {'ok': True, 'updated_at': time.time(), 'error': None}
        elif command in CURVES and ok:
            self.mode = 'manual'
        else:
            self.mode, self.profile, self.duty = 'unknown', 'unknown', None
            self.recovery_error = result.get('error') or 'Automatic cooling could not be verified'
            self.last_recovery = {'ok': False, 'updated_at': time.time(),
                                  'error': self.recovery_error}

    def execute(self, command):
        # Caller holds the hardware lock. Errors survive subsequent RPM polls.
        self.active_operation = command
        self.snapshot([None, None], 'control operation')
        try:
            if command in CURVES:
                temperature = cpu_temperature()
                if temperature >= 95:
                    raise ValueError('CPU temperature at or above 95 C; use firmware cooling')
                duty = curve_duty(command, temperature)
                result = self.rpc(f'set-{duty}')
                self.record_result(command, result)
                if result.get('ok'):
                    self.profile, self.duty = command, duty
                    self.duty_changed_at = time.monotonic()
            else:
                if command == 'max' and self.profile in CURVES:
                    recovery = self.rpc('auto')
                    self.record_result('auto', recovery)
                    if recovery.get('auto_restored') is not True:
                        raise RuntimeError(recovery.get('error') or 'Restore before maximum test failed')
                result = self.rpc(command)
                self.record_result(command, result)
            return result
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            result = {'ok': False, 'error': str(exc)}
            self.record_result(command, result)
            # A failed sensor lookup may leave an earlier profile active.
            # Never reuse a pipe after a deadline (rpc already stops the worker).
            if not self.stop.is_set():
                try:
                    self.record_result('auto', self.rpc('auto'))
                except (OSError, ValueError, RuntimeError, TimeoutError):
                    pass
                self.control_error = str(exc)
                self.last_control = {'command': command, 'ok': False,
                                     'updated_at': time.time(), 'error': str(exc)}
            return result
        finally:
            self.active_operation = None
            self.snapshot([None, None])

    def request(self, connection):
        try:
            connection.settimeout(1)
            uid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
            command = connection.recv(32).decode('ascii').strip()
            if not authorized(command, uid):
                result = {'ok': False, 'error': 'Control requires root; use status.json for telemetry'}
            else:
                if command == 'auto':
                    self.worker.send_signal(signal.SIGUSR1)
                with self.lock:
                    if self.stop.is_set():
                        raise RuntimeError('Service stopping')
                    result = self.execute(command)
            connection.sendall(json.dumps(result).encode() + b'\n')
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            try:
                connection.sendall(json.dumps({'ok': False, 'error': str(exc)}).encode() + b'\n')
            except OSError:
                pass
        finally:
            connection.close()
            self.slots.release()

    def shutdown(self, *_):
        self.stop.set()
        if self.worker.poll() is None:
            self.worker.terminate()

    def poll(self):
        temperature = None
        if self.profile in CURVES:
            temperature = cpu_temperature()
            if temperature >= 95:
                raise ValueError('CPU temperature at or above 95 C; returning to firmware cooling')
            now = time.monotonic()
            duty = next_duty(self.profile, temperature, self.duty,
                             self.duty_changed_at or now, now)
            if duty != self.duty:
                result = self.rpc(f'set-{duty}')
                if not result.get('ok'):
                    self.record_result(self.profile, result)
                    raise RuntimeError(result.get('error') or 'Curve update failed')
                self.duty = duty
                self.duty_changed_at = now
        result = self.rpc('poll')
        self.mode = 'unknown'
        values = validate(result)
        self.mode = result.get('mode') if result.get('mode') in ('auto', 'manual') else 'unknown'
        if self.mode == 'auto':
            self.profile, self.duty = 'auto', None
            if self.startup_lease and not (RUNTIME / 'manual-lease').exists():
                self.recovery_error = None
                self.last_recovery = {'ok': True, 'updated_at': time.time(), 'error': None}
            self.startup_lease = False
            # Other recovery errors require an explicit verified restoration.
        elif self.mode != 'manual' and self.profile in CURVES:
            raise RuntimeError('Manual mode could not be verified')
        return values, temperature

    def serve(self):
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGHUP, self.shutdown)
        server = socket.socket(socket.AF_UNIX)
        address = RUNTIME / 'control.sock'
        address.unlink(missing_ok=True)
        server.bind(str(address))
        address.chmod(0o600)
        server.listen(8)
        server.settimeout(0.2)
        next_poll = 0
        try:
            while not self.stop.is_set():
                if self.worker.poll() is not None:
                    raise RuntimeError('Hardware worker exited')
                if time.monotonic() >= next_poll and self.lock.acquire(blocking=False):
                    try:
                        try:
                            values, temperature = self.poll()
                            self.snapshot(values, temperature=temperature)
                        except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
                            if self.profile in CURVES:
                                self.record_result(self.profile, {'ok': False, 'error': str(exc)})
                                if not self.stop.is_set():
                                    try:
                                        self.record_result('auto', self.rpc('auto'))
                                    except (ValueError, OSError, RuntimeError, TimeoutError) as recovery:
                                        self.record_result('auto', {'ok': False, 'error': str(recovery)})
                                self.control_error = str(exc)
                            else:
                                self.mode = 'unknown'
                            self.snapshot([None, None], str(exc))
                            # A timed-out pipe is no longer synchronized. Fail closed.
                            if isinstance(exc, TimeoutError):
                                raise
                    finally:
                        self.lock.release()
                    next_poll = time.monotonic() + 3
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                if self.slots.acquire(blocking=False):
                    threading.Thread(target=self.request, args=(conn,), daemon=True).start()
                else:
                    conn.close()
        finally:
            self.shutdown()
            # Worker restores any outstanding manual lease, including profiles.
            self.worker.wait(timeout=35)
            with self.lock:
                self.mode, self.profile, self.duty = 'unknown', 'unknown', None
                self.active_operation = None
                if (RUNTIME / 'manual-lease').exists():
                    self.recovery_error = 'Outstanding manual lease after service stop'
                self.snapshot([None, None], 'service stopped')
            server.close()
            address.unlink(missing_ok=True)


if __name__ == '__main__':
    Driver().serve()
