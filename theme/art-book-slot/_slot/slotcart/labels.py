"""Where a cart's label comes from. First hit wins:

1. own    the user's image: <rom dir>/media/labels/<stem>.png|.jpg, or <labels dir>/<SYS>/<stem>.png|.jpg
          (Slot's Labels/ layout, so labels made with Cart Studio work as they are)
2. scan   Slot's handheld label scan by ROM CRC32, or regional LaunchBox console cartridge art
3. logo   the game's logo on a plain label: the art set's wheel, <rom dir>/media/wheels/<stem>,
          else the scraped marquee
4. text   the game's name on a plain label

Downloads are cached under ~/.cache/slotcart, so a second run needs no network.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ART = 'https://art.slot-cfw.fyi/'
# art.slot-cfw.fyi answers 403 to urllib's default agent.
AGENT = 'Mozilla/5.0 (X11; Linux aarch64) slotcart/1 (Art Book Slot theme)'
INDEX_MAX_AGE = 7 * 24 * 3600

FONT = Path(__file__).resolve().parents[1] / 'fonts' / 'OpenSans-SemiBold.ttf'
OWN_EXTENSIONS = ('.png', '.jpg', '.jpeg')
SYS = {'gba': 'GBA', 'gb': 'GB', 'gbc': 'GBC', 'snes': 'SNES', 'nes': 'NES', 'n64': 'N64', 'md': 'MD', 'psx': 'PSX', 'dreamcast': 'DREAMCAST', 'psp': 'PSP', 'nds': 'NDS', 'pico8': 'PICO8'}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class ArtSet:
    """Slot's art set: index.json maps a ROM CRC32 to a label scan, a logo and a label colour."""

    def __init__(self, cache, offline=False):
        self.cache = Path(cache) / 'art'
        self.cache.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.index = self._load_index()

    def _load_index(self):
        path = self.cache / 'index.json'
        fresh = path.exists() and time.time() - path.stat().st_mtime < INDEX_MAX_AGE
        if not fresh and not self.offline:
            try:
                path.write_bytes(get(ART + 'index.json'))
            except OSError as ex:
                print('art set index not refreshed:', ex)
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def entry(self, crc):
        return self.index.get(crc) or {}

    def cached(self, rel):
        return self.cache / rel

    def fetch(self, rel):
        """Local path of an art-set file, downloading it if needed; None if unavailable."""
        path = self.cached(rel)
        if path.exists():
            return path
        if self.offline:
            return None
        try:
            data = get(ART + rel)
        except OSError:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.part')
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return path


def candidates(game, art, labels_dir=None, carts=None):
    """Label plans in order of preference, without downloading anything: (kind, source, colour).
    `source` is a local path, a download name or (for text) the title. The third value is
    paper colour for logo/text, or a source record for a console cart scan. Text always works."""
    out = []
    # Skraper keeps a scan's original format, so JPEG labels are accepted too.
    own = [game.dir / 'media' / 'labels' / (game.stem + ext) for ext in OWN_EXTENSIONS]
    if labels_dir:
        own += [Path(labels_dir) / SYS[game.kind] / (game.stem + ext) for ext in OWN_EXTENSIONS]
    out += [('own', str(p), None) for p in own if p.exists()]
    if game.kind in ('snes', 'nes', 'n64', 'md', 'psx', 'dreamcast', 'psp', 'nds') and carts is not None:
        provider = carts[game.kind] if isinstance(carts, dict) else carts
        out += [('disc-scan' if game.kind in ('psx','dreamcast','psp') else 'cart-scan', image['FileName'], image) for image in provider.candidates(game)]
    # Slot's CRC art set covers Nintendo handhelds only, never console CRC hits.
    entry = art.entry(game.crc) if game.kind in ('gba', 'gb', 'gbc') and game.crc else {}
    ground = (entry.get('look') or {}).get('ground')
    paper = tuple(int(ground[i:i + 2], 16) for i in (0, 2, 4)) if ground else paper_colour(game)
    if entry.get('support-texture'):
        out.append(('scan', entry['support-texture'], None))
    if entry.get('wheel'):
        out.append(('logo', entry['wheel'], paper))
    # A wheel logo downloaded next to the ROM (the Skraper preset's media\wheels).
    out += [('logo', str(p), paper) for p in
            (game.dir / 'media' / 'wheels' / (game.stem + ext) for ext in OWN_EXTENSIONS) if p.exists()][:1]
    if game.marquee and Path(game.marquee).exists():
        out.append(('logo', game.marquee, paper))
    out.append(('text', game.title, paper_colour(game)))
    return out


def fnv1a(text):
    h = 0xcbf29ce484222325
    for b in text.encode('utf-8'):
        h = ((h ^ b) * 0x100000001b3) & 0xffffffffffffffff
    return h


def hsv(h, s, v):
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return tuple(round((u + m) * 255) for u in (r, g, b))


def paper_colour(game):
    """A muted colour that is the same for a title every time."""
    return hsv(fnv1a(game.title) % 360, 0.52, 0.74)


def ink_for(colour):
    luma = 0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2]
    return (0x1a, 0x18, 0x16) if luma > 140 else (0xf4, 0xf1, 0xea)


def logo_label(size, logo_path, colour):
    label = Image.new('RGB', size, colour)
    logo = Image.open(logo_path).convert('RGBA')
    pad = round(min(size) * 0.1)
    logo = ImageOps.contain(logo, (size[0] - 2 * pad, size[1] - 2 * pad), Image.LANCZOS)
    label.paste(logo, ((size[0] - logo.width) // 2, (size[1] - logo.height) // 2), logo)
    return label


def wrap(draw, words, font, width):
    lines, line = [], ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def text_label(size, title, colour, max_lines=3):
    label = Image.new('RGB', size, colour)
    draw = ImageDraw.Draw(label)
    pad = round(min(size) * 0.08)
    width, height = size[0] - 2 * pad, size[1] - 2 * pad
    words = title.split()
    for px in range(round(size[1] / (max_lines * 1.3)), 9, -1):
        font = ImageFont.truetype(str(FONT), px)
        lines = wrap(draw, words, font, width)
        step = round(px * 1.25)
        fits = all(draw.textlength(l, font=font) <= width for l in lines)
        if len(lines) <= max_lines and step * len(lines) <= height and fits:
            break
    y = (size[1] - step * len(lines)) / 2
    ink = ink_for(colour)
    for line in lines:
        draw.text((size[0] / 2, y + step / 2), line, font=font, fill=ink, anchor='mm')
        y += step
    return label


def make(kind, source, colour, size, art):
    """The label image for a plan, or None if its file could not be had."""
    if kind == 'own':
        return Image.open(source)
    if kind == 'scan':
        path = art.fetch(source)
        return Image.open(path) if path else None
    if kind == 'logo':
        path = Path(source) if Path(source).is_absolute() else art.fetch(source)
        return logo_label(size, path, colour) if path else None
    return text_label(size, source, colour)
