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
        raise ValueError('EC read failed')
    if any(type(x) is not int or not 0 <= x <= 20000 for x in values):
        raise ValueError('Invalid RPM')
    return values


CURVES = {
    'quiet': ((0, 80), (50, 100), (60, 120), (70, 140), (80, 153)),
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


def publish(values, error=None, control='auto', temperature=None, duty=None, path=RUNTIME / 'status.json'):
    data = {'updated_at': time.time(), 'fan_rpms': values, 'error': error,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'updated_monotonic': time.monotonic(),
            'control': {'mode': control, 'temperature_c': temperature, 'duty': duty,
                        'curve': curve_status(control)}}
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data) + '\n')
    tmp.chmod(0o644)
    os.replace(tmp, path)


def authorized(command, uid):
    return command in ('max', 'auto', 'quiet', 'performance') and uid == 0


class Driver:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.slots = threading.BoundedSemaphore(8)
        self.profile = 'auto'
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
                return json.loads(response)
            response.extend(c)
        raise ValueError('Oversized worker response')

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
                    publish([None, None], 'control operation', self.profile, duty=self.duty)
                    if command in CURVES:
                        temperature = cpu_temperature()
                        duty = curve_duty(command, temperature)
                        result = self.rpc(f'set-{duty}')
                        if result.get('ok'):
                            self.profile, self.duty = command, duty
                            self.duty_changed_at = time.monotonic()
                    else:
                        result = self.rpc(command)
                        if result.get('ok'):
                            self.profile, self.duty = 'auto', None
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
            now = time.monotonic()
            duty = next_duty(self.profile, temperature, self.duty,
                             self.duty_changed_at or now, now)
            if duty != self.duty:
                result = self.rpc(f'set-{duty}')
                if not result.get('ok'):
                    raise RuntimeError('Curve update failed')
                self.duty = duty
                self.duty_changed_at = now
        return validate(self.rpc('poll')), temperature

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
                            publish(values, control=self.profile, temperature=temperature, duty=self.duty)
                        except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
                            if self.profile in CURVES:
                                try:
                                    self.rpc('auto')
                                except (ValueError, OSError, RuntimeError, TimeoutError):
                                    pass
                                self.profile, self.duty = 'auto', None
                            publish([None, None], str(exc), self.profile)
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
            # Worker/supervisor restores only if a maximum test was entered.
            self.worker.wait(timeout=35)
            publish([None, None], 'service stopped', self.profile, duty=self.duty)
            server.close()
            address.unlink(missing_ok=True)


if __name__ == '__main__':
    Driver().serve()
