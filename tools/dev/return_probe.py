#!/usr/bin/env python3
"""Launch one shelf game, exit it and time the first accepted input after eject.

Run on the device next to esdev.py and profile_navigation.py, with ES showing the
target system's shelf. Take a session_data snapshot first: games write saves and
play statistics. Each accepted right tap moves the selection; the first selection
change after the frontend's own return notification identifies the earliest
accepted tap. Selections come from tools/dev/selection-hook.sh, which the theme
no longer installs; install it only while probing.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from esdev import api, press

SELECTED = Path('/tmp/art-book-slot-launch/selected')


def running_game():
    try:
        return 'NO GAME RUNNING' not in api('/runningGame')
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='substring of the ROM path to select')
    parser.add_argument('output', type=Path)
    parser.add_argument('--boot', type=float, default=14, help='seconds to let the game settle')
    parser.add_argument('--offsets', default='0,.25,.5,.75,1,1.25,1.5,1.75,2,2.5',
                        help='right taps, seconds after the eject render loop ends')
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--display', action='store_true')
    parser.add_argument('--probe-button', default='right',
                        help='a relaunches during the hold to test scene serialization')
    args = parser.parse_args()
    for step in range(150):
        # "." keeps the current selection; earlier probes move the cursor right.
        if args.target == '.' or args.target.lower() in (SELECTED.read_text().lower() if SELECTED.exists() else ''):
            break
        press(['right'])
    else:
        sys.exit('target not reached; nothing launched')
    rom = SELECTED.read_text().strip()
    time.sleep(1.5)
    press(['a'])
    deadline = time.time() + 30
    while not running_game():
        if time.time() > deadline:
            sys.exit('game did not start')
        time.sleep(.25)
    time.sleep(args.boot)
    command = [sys.executable, str(Path(__file__).with_name('profile_navigation.py')), str(args.output),
               '--seconds', str(args.seconds), '--event', '0.2:hotkey+start:100']
    for offset in args.offsets.split(','):
        command += ['--after-eject', offset]
    if args.display:
        command.append('--display')
    command += ['--probe-button', args.probe_button]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    trace = json.loads((args.output / 'trace.json').read_text())
    motion_end = next((item['t'] for item in trace['logs']
                       if item['message'].startswith('eject ') and 'frames in' in item['message']), None)
    returned = next((item['t'] for item in trace['selections'] if item['rom'] == rom), None)
    probes = [event for event in trace['events'] if event['kind'] == 'return-probe']
    moves = [item for item in trace['selections'] if returned is not None and item['t'] > returned]
    # Taps are lost only until the frontend reopens input, so the last N of them were
    # accepted. Taps queued before its first frame may merge into one notification,
    # which makes this estimate conservative.
    first = probes[len(probes) - len(moves)] if 0 < len(moves) <= len(probes) else None
    summary = {
        'rom': rom,
        'motion_end': motion_end,
        'frontend_return': returned,
        'return_after_motion': None if returned is None or motion_end is None else returned - motion_end,
        'probes_after_motion': [round(event['pressed'] - motion_end, 3) for event in probes] if motion_end else [],
        'accepted_moves': len(moves),
        'first_accepted_after_motion': None if first is None else round(first['pressed'] - motion_end, 3),
        'first_move_after_motion': round(moves[0]['t'] - motion_end, 3) if moves and motion_end else None,
        'helper': [item['message'] for item in trace['logs']
                   if item['message'].startswith(('return:', 'handover:', 'eject '))],
    }
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
