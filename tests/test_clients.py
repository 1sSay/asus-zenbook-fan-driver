# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / 'src' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client, service = load('client'), load('service')


class Telemetry(unittest.TestCase):
    def test_valid_zero_and_errors(self):
        self.assertEqual(service.validate({'ok': True, 'fan_rpms': [0, 8694]}), [0, 8694])
        for values in ([True, 1], [None, 0], [-1, 0], [20001, 0], [0], '00'):
            with self.assertRaises(ValueError):
                service.validate({'ok': True, 'fan_rpms': values})

    def test_age_boot_and_malformed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'status.json'
            service.publish([0, 8694], path=path)
            good = json.loads(path.read_text())
            self.assertEqual(client.status(path)['fan_rpms'], [0, 8694])
            for change in ({'updated_at': time.time() - 11}, {'updated_at': float('nan')},
                           {'updated_at': time.time() + 30}, {'boot_id': 'other'},
                           {'updated_monotonic': time.monotonic() - 11},
                           {'fan_rpms': [False, 0]}, {'fan_rpms': [1]}):
                path.write_text(json.dumps({**good, **change}))
                self.assertEqual(client.status(path)['fan_rpms'], [None, None])
            path.write_text('broken')
            self.assertEqual(client.status(path)['fan_rpms'], [None, None])
            path.unlink()
            self.assertEqual(client.status(path)['fan_rpms'], [None, None])

    def test_control_authorization(self):
        for uid in (1, 1000, 65534):
            for command in ('max', 'auto', 'poll', 'anything'):
                self.assertFalse(service.authorized(command, uid))
        self.assertTrue(service.authorized('max', 0))
        self.assertTrue(service.authorized('auto', 0))
        self.assertTrue(service.authorized('quiet', 0))
        self.assertTrue(service.authorized('performance', 0))
        self.assertFalse(service.authorized('arbitrary-pwm', 0))

    def test_profile_curves(self):
        self.assertEqual(service.curve_duty('quiet', 49), 80)
        self.assertEqual(service.curve_duty('quiet', 70), 140)
        self.assertEqual(service.curve_duty('quiet', 90), 153)
        self.assertEqual(service.curve_duty('performance', 54), 160)
        self.assertEqual(service.curve_duty('performance', 74), 200)
        self.assertEqual(service.curve_duty('performance', 85), 217)
        self.assertEqual(service.curve_status('quiet')[-1], {'from_c': 80, 'duty': 153})
        with self.assertRaises(ValueError):
            service.curve_duty('quiet', 0)
