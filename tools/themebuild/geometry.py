"""Panel geometry shared by every generated asset and shelf view.

Everything is in panel pixels for a 720x480 screen. ES theme values are normalised from these at
the point they are written out.
"""
import math
from dataclasses import dataclass,replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLOT_MIT = ROOT / 'third_party' / 'slot-mit'
SLOT2_MIT = ROOT / 'third_party' / 'slot2-mit'
OPEN_SANS = ROOT / 'third_party' / 'open-sans'
RASTER_FORGE = ROOT / 'third_party' / 'raster-forge'

W, H = 720, 480

# The slot band along the bottom of the screen.
BAND_H = 58
BAND_Y = H - BAND_H
LIP_H = 2
SEATED_W = 240
MOUTH_W = SEATED_W + 14
BAY_W = MOUTH_W + 18
RECESS_H = 42
SLIT_H = 9
RIM_W = 2
SCOOP_W = MOUTH_W * 0.88
SCOOP_POWER = 4

# Band-relative rows.
BAY_Y = LIP_H
SLIT_Y = BAY_Y + 5
SCOOP_Y = SLIT_Y + SLIT_H
SCOOP_D = RECESS_H - (SCOOP_Y - BAY_Y)

HOUSING = (0x24, 0x24, 0x29)
RECESS = (0x1a, 0x1a, 0x1d)
OPENING = (0x05, 0x05, 0x08)
EDGE = (0x4d, 0x4d, 0x57)
INK = (0xf6, 0xf4, 0xef)

# Top status (battery left, clock right) and the shelf name inside the slot.
FOOTER_MARGIN = 24
FOOTER_TEXT_H = 24
FOOTER_Y = 12
SLOT_NAME_Y = BAND_Y + SLIT_Y + (SCOOP_Y + SCOOP_D - SLIT_Y) / 2  # centre of the opening

# Neighbouring carts on the shelf.
SIDE_SCALE = 0.78
SIDE_BRIGHTNESS = 0.55
CAROUSEL_H = BAND_Y


@dataclass(frozen=True)
class Shape:
    """One kind of physical media: its outline, its label well and where it rests on the shelf."""
    name: str
    outline: str           # SVG silhouette (white on transparent)
    detail: str            # SVG moulding: black = shadow, white = light
    size: tuple            # face in panel pixels
    well: tuple            # label well as fractions of the face: x0, y0, x1, y1
    seated: tuple          # size once it is down in the slot
    source: Path = SLOT_MIT
    detail_shadow: bool = False  # SLOT2's new details are white shadow coverage
    well_radius: int = 0
    video_well: tuple = ()  # optional common video area shared by regional shells
    accent: str = ''        # fixed-colour moulded part, such as EA's yellow grip

    @property
    def top(self):
        w, h = self.size
        if h > GBA.size[1]:
            # Tall carts are centred in the space above the band, on a whole pixel.
            return math.floor((BAND_Y - h) / 2 + 0.5)
        # Short carts share the GBA's foot line.
        return (H + GBA.size[1]) / 2 - h

    @property
    def foot(self):
        return self.top + self.size[1]


GBA = Shape('gba', 'cart.svg', 'cart_detail.svg', (360, 212), (0.135, 0.231, 0.875, 0.882), (240, 141))
GB = Shape('gb', 'gb_cart.svg', 'gb_cart_detail.svg', (312, 337), (0.133, 0.277, 0.867, 0.870), (240, 259))
GBC = Shape('gbc', 'gbc_cart.svg', 'gbc_cart_detail.svg', (312, 337), (0.133, 0.277, 0.867, 0.870), (240, 259))
SNES = Shape('snes', 'snes-pal.svg', 'snes-pal-detail.svg', (360, 245),
             (30/360, 12/245, 330/360, 120/245), (240, 163), ROOT/'tools/themebuild/assets',
             well_radius=10, video_well=(80/360, 22/245, 280/360, 110/245))
SNES_US = Shape('snes-us', 'snes-us.svg', 'snes-us-detail.svg', (360, 245),
                (70/360, 7/245, 290/360, 111/245), (240, 163), ROOT/'tools/themebuild/assets',
                well_radius=10)
NES = Shape('nes', 'nes.svg', 'nes-detail.svg', (304, 337),
            (122/304, 4/337, 263/304, 230/337), (240, 266), ROOT/'tools/themebuild/assets',
            well_radius=3, video_well=(124/304, 80/337, 261/304, 183/337))
N64 = Shape('n64', 'n64.svg', 'n64-detail.svg', (360, 241),
            (78/360, 26/241, 282/360, 220/241), (240, 161), ROOT/'tools/themebuild/assets',
            well_radius=10, video_well=(96/360, 58/241, 265/360, 185/241))
MD = Shape('md', 'md.svg', 'md-detail.svg', (360, 270),
           (51/360, 22/270, 311/360, 232/270), (240, 180), ROOT/'tools/themebuild/assets',
           well_radius=8, video_well=(98/360, 70/270, 301/360, 222/270))
MD_JP = Shape('md-jp', 'md-jp.svg', 'md-jp-detail.svg', MD.size,
              (50/360, 24/270, 311/360, 231/270), MD.seated, MD.source,
              well_radius=10, video_well=MD.video_well)
MD_EA = Shape('md-ea', 'md-ea.svg', 'md-ea-detail.svg', MD.size,
              (96/360, 3/270, 303/360, 224/270), MD.seated, MD.source,
              well_radius=2, video_well=MD.video_well, accent='md-ea-accent.svg')

PSX = Shape('psx', '', '', (336, 336), (90/336, 38/336, 246/336, 108/336), (240, 240),
            video_well=(98/336, 225/336, 238/336, 299/336))
DREAMCAST = Shape('dreamcast', '', '', PSX.size, PSX.well, PSX.seated, video_well=PSX.video_well)
PSP = Shape('psp', '', '', (336, 336), (70/336, 72/336, 266/336, 133/336), (240,240),
            video_well=(106/336,223/336,230/336,290/336))
NDS = Shape('nds', 'nds.svg', 'nds-detail.svg', (312, 341),
            (23/312, 17/341, 289/312, 302/341), (112, 122), ROOT/'tools/themebuild/assets',
            well_radius=9, video_well=(31/312, 110/341, 281/312, 270/341))
PICO8 = Shape('pico8', 'pico8.svg', 'pico8-detail.svg', (264, 338),
              (16/160, 24/205, 144/160, 152/205), (132,169), ROOT/'tools/themebuild/assets',
              video_well=(16/160, 24/205, 144/160, 152/205))

SHAPES = {s.name: s for s in (GBA, GB, GBC, SNES, SNES_US, NES, N64, MD, MD_JP, MD_EA, PSX, DREAMCAST, PSP, NDS, PICO8)}
SHAPES['snes-tzakol']=replace(SNES,name='snes-tzakol',well_radius=0)
# Authored media's measured physical sticker is also its shelf/video boundary.
import json
for _key in ('gba','snes','n64','pico8','snes-tzakol'):
    _folder='snes' if _key=='snes-tzakol' else _key
    _part='media-tzakol' if _key=='snes-tzakol' else 'media'
    _hero=ROOT/'tools/themebuild/assets/hero'/(_key+'.json')
    if _hero.exists() and (ROOT/'theme/art-book-slot/_slot/consoles'/_folder/(_part+'-registration.json')).exists():
        _shape=SHAPES[_key];_label=json.loads(_hero.read_text())['label']
        if _key=='pico8':_label=[*_label[:3],_label[1]+(_label[3]-_label[1])*128/172]
        _well=tuple(v/_shape.size[i%2] for i,v in enumerate(_label))
        SHAPES[_key]=replace(_shape,well=_well,video_well=_well,well_radius=0)


# ES system theme name -> (shape, generic shell). Hack and variant systems reuse the shelves.
SYSTEMS = {
    'gba': ('gba', 'gba'),
    'gbah': ('gba', 'gba'),
    'gb': ('gb', 'gb'),
    'gbh': ('gb', 'gb'),
    'gbc': ('gbc', 'gbc'),
    'gbch': ('gbc', 'gbc'),
    'snes': ('snes', 'snes'),
    'snesh': ('snes', 'snes'),
    'nes': ('nes', 'nes'),
    'nesh': ('nes', 'nes'),
    'n64': ('n64', 'n64'),
    'n64h': ('n64', 'n64'),
    'megadrive': ('md', 'md'),
    'genesis': ('md', 'md'),
    'psx': ('psx', 'psx'),
    'dreamcast': ('dreamcast', 'dreamcast'),
    'psp': ('psp', 'psp'),
    'nds': ('nds', 'nds'),
    'pico8': ('pico8', 'pico8'),
}
