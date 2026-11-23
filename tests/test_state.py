# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Control/recovery transitions with fake RPC only; no hardware or root."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_clients import service, client


class State(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temp.name)
        self.runtime_patch = patch.object(service, 'RUNTIME', self.runtime)
        self.runtime_patch.start()
        self.process_patch = patch.object(service.subprocess, 'Popen')
        self.process_patch.start()
        self.driver = service.Driver()
        self.driver.rpc = lambda command: {'ok': True, 'auto_restored': True}

    def tearDown(self):
        self.process_patch.stop()
        self.runtime_patch.stop()
        self.temp.cleanup()

    def read(self):
        return client.status(self.runtime / 'status.json')

    def test_failed_recovery_survives_poll_and_restart(self):
        d = self.driver
        d.record_result('auto', {'ok': False, 'auto_restored': False, 'error': 'EC busy'})
        d.rpc = lambda _: {'ok': True, 'fan_rpms': [0, 4321], 'mode': 'auto'}
        values, temp = d.poll()
        d.snapshot(values, temperature=temp)
        data = self.read()
        self.assertEqual(data['fan_rpms'], [0, 4321])
        self.assertEqual(data['recovery_error'], 'EC busy')
        self.assertEqual(service.Driver().recovery_error, 'EC busy')
        d.record_result('auto', {'ok': True, 'auto_restored': True})
        d.snapshot(values)
        self.assertIsNone(self.read()['recovery_error'])
        self.assertTrue(self.read()['last_recovery']['ok'])

    def test_startup_lease_is_unknown_until_worker_confirms(self):
        (self.runtime / 'manual-lease').touch()
        d = service.Driver()
        self.assertEqual(d.mode, 'unknown')
        self.assertIsNotNone(d.recovery_error)
        d.rpc = lambda _: {'ok': True, 'fan_rpms': [0, 1], 'mode': 'auto'}
        d.poll()
        self.assertIsNotNone(d.recovery_error)
        (self.runtime / 'manual-lease').unlink()
        d.startup_lease = True
        d.poll()
        self.assertIsNone(d.recovery_error)
        self.assertTrue(d.last_recovery['ok'])

    def test_profiles_and_active_operation(self):
        d = self.driver
        def rpc(command):
            self.assertEqual(self.read()['active_operation'], 'balanced')
            self.assertEqual(command, 'set-153')
            return {'ok': True, 'auto_restored': False}
        d.rpc = rpc
        with patch.object(service, 'cpu_temperature', return_value=65):
            self.assertTrue(d.execute('balanced')['ok'])
        data = self.read()
        self.assertIsNone(data['active_operation'])
        self.assertEqual(data['control']['mode'], 'manual')
        self.assertEqual(data['control']['profile'], 'balanced')
        self.assertEqual(data['control']['duty'], 153)

    def test_sensor_failure_and_overheat_restore(self):
        for temp in (None, 95, 110):
            d = self.driver
            calls = []
            d.rpc = lambda command: calls.append(command) or {'ok': True, 'auto_restored': True}
            with patch.object(service, 'cpu_temperature',
                              side_effect=ValueError('sensor failed') if temp is None else None,
                              return_value=temp):
                self.assertFalse(d.execute('quiet')['ok'])
            self.assertEqual(calls, ['auto'])
            self.assertEqual(d.mode, 'auto')
            self.assertIsNotNone(self.read()['control_error'])
            self.assertIsNone(self.read()['recovery_error'])

    def test_failed_control_with_successful_restore(self):
        d = self.driver
        d.record_result('max', {'ok': False, 'auto_restored': True, 'error': 'interrupted'})
        self.assertEqual(d.mode, 'auto')
        self.assertEqual(d.control_error, 'interrupted')
        self.assertIsNone(d.recovery_error)
        d.rpc = lambda _: {'ok': True, 'fan_rpms': [0, 1]}
        d.poll()
        self.assertEqual(d.mode, 'unknown')
        self.assertEqual(d.control_error, 'interrupted')

    def test_bad_control_telemetry_rejected(self):
        for control in ([], {'mode': 'auto', 'curve': [None]}, {'mode': 'bad'}):
            service.publish([0, 1], path=self.runtime / 'status.json', state={'control': control})
            self.assertEqual(self.read()['fan_rpms'], [None, None])

    def test_previous_boot_errors_are_not_reused(self):
        service.publish([0, 1], path=self.runtime / 'status.json',
                        state={'boot_id': 'previous', 'recovery_error': 'old'})
        self.assertIsNone(service.Driver().recovery_error)

    def test_balanced_curve_and_authorization(self):
        self.assertTrue(service.authorized('balanced', 0))
        self.assertFalse(service.authorized('balanced', 1000))
        self.assertEqual(service.curve_duty('balanced', 45), 100)
        self.assertEqual(service.curve_duty('balanced', 85), 200)
