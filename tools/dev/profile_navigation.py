#!/usr/bin/env python3
"""Timestamp controlled navigation/return probes and framebuffer changes on device.

Record CRC samples without claiming renderer fps. --display sees Sunxi overlays.
All injected keys are released in finally; saved frames are encoded after sampling.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import struct
import time
import zlib

from PIL import Image, ImageDraw
from esdev import BUTTONS, HAT, pad


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--seconds', type=float, default=6)
    parser.add_argument('--period', type=float, default=1 / 60)
    parser.add_argument('--event', action='append', default=[], help='SECONDS:button+button:DURATION_MS')
    parser.add_argument('--after-eject', type=float, action='append',
                        help='right tap this many seconds after the motion log; repeat for a series')
    parser.add_argument('--display', action='store_true')
    parser.add_argument('--probe-button', default='right', choices=sorted(HAT) + sorted(BUTTONS))
    args = parser.parse_args()
    if not 0 < args.seconds <= 30 or args.period <= 0:
        parser.error('duration must be 0..30 seconds and period must be positive')
    scheduled = []
    for item in args.event:
        at, buttons, milliseconds = item.split(':')
        names = buttons.split('+')
        if any(name not in BUTTONS and name not in HAT for name in names):
            parser.error('unknown button')
        scheduled.append({'at': float(at), 'buttons': names, 'hold': float(milliseconds) / 1000,
                          'kind': 'scheduled', 'pressed': None, 'released': None})
    if args.after_eject and min(args.after_eject) < 0:
        parser.error('after-eject must be nonnegative')
    args.output.mkdir(parents=True, exist_ok=False)
    controller = pad()
    pressed = set()
    events, samples, frames, selections, log_events = [], [], [], [], []
    display = None
    if args.display:
        from sunxi_capture import DisplayCapture
        display = DisplayCapture()
    log = Path('/tmp/art-book-slot-launch/animation.log')
    log_offset = log.stat().st_size if log.exists() else 0
    selection = Path('/tmp/art-book-slot-launch/selected')
    selected_before = selection.read_text() if selection.exists() else ''
    last_selection = selection.stat().st_mtime_ns if selection.exists() else 0

    def inject(names, value):
        for name in names:
            if name in HAT:
                axis, sign = HAT[name]
                controller.write(3, axis, sign if value else 0)
            else:
                controller.write(1, BUTTONS[name], value)
            (pressed.add if value else pressed.discard)(name)
        controller.write(0, 0, 0)

    started = time.monotonic()
    next_sample, next_image = started, started
    probe_added = False
    try:
        while time.monotonic() - started < args.seconds:
            current = time.monotonic()
            elapsed = current - started
            if log.exists():
                with log.open() as stream:
                    stream.seek(log_offset)
                    fresh_lines = stream.readlines()
                    log_offset = stream.tell()
                for line in fresh_lines:
                    match = re.match(r'^([\d.]+) \+([\d.]+) (.*)', line)
                    if not match:
                        continue
                    timestamp, since_helper, message = match.groups()
                    log_events.append({'t': float(timestamp) - started,
                                       'helper_t': float(since_helper), 'message': message})
                    if args.after_eject and not probe_added and message.startswith('eject ') and 'frames in' in message:
                        for offset in args.after_eject:
                            scheduled.append({'at': float(timestamp) - started + offset,
                                              'buttons': [args.probe_button], 'hold': .06, 'kind': 'return-probe',
                                              'pressed': None, 'released': None})
                        probe_added = True
            for event in scheduled:
                if event['pressed'] is None and elapsed >= event['at']:
                    inject(event['buttons'], 1)
                    event['pressed'] = time.monotonic() - started
                    events.append(event)
                elif event['pressed'] is not None and event['released'] is None and elapsed >= event['pressed'] + event['hold']:
                    inject(event['buttons'], 0)
                    event['released'] = time.monotonic() - started
            if selection.exists():
                stamp = selection.stat().st_mtime_ns
                if stamp != last_selection:
                    selections.append({'t': time.monotonic() - started, 'rom': selection.read_text().strip()})
                    last_selection = stamp
            fd = os.open('/dev/fb0', os.O_RDONLY)
            try:
                var, fix = bytearray(160), bytearray(80)
                fcntl.ioctl(fd, 0x4600, var)
                fcntl.ioctl(fd, 0x4602, fix)
                width, height, _, _, xoffset, yoffset, bpp = struct.unpack_from('7I', var)
                stride = struct.unpack_from('I', fix, 48)[0]
                if (width, height, bpp) != (720, 480, 32):
                    raise RuntimeError('Expected a 720x480 32-bit framebuffer')
                pixels = display.read() if display else os.pread(fd, height * stride, yoffset * stride)
                captured = time.monotonic() - started
                if len(pixels) == height * stride:
                    samples.append({'t': captured, 'crc': zlib.crc32(pixels[80*stride:400*stride])})
                    if current >= next_image:
                        frames.append((captured, pixels))
                        next_image += .2
            finally:
                os.close(fd)
            next_sample += args.period
            time.sleep(max(0, next_sample - time.monotonic()))
    finally:
        inject(list(pressed), 0)
        controller.close()
        if display:
            display.close()
    result = {'started': started, 'display': args.display, 'selected_before': selected_before.strip(),
              'events': events, 'selections': selections, 'logs': log_events, 'samples': samples,
              'frames': [{'file':'frame-%03d.png'%index,'t':elapsed}
                         for index,(elapsed,_) in enumerate(frames)]}
    (args.output / 'trace.json').write_text(json.dumps(result, indent=2))
    sheet = Image.new('RGB', (360 * 4, 264 * ((len(frames) + 3) // 4)), '#17181a')
    drawing = ImageDraw.Draw(sheet)
    rawmode = 'BGRX' if struct.unpack_from('I', var, 32)[0] == 16 else 'RGBX'
    for index, (elapsed, pixels) in enumerate(frames):
        frame = Image.frombytes('RGB', (720, 480), pixels, 'raw', rawmode, stride)
        frame.save(args.output / ('frame-%03d.png' % index))
        x, y = index % 4 * 360, index // 4 * 264
        sheet.paste(frame.resize((360, 240)), (x, y))
        drawing.text((x + 6, y + 244), '%.3f s' % elapsed, fill='white')
    sheet.save(args.output / 'sheet.jpg')
    print(json.dumps({key: result[key] for key in ('events', 'selections', 'logs')}, indent=2))


if __name__ == '__main__':
    main()
