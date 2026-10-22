#!/usr/bin/env python3
"""Measure ES frame presentation from framebuffer page flips while injecting input.

Mali/fbdev presents each frame by panning fb0. Polling the pan offset at about
2 kHz timestamps real flips without reading pixels, so it adds little load and
measures presented-frame intervals rather than screenshot sampling gaps.
ES only presents while something animates; idle stretches are excluded by
reporting intervals inside each motion window after a tap.
"""
import argparse
import fcntl
import json
import struct
import threading
import time

from esdev import press


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--taps', default='right*8', help='esdev press tokens, separated by spaces')
    parser.add_argument('--settle', type=float, default=1.0)
    parser.add_argument('--output')
    args = parser.parse_args()
    flips, taps = [], []
    stop = threading.Event()

    def sample():
        var = bytearray(160)
        with open('/dev/fb0', 'rb') as fb:
            last = None
            while not stop.is_set():
                fcntl.ioctl(fb, 0x4600, var)
                offset = struct.unpack_from('I', var, 20)[0]
                if offset != last:
                    flips.append(time.monotonic())
                    last = offset
                time.sleep(0.0005)

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    time.sleep(args.settle)
    started = time.monotonic()
    for token in args.taps.split():
        taps.append(time.monotonic())
        press([token])
    time.sleep(args.settle)
    stop.set()
    thread.join()
    moving = [b - a for a, b in zip(flips, flips[1:]) if a >= started and b - a < 0.25]
    moving.sort()

    def pct(p):
        return round(moving[min(len(moving) - 1, int(p * len(moving)))] * 1000, 1) if moving else None

    long = [(round((a - started) * 1000), round((b - a) * 1000, 1))
            for a, b in zip(flips, flips[1:]) if a >= started and 0.025 < b - a < 0.25]
    result = {'frames': len(moving), 'p50_ms': pct(.5), 'p95_ms': pct(.95), 'p99_ms': pct(.99),
              'max_ms': round(moving[-1] * 1000, 1) if moving else None,
              'over_25ms': len(long), 'long_frames_at_ms': long[:40],
              'taps_at_ms': [round((t - started) * 1000) for t in taps]}
    if args.output:
        with open(args.output, 'w') as stream:
            json.dump({'flips': [t - started for t in flips], **result}, stream)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
