#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 1sSay
"""Standalone unprivileged desktop client for public telemetry and polkit control."""
import json
import os
import runpy
import subprocess
import threading

HELPER = '/usr/lib/asus-zenbook-fan-driver/control-helper'
CLIENT = '/usr/lib/asus-zenbook-fan-driver/client.py'
COMMANDS = ('quiet', 'balanced', 'performance', 'restore-auto')


def authorize(command, run=subprocess.run):
    if command not in COMMANDS:
        return {'ok': False, 'error': 'Invalid desktop control command'}
    try:
        result = run(['/usr/bin/pkexec', '--disable-internal-agent', HELPER, command],
                     capture_output=True, text=True, timeout=120)
        if result.returncode == 126:
            return {'ok': False, 'error': 'Authorization cancelled; no cooling command sent'}
        if result.returncode == 127:
            return {'ok': False, 'error': 'Authorization denied or unavailable; check the desktop polkit agent'}
        if result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict) and type(data.get('ok')) is bool:
                return data
        return {'ok': False, 'error': result.stderr.strip() or 'Control service unavailable'}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'error': str(exc)}


def describe(data):
    rpms = data['fan_rpms']
    lines = [f'Fan {i + 1}: {rpm} RPM' if rpm is not None else f'Fan {i + 1}: unavailable'
             for i, rpm in enumerate(rpms)]
    control = data.get('control') or {}
    lines += ['Mode: ' + str(control.get('mode', 'unknown')),
              'Profile: ' + str(control.get('profile') or 'none')]
    for key in ('error', 'control_error', 'recovery_error'):
        if data.get(key):
            lines.append(key.replace('_', ' ').capitalize() + ': ' + str(data[key]))
    if data.get('active_operation'):
        lines.append('Operation: ' + str(data['active_operation']))
    return '\n'.join(lines)


def main():
    if os.geteuid() == 0:
        raise SystemExit('Run the desktop client as your ordinary desktop user')
    import tkinter as tk
    from tkinter import ttk
    status = runpy.run_path(CLIENT)['status']
    root = tk.Tk()
    root.title('ASUS Zenbook fans')
    root.geometry('540x330')
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill='both', expand=True)
    telemetry = tk.StringVar()
    message = tk.StringVar(value='Profile changes require administrator authentication.')
    ttk.Label(frame, textvariable=telemetry, wraplength=500, justify='left').pack(anchor='w')
    buttons = []
    pending = []
    busy = False

    def control(command):
        nonlocal busy
        busy = True
        for button in buttons:
            button.configure(state='disabled')
        message.set('Waiting for authorization and service response…')
        # All Tk operations stay on the main thread. Closing the window never
        # cancels a control operation already accepted by the service.
        threading.Thread(target=lambda: pending.append(authorize(command)), daemon=True).start()

    for command in COMMANDS:
        button = ttk.Button(frame, text=command.replace('-', ' ').capitalize(),
                            command=lambda command=command: control(command))
        button.pack(side='top', anchor='w', pady=2)
        buttons.append(button)
    ttk.Label(frame, textvariable=message, wraplength=500).pack(anchor='w', pady=8)

    def refresh():
        nonlocal busy
        telemetry.set(describe(status()))
        if busy and pending:
            result = pending.pop()
            message.set('Command completed.' if result.get('ok') else 'Error: ' + str(result.get('error')))
            busy = False
            for button in buttons:
                button.configure(state='normal')
        root.after(1000, refresh)
    refresh()
    root.mainloop()


if __name__ == '__main__':
    main()
