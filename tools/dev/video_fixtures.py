"""Create original crop/mask diagnostic clips; requires Pillow and ffmpeg.

Circles and squares are drawn in display coordinates, including the non-square
pixel fixture. Edge colours expose unintended stretching or leaking at masks.
"""
import argparse
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


FORMATS = {'4x3': (640, 480, 1), '16x9': (640, 360, 1),
           'portrait': (360, 640, 1), 'sar2': (320, 480, 2)}


def build(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, (width, height, sar) in FORMATS.items():
        display_width = width * sar
        base = Image.new('RGB', (display_width, height), '#263441')
        drawing = ImageDraw.Draw(base)
        cx, cy = display_width / 2, height / 2
        unit = min(display_width, height) / 4
        for offset in (-1, 0, 1):
            x, y = cx + offset * unit, cy + offset * unit
            drawing.line((x, 0, x, height), fill='#8198a5', width=2)
            drawing.line((0, y, display_width, y), fill='#8198a5', width=2)
        drawing.rectangle((cx-unit, cy-unit, cx+unit, cy+unit), outline='#36ed6a', width=6)
        drawing.ellipse((cx-unit, cy-unit, cx+unit, cy+unit), outline='#ffffff', width=6)
        drawing.rectangle((0, 0, display_width-1, height-1), outline='#ef344b', width=12)
        # Correct display-space circles become ellipses in encoded non-square pixels.
        base = base.resize((width, height), Image.Resampling.LANCZOS)
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (width, height),
                   '-r', '30', '-i', '-', '-vf', 'setsar=%d' % sar, '-an',
                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                   '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(folder / (name + '.mp4'))]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for frame in range(180):
                image = base.copy()
                ImageDraw.Draw(image).rectangle((frame % width, 0, frame % width+8, 16), fill='#ffe03b')
                process.stdin.write(image.tobytes())
        finally:
            process.stdin.close()
        if process.wait():
            raise RuntimeError('ffmpeg failed: ' + name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
