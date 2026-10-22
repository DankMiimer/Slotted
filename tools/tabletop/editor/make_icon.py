"""Draws the scene editor's desktop icon (the editor's "S" badge) as slotted-editor.ico (MIT).

    python tools/tabletop/editor/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def badge(size):
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(1, size // 16)
    draw.rounded_rectangle((margin, margin, size - margin - 1, size - margin - 1), radius=size // 5, fill=(204, 232, 183, 255))
    font = None
    for name in ('segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            font = ImageFont.truetype(name, int(size * .66))
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    draw.text((size / 2, size / 2), 'S', fill=(38, 51, 34, 255), font=font, anchor='mm')
    return image


if __name__ == '__main__':
    sizes = (16, 24, 32, 48, 64, 128, 256)
    badge(256).save(HERE / 'slotted-editor.ico', sizes=[(s, s) for s in sizes])
    print(HERE / 'slotted-editor.ico')
