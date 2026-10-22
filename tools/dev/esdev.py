#!/usr/bin/env python3
"""Device-side helper for developing the Slot shelf theme on Knulli (Batocera EmulationStation).

Lives at /userdata/system/slot-dev/esdev.py on the handheld; dev.ps1 on the PC calls it over ssh.

  status                    ES pid, running game, ThemeSet
  stop | start | restart    EmulationStation via its init script (stop saves settings cleanly)
  wait [seconds]            block until the ES HTTP API answers
  get NAME                  read an es_settings.cfg value
  set NAME VALUE [TYPE]     write an es_settings.cfg value; ES must be stopped or it overwrites it
  backup | restore [session] snapshot once / restore; session preserves the current dev session
  press TOKEN...            controller input: a b x y l1 r1 l2 r2 select start hotkey
                            up down left right; NAME*N repeats, hold:NAME:MS, wait:MS
  shot PATH                 framebuffer screenshot (png)
"""
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

SETTINGS = '/userdata/system/configs/emulationstation/es_settings.cfg'
BACKUP = '/userdata/system/slot-dev/es_settings.cfg.orig'
SESSION_BACKUP = '/userdata/system/slot-dev/es_settings.cfg.session'
INIT = '/etc/init.d/S31emulationstation'
API = 'http://127.0.0.1:1234'
PAD_NAME = 'Anbernic RG34XX-SP Controller'

# ES button name -> evdev code, from the RG34XX-SP entry in /usr/share/emulationstation/es_input.cfg.
BUTTONS = {
    'a': 304, 'b': 305, 'y': 306, 'x': 307, 'l1': 308, 'r1': 309, 'select': 310,
    'start': 311, 'hotkey': 312, 'l3': 313, 'l2': 314, 'r2': 315, 'r3': 316,
}
# The d-pad is a hat: (axis, value).
HAT = {'up': (17, -1), 'down': (17, 1), 'left': (16, -1), 'right': (16, 1)}

TAP_MS = 60
GAP_MS = 140


def api(path, timeout=2):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def es_pid():
    out = subprocess.run(['pidof', 'emulationstation'], capture_output=True, text=True).stdout.split()
    return out[0] if out else None


def read_settings():
    with open(SETTINGS, encoding='utf-8') as f:
        return f.read()


def get(name):
    m = re.search(r'<\w+ name="%s" value="([^"]*)"' % re.escape(name), read_settings())
    return m.group(1) if m else None


def set_(name, value, kind=None):
    if es_pid():
        sys.exit('es is running; "esdev.py stop" first or it will overwrite the change')
    if kind is None:
        kind = 'bool' if value in ('true', 'false') else 'int' if re.fullmatch(r'-?\d+', value) else 'string'
    text = read_settings()
    pattern = r'<\w+ name="%s" value="[^"]*" />' % re.escape(name)
    line = '<%s name="%s" value="%s" />' % (kind, name, value)
    if re.search(pattern, text):
        text = re.sub(pattern, line, text)
    else:
        text = text.replace('</config>', '\t%s\n</config>' % line)
    with open(SETTINGS, 'w', encoding='utf-8') as f:
        f.write(text)


def backup(path=BACKUP):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print('backup already exists, keeping the original:', path)
        return
    shutil.copy2(SETTINGS, path)
    print('saved', path)


def restore(path=BACKUP):
    if es_pid():
        sys.exit('es is running; "esdev.py stop" first')
    shutil.copy2(path, SETTINGS)
    if path == SESSION_BACKUP:
        os.unlink(path)  # The next work block takes a fresh snapshot of the user's settings.
    print('restored', SETTINGS)


def stop():
    subprocess.run([INIT, 'stop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start():
    subprocess.Popen(['setsid', INIT, 'start'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def wait(seconds=60.0):
    end = time.time() + seconds
    while time.time() < end:
        try:
            api('/caps', timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    sys.exit('es did not answer within %ss' % seconds)


def pad():
    import evdev
    for path in evdev.list_devices():
        d = evdev.InputDevice(path)
        if d.name == PAD_NAME:
            return d
    sys.exit('controller not found')


def press(tokens):
    from evdev import ecodes as e
    d = pad()

    def down(name):
        if name in HAT:
            axis, value = HAT[name]
            d.write(e.EV_ABS, axis, value)
        else:
            d.write(e.EV_KEY, BUTTONS[name], 1)
        d.write(e.EV_SYN, e.SYN_REPORT, 0)

    def up(name):
        if name in HAT:
            d.write(e.EV_ABS, HAT[name][0], 0)
        else:
            d.write(e.EV_KEY, BUTTONS[name], 0)
        d.write(e.EV_SYN, e.SYN_REPORT, 0)

    for token in tokens:
        if token.startswith('wait:'):
            time.sleep(int(token[5:]) / 1000)
            continue
        if token.startswith('hold:'):
            _, name, ms = token.split(':')
            down(name)
            time.sleep(int(ms) / 1000)
            up(name)
            time.sleep(GAP_MS / 1000)
            continue
        name, _, times = token.partition('*')
        if name not in BUTTONS and name not in HAT:
            sys.exit('unknown input: ' + name)
        for _ in range(int(times or 1)):
            down(name)
            time.sleep(TAP_MS / 1000)
            up(name)
            time.sleep(GAP_MS / 1000)


def status():
    print('es pid:', es_pid())
    try:
        print('running game:', api('/runningGame'))
    except Exception as ex:
        print('api:', ex)
    print('ThemeSet:', get('ThemeSet'))


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == 'status':
        status()
    elif cmd == 'stop':
        stop()
    elif cmd == 'start':
        start()
    elif cmd == 'restart':
        stop()
        start()
    elif cmd == 'wait':
        wait(float(args[0]) if args else 60.0)
    elif cmd == 'get':
        print(get(args[0]))
    elif cmd == 'set':
        set_(*args)
    elif cmd == 'backup':
        if args not in ([], ['session']):
            sys.exit('Usage: esdev.py backup [session]')
        backup(SESSION_BACKUP if args == ['session'] else BACKUP)
    elif cmd == 'restore':
        if args not in ([], ['session']):
            sys.exit('Usage: esdev.py restore [session]')
        restore(SESSION_BACKUP if args == ['session'] else BACKUP)
    elif cmd == 'press':
        press(args)
    elif cmd == 'shot':
        subprocess.run(['knulli-screenshot', args[0]], check=True)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
