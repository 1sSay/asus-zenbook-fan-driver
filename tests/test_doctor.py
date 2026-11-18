# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Doctor uses fixture files and a fake systemctl, never hardware."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_clients import client


class Doctor(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name, executable in client.COMPONENTS:
            self.write(name, 'fixture')
            (self.root / name).chmod(0o755 if executable else 0o644)
        self.write('sys/class/dmi/id/product_name', client.SUPPORTED_MODELS[0] + '\n')
        self.write('proc/sys/kernel/random/boot_id', 'fixture-boot\n')
        (self.root / 'run/systemd/system').mkdir(parents=True)
        self.data = {'updated_at': 100, 'updated_monotonic': 50,
                     'boot_id': 'fixture-boot', 'fan_rpms': [0, 8694], 'error': None}
        self.publish()
        self.manager = subprocess.CompletedProcess([], 0,
            'LoadState=loaded\nActiveState=active\nSubState=running\nResult=success\n', '')

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def publish(self, **changes):
        self.write('run/asus-fan-rpm/status.json', json.dumps({**self.data, **changes}))

    def diagnose(self):
        with patch.object(client.socket, 'socket', side_effect=AssertionError('No sockets')), \
                patch.object(client.subprocess, 'Popen', side_effect=AssertionError('No worker')), \
                patch.object(client.subprocess, 'run', return_value=self.manager) as run:
            report = client.doctor(self.root, 'x86_64', now=101, monotonic=51)
            if run.called:
                self.assertEqual(run.call_args.args[0], [
                    'systemctl', '--system', 'show', 'asus-zenbook-fan-driver.service',
                    '--property=LoadState', '--property=ActiveState', '--property=SubState',
                    '--property=Result'])
                self.assertEqual(run.call_args.kwargs['timeout'], 5)
            return report

    def check(self, report, name):
        return next(c for c in report['checks'] if c['name'] == name)

    def test_healthy_and_exact_allowlist(self):
        for model in client.SUPPORTED_MODELS:
            self.write('sys/class/dmi/id/product_name', model + '\n')
            report = self.diagnose()
            self.assertEqual(report['exit_code'], 0)
            self.assertEqual(self.check(report, 'fan_readings')['detail']['Fan 1'], 0)
            self.assertEqual(self.check(report, 'recovery_error')['detail'], 'Not published')
            hardware = (Path(__file__).parents[1] / 'src/hardware.c').read_text()
            self.assertIn('"' + model + '"', hardware)

    def test_unsupported_model_and_architecture(self):
        for model in ('Other Zenbook', client.SUPPORTED_MODELS[0] + ' ', client.SUPPORTED_MODELS[0] + '\vother', ''):
            self.write('sys/class/dmi/id/product_name', model + '\n')
            report = self.diagnose()
            self.assertEqual(self.check(report, 'model')['state'], 'problem')
            self.assertEqual(report['exit_code'], 1)
        report = client.doctor(self.root, 'aarch64', run=lambda *a, **k: self.manager,
                               now=101, monotonic=51)
        self.assertEqual(self.check(report, 'architecture')['state'], 'problem')

    def test_dmi_unavailable_is_not_unsupported(self):
        (self.root / 'sys/class/dmi/id/product_name').unlink()
        report = self.diagnose()
        self.assertEqual(report['exit_code'], 2)
        self.assertEqual(self.check(report, 'model')['state'], 'unknown')
        original = Path.read_text
        def denied(path, *args, **kwargs):
            if path.name == 'product_name':
                raise PermissionError('denied')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', denied):
            self.assertEqual(self.diagnose()['exit_code'], 2)

    def test_missing_components(self):
        for name, _ in client.COMPONENTS:
            with self.subTest(name=name):
                path = self.root / name
                path.unlink()
                report = self.diagnose()
                self.assertEqual(report['exit_code'], 1)
                self.assertEqual(self.check(report, name)['detail'], 'Missing installed component')
                self.write(name, 'fixture')
                path.chmod(0o755)

    def test_stopped_failed_or_missing_unit_with_fresh_telemetry(self):
        for state in ('inactive', 'failed', 'activating'):
            self.manager.stdout = f'LoadState=loaded\nActiveState={state}\nSubState=dead\nResult=success\n'
            report = self.diagnose()
            self.assertEqual(report['exit_code'], 1)
            self.assertEqual(self.check(report, 'service')['state'], 'problem')
            self.assertEqual(self.check(report, 'telemetry')['state'], 'ok')
        self.manager.stdout = 'LoadState=not-found\nActiveState=inactive\n'
        self.assertEqual(self.diagnose()['exit_code'], 1)

    def test_systemd_unavailable_and_query_failure(self):
        for result in (subprocess.CompletedProcess([], 1, '', 'bus unavailable'),
                       subprocess.CompletedProcess([], 0, '', '')):
            self.manager = result
            self.assertEqual(self.diagnose()['exit_code'], 2)
        for exc in (FileNotFoundError('systemctl'), subprocess.TimeoutExpired('systemctl', 5)):
            with patch.object(client.subprocess, 'run', side_effect=exc):
                self.assertEqual(client.doctor(self.root, 'x86_64', now=101, monotonic=51)['exit_code'], 2)
        (self.root / 'run/systemd/system').rmdir()
        with patch.object(client.subprocess, 'run', side_effect=AssertionError('No manager')):
            report = client.doctor(self.root, 'x86_64', now=101, monotonic=51)
        self.assertEqual(report['exit_code'], 2)
        self.assertIn('No running systemd', self.check(report, 'service')['detail'])

    def test_missing_malformed_and_stale_telemetry(self):
        path = self.root / 'run/asus-fan-rpm/status.json'
        path.unlink()
        self.assertEqual(self.diagnose()['exit_code'], 1)
        for raw in ('broken', '[]', 'null', '{}'):
            path.write_text(raw)
            self.assertIn('invalid', self.check(self.diagnose(), 'telemetry')['detail'])
        for change in ({'updated_at': 89}, {'updated_at': 102}, {'updated_monotonic': 40},
                       {'boot_id': 'other'}, {'updated_at': float('nan')},
                       {'updated_at': True}, {'updated_at': 10**400},
                       {'fan_rpms': [False, 0]}, {'recovery_error': []}):
            self.publish(**change)
            self.assertEqual(self.diagnose()['exit_code'], 1)

    def test_public_errors_and_null_readings(self):
        for key in ('error', 'control_error', 'recovery_error'):
            self.publish(**{key: 'fixture failure'})
            report = self.diagnose()
            self.assertEqual(report['exit_code'], 1)
            self.assertEqual(self.check(report, key)['detail'], 'fixture failure')
        self.publish(fan_rpms=[None, None])
        self.assertEqual(self.diagnose()['exit_code'], 1)

    def test_permission_and_unknown_precedence(self):
        original = Path.read_text
        def denied(path, *args, **kwargs):
            if path.name == 'status.json':
                raise PermissionError('denied')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', denied):
            report = self.diagnose()
            self.assertEqual(report['exit_code'], 2)
            self.assertEqual(self.check(report, 'telemetry')['state'], 'unknown')
            (self.root / client.COMPONENTS[0][0]).unlink()
            self.assertEqual(self.diagnose()['exit_code'], 1)
        with patch.object(client.os, 'access', return_value=False):
            self.assertEqual(self.diagnose()['exit_code'], 1)

    def test_cli_json_text_and_help(self):
        report = self.diagnose()
        for args in (['doctor'], ['doctor', '--json']):
            output = io.StringIO()
            with patch('sys.argv', ['asus-zenbook-fan-driver', *args]), \
                    patch.object(client, 'doctor', return_value=report), contextlib.redirect_stdout(output):
                self.assertEqual(client.main(), 0)
            if '--json' in args:
                self.assertEqual(json.loads(output.getvalue()), report)
            else:
                self.assertIn('Fan 1', output.getvalue())
                self.assertIn('HealthyTable', output.getvalue())
        output = io.StringIO()
        with patch('sys.argv', ['asus-zenbook-fan-driver', '--help']), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                client.main()
        self.assertEqual(result.exception.code, 0)
        for word in ('doctor', '--json', 'Exit codes', 'no root'):
            self.assertIn(word, ' '.join(output.getvalue().split()))
