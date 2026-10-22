"""Footer battery icons: a small gauge, with a bolt beside it while charging.

ES's batteryIcon picks one image per level (full, at75, at50, at25, empty, incharge). They are
drawn 24 px tall to match the footer row so ES shows them at 1:1, and all share one width with
the gauge at the same x, so the percentage beside them never moves when charging starts.
"""
from PIL import Image, ImageDraw

from .geometry import INK

SS = 4
ROW_H = 24
GAUGE_W, GAUGE_H = 22, 11
WALL = 1.5
NUB_W, NUB_H = 2.5, 4
BOLT_W, BOLT_H = 12, 15
BOLT_GAP = 5
LOW = (0xe5, 0x53, 0x3b)

LEVELS = {'full': 1.0, 'at75': 0.75, 'at50': 0.5, 'at25': 0.25, 'empty': 0.0}


def gauge(draw, x, level, colour):
    y = (ROW_H - GAUGE_H) / 2
    s = SS
    draw.rounded_rectangle([x * s, y * s, (x + GAUGE_W) * s, (y + GAUGE_H) * s], radius=2.5 * s,
                           outline=colour + (255,), width=round(WALL * s))
    draw.rounded_rectangle([(x + GAUGE_W + 0.5) * s, (ROW_H - NUB_H) / 2 * s,
                            (x + GAUGE_W + NUB_W) * s, (ROW_H + NUB_H) / 2 * s],
                           radius=1 * s, fill=colour + (255,))
    inset = WALL + 1.5
    span = GAUGE_W - 2 * inset
    if level > 0:
        draw.rounded_rectangle([(x + inset) * s, (y + inset) * s, (x + inset + span * level) * s,
                                (y + GAUGE_H - inset) * s], radius=1 * s, fill=colour + (255,))


def bolt(draw, x):
    s = SS
    y = (ROW_H - BOLT_H) / 2
    pts = [(7, 0), (0, 8.5), (5, 8.5), (4, 15), (12, 6), (7, 6), (8, 0)]
    draw.polygon([((x + px) * s, (y + py) * s) for px, py in pts], fill=INK + (255,))


ICON_W = 42  # bolt, gap, gauge and nub, rounded up to whole pixels


def icon(level, charging):
    img = Image.new('RGBA', (ICON_W * SS, ROW_H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if charging:
        bolt(d, 0)
    gauge(d, BOLT_W + BOLT_GAP, level, LOW if level == 0 and not charging else INK)
    return img.resize((ICON_W, ROW_H), Image.LANCZOS)


def build(out):
    (out / 'icons').mkdir(parents=True, exist_ok=True)
    for name, level in LEVELS.items():
        icon(level, False).save(out / 'icons' / f'battery-{name}.png')
    icon(1.0, True).save(out / 'icons' / 'battery-charging.png')
