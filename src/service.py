#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Single serialized hardware worker, public telemetry, root-only control IPC."""
import json
import os
from pathlib import Path
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


def publish(values, error=None, path=RUNTIME / 'status.json'):
    data = {'updated_at': time.time(), 'fan_rpms': values, 'error': error,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'updated_monotonic': time.monotonic()}
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data) + '\n')
    tmp.chmod(0o644)
    os.replace(tmp, path)


def authorized(command, uid):
    return command in ('max', 'auto') and uid == 0


class Driver:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.slots = threading.BoundedSemaphore(8)
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
                    publish([None, None], 'control operation')
                    result = self.rpc(command)
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
                            publish(validate(self.rpc('poll')))
                        except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
                            publish([None, None], str(exc))
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
            publish([None, None], 'service stopped')
            server.close()
            address.unlink(missing_ok=True)


if __name__ == '__main__':
    Driver().serve()
