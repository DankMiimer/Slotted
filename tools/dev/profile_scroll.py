#!/usr/bin/env python3
"""Sample the visible framebuffer at 60 Hz during held carousel input.

Run on the device beside esdev.py. PNG compression happens after input is released,
so the ordinary screenshot utility's slow PNG writes do not distort the measurement.
This measures framebuffer changes, not the renderer's internal frame rate.
"""
import argparse
import fcntl
import json
import mmap
from pathlib import Path
import struct
import time
import zlib

from PIL import Image, ImageDraw
from evdev import ecodes

import esdev


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--hold-ms', type=int, default=3000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stride = int(Path('/sys/class/graphics/fb0/stride').read_text())
    controller = esdev.pad()
    samples, frames = [], []
    hold_start, hold_end = 0.3, 0.3 + args.hold_ms / 1000
    pressed, released = False, False

    def input_value(value):
        controller.write(ecodes.EV_ABS, 16, value)
        controller.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)

    with open('/dev/fb0', 'r+b', buffering=0) as framebuffer:
        info = bytearray(160)
        fcntl.ioctl(framebuffer, 0x4600, info)
        width, height, _, virtual_height, _, _, bpp = struct.unpack_from('7I', info)
        if bpp != 32:
            raise SystemExit('This profiler requires a 32-bit framebuffer')
        red, green, blue = (struct.unpack_from('I', info, offset)[0] for offset in (32, 44, 56))
        rawmode = 'BGRX' if (red, green, blue) == (16, 8, 0) else 'RGBX'
        mapped = mmap.mmap(framebuffer.fileno(), stride * virtual_height)
        started = time.monotonic()
        next_sample, next_frame = started, 0.0
        try:
            while True:
                now = time.monotonic()
                elapsed = now - started
                if elapsed >= hold_start and not pressed:
                    input_value(1)
                    pressed = True
                if elapsed >= hold_end and not released:
                    input_value(0)
                    released = True
                if elapsed >= hold_end + 0.5:
                    break
                fcntl.ioctl(framebuffer, 0x4600, info)
                yoffset = struct.unpack_from('I', info, 20)[0]
                base = yoffset * stride
                # The cart row, excluding the static footer and clock.
                pixels = mapped[base + 80 * stride:base + 380 * stride]
                samples.append((elapsed, zlib.crc32(pixels)))
                if elapsed >= next_frame:
                    frames.append((elapsed, mapped[base:base + height * stride]))
                    next_frame += 0.2
                next_sample += 1 / 60
                time.sleep(max(0, next_sample - time.monotonic()))
        finally:
            input_value(0)
            mapped.close()

    # Ignore the initial key repeat delay and the release/settling period.
    active = [(t, checksum) for t, checksum in samples if hold_start + 0.55 <= t <= hold_end]
    changes = [active[0][0]] if active else []
    for previous, current in zip(active, active[1:]):
        if previous[1] != current[1]:
            changes.append(current[0])
    gaps = [b - a for a, b in zip(changes, changes[1:])]
    if active and changes:
        gaps.append(active[-1][0] - changes[-1])
    summary = {
        'hold_ms': args.hold_ms,
        'samples': len(samples),
        'active_samples': len(active),
        'changed_samples': max(0, len(changes) - 1),
        'longest_unchanged_ms': round(max(gaps, default=0) * 1000, 1),
        'largest_sample_gap_ms': round(max((b[0] - a[0] for a, b in zip(samples, samples[1:])), default=0) * 1000, 1),
    }
    (args.output / 'scroll.json').write_text(json.dumps({'summary': summary, 'samples': samples}, indent=2))
    sheet = Image.new('RGB', (360 * 4, (240 + 24) * ((len(frames) + 3) // 4)))
    draw = ImageDraw.Draw(sheet)
    for index, (elapsed, pixels) in enumerate(frames):
        frame = Image.frombytes('RGB', (width, height), pixels, 'raw', rawmode, stride)
        x, y = (index % 4) * 360, (index // 4) * 264
        sheet.paste(frame.resize((360, 240)), (x, y))
        draw.text((x + 6, y + 244), '%.3f s' % elapsed, fill='white')
    sheet.save(args.output / 'scroll-sheet.png')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
