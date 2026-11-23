# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Real service process/IPC with a fake worker, never EC or root."""
import json
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest


class ServiceProcess(unittest.TestCase):
    def test_publish_socket_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            fake = runtime / 'worker'
            fake.write_text('#!' + sys.executable + '\nimport sys,json\n'
                            'for line in sys.stdin:\n'
                            ' print(json.dumps({"ok":True,"fan_rpms":[0,4321]}),flush=True)\n')
            fake.chmod(0o755)
            service = Path(__file__).parents[1] / 'src/service.py'
            code = ('import runpy; from pathlib import Path; '
                    f'm=runpy.run_path({str(service)!r}); '
                    f'm["Driver"].__init__.__globals__["WORKER"]={str(fake)!r}; '
                    f'm["Driver"].__init__.__globals__["RUNTIME"]=Path({directory!r}); '
                    # publish() default path is bound at definition time.
                    'g=m["Driver"].__init__.__globals__; original=g["publish"]; '
                    f'g["publish"]=lambda values,error=None,control="auto",temperature=None,duty=None: original(values,error,control,temperature,duty,Path({directory!r})/"status.json"); '
                    'm["Driver"]().serve()')
            proc = subprocess.Popen([sys.executable, '-c', code], stderr=subprocess.PIPE)
            try:
                status = runtime / 'status.json'
                for _ in range(200):
                    if status.exists():
                        break
                    if proc.poll() is not None:
                        self.fail(proc.stderr.read().decode())
                    time.sleep(0.01)
                self.assertEqual(json.loads(status.read_text())['fan_rpms'], [0, 4321])
                self.assertEqual((runtime / 'control.sock').stat().st_mode & 0o777, 0o600)
                with socket.socket(socket.AF_UNIX) as conn:
                    conn.settimeout(2)
                    conn.connect(str(runtime / 'control.sock'))
                    conn.sendall(b'forbidden\n')
                    self.assertFalse(json.loads(conn.recv(4096))['ok'])
                proc.send_signal(signal.SIGTERM)
                self.assertEqual(proc.wait(timeout=3), 0)
                self.assertEqual(json.loads(status.read_text())['fan_rpms'], [None, None])
                self.assertFalse((runtime / 'control.sock').exists())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                proc.stderr.close()
