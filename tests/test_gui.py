# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
import subprocess
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from test_clients import load

gui = load('gui')


class Desktop(unittest.TestCase):
    def test_authorized_and_service_failure(self):
        for ok in (True, False):
            def run(argv, **kwargs):
                self.assertEqual(argv, ['/usr/bin/pkexec', '--disable-internal-agent', gui.HELPER, 'quiet'])
                self.assertEqual(kwargs['timeout'], 120)
                return SimpleNamespace(returncode=0 if ok else 1,
                                       stdout='{"ok":' + str(ok).lower() + ',"error":"EC busy"}', stderr='')
            self.assertEqual(gui.authorize('quiet', run)['ok'], ok)

    def test_denied_cancelled_missing_agent_and_service(self):
        for code, expected in ((126, 'cancelled'), (127, 'denied'), (1, 'service unavailable')):
            run = lambda *a, **kw: SimpleNamespace(returncode=code, stdout='', stderr='service unavailable')
            result = gui.authorize('restore-auto', run)
            self.assertFalse(result['ok'])
            self.assertIn(expected, result['error'])
        for exc in (FileNotFoundError('pkexec missing'), subprocess.TimeoutExpired('pkexec', 120)):
            def run(*a, **kw):
                raise exc
            self.assertFalse(gui.authorize('quiet', run)['ok'])

    def test_invalid_commands_never_authorize(self):
        def run(*a, **kw):
            self.fail('Invalid command reached pkexec')
        for command in ('test-max', 'max', 'set-255', 'quiet extra', ''):
            self.assertFalse(gui.authorize(command, run)['ok'])

    def test_zero_unavailable_and_errors(self):
        text = gui.describe({'fan_rpms': [0, None], 'recovery_error': 'unverified'})
        self.assertIn('Fan 1: 0 RPM', text)
        self.assertIn('Fan 2: unavailable', text)
        self.assertIn('Mode: unknown', text)
        self.assertIn('unverified', text)

    def test_policy_is_narrow_and_requires_fresh_admin_authentication(self):
        path = Path(__file__).parents[1] / 'polkit/org.asuszenbook.fan.control.policy'
        action = ET.parse(path).getroot().find('action')
        self.assertEqual(action.findtext('defaults/allow_active'), 'auth_admin')
        self.assertEqual(action.findtext('defaults/allow_inactive'), 'no')
        self.assertEqual(action.findtext('defaults/allow_any'), 'no')
        self.assertEqual([(a.attrib['key'], a.text) for a in action.findall('annotate')],
                         [('org.freedesktop.policykit.exec.path', gui.HELPER)])
