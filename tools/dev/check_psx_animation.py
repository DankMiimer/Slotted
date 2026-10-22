#!/usr/bin/env python3
"""Check full PS1 console visibility in a composed-LCD animation capture.

Usage: check_psx_animation.py CAPTURE_DIR ANIMATION_LOG --mode insert|eject
Needs capture_frames.py PNGs/timing.json and the matching native animation.log.
This checks the moving console, separately from the settled shelf return checks.
"""
import argparse
import json
from pathlib import Path
import re

from PIL import Image


def check(folder, log, mode):
    timing = json.loads((folder / 'timing.json').read_text())
    started, times = timing['started'], timing['frames']
    pattern = r'([\d.]+) \+[\d.]+ ' + mode + r' \d+ frames in ([\d.]+) s'
    motions = [(float(end) - float(duration), float(end))
               for end, duration in re.findall(pattern, log)]
    motions = [(start, end) for start, end in motions
               if started < start < end < started + times[-1]]
    if len(motions) != 1:
        raise ValueError('need exactly one complete matching motion in this capture')
    motion_start = motions[0][0]
    probes = (((178, 320), (180, 177, 181)),
              ((540, 320), (180, 177, 181)),
              ((360, 456), (133, 130, 135)))
    checked, failures, stages = [], [], set()
    for index, elapsed in enumerate(times):
        seat = (started + elapsed - motion_start) / (.95 if mode == 'insert' else .85)
        if mode == 'eject':
            seat = 1 - seat
        # The deck has reached its fixed pose, and the final fade has not begun.
        # Leave margins for LCD writeback latency and rounded native log times.
        if not .32 <= seat <= .80:
            continue
        with Image.open(folder / ('frame-%03d.png' % index)) as frame:
            if frame.size != (720, 480):
                raise ValueError('requires full-resolution 720x480 captures')
            pixels = [frame.convert('RGB').getpixel(point) for point, _ in probes]
        if any(max(abs(a - b) for a, b in zip(actual, expected)) > 12
               for actual, (_, expected) in zip(pixels, probes)):
            failures.append({'frame': index, 'seat': round(seat, 3), 'pixels': pixels})
        checked.append(index)
        stages.add('descent' if seat < .55 else 'seated' if seat < .70 else 'closure')
    if len(checked) < 5 or len(stages) != 3:
        raise ValueError('capture misses descent, seated disc or closing lid')
    return {'mode': mode, 'checked_frames': checked, 'missing_console': failures,
            'passed': not failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('log', type=Path)
    parser.add_argument('--mode', choices=('insert', 'eject'), required=True)
    options = parser.parse_args()
    try:
        report = check(options.capture, options.log.read_text(), options.mode)
    except (OSError, ValueError) as error:
        parser.exit(2, str(error) + '\n')
    (options.capture / 'animation-check.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
