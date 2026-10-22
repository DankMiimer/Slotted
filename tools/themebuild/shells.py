"""Per-shape assets for the cart renderer, and the generic shells drawn with them.

The heavy lifting (SVG rasterising, distance rings, the circuit board) happens here on the PC, so
the renderer that bakes carts on the handheld (theme/art-book-slot/_slot/slotcart/render.py)
only composites masks with Pillow. See that file for what each asset is.
"""
import hashlib
import json
import sys
from io import BytesIO

import numpy as np
import resvg_py
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

from .geometry import ROOT, SLOT_MIT, OPEN_SANS

sys.path.insert(0, str(ROOT / 'theme' / 'art-book-slot' / '_slot'))
from slotcart import render, shells as cart_shells  # noqa: E402

BOARD = (0x2c, 0x96, 0x52)
TRACE = (0x5a, 0xb4, 0x74)
GOLD = (0xe6, 0xb4, 0x46)

# Where the circuit board sits inside each shell, as fractions of the face:
# x0, x1, top, traces from, contacts from.
BOARDS = {
    'snes-tzakol':(0.12,0.88,0.20,0.84,0.91),
    'gba': (0.14, 0.86, 0.25, 0.78, 0.86),
    'gb': (0.08, 0.92, 0.08, 0.85, 0.92),
    'gbc': (0.08, 0.92, 0.08, 0.85, 0.92),
    'snes': (0.12, 0.88, 0.20, 0.84, 0.91),
    'snes-us': (0.12, 0.88, 0.20, 0.84, 0.91),
    'nes': (0.10, 0.90, 0.12, 0.87, 0.94),
    'n64': (0.12, 0.88, 0.20, 0.86, 0.93),
    'md': (0.1, 0.9, 0.12, 0.82, 0.89),
    'md-jp': (0.1, 0.9, 0.12, 0.82, 0.89),
    'md-ea': (0.14, 0.86, 0.12, 0.88, 0.95),
    'nds': (0.10, 0.90, 0.12, 0.77, 0.84),
    'pico8': (0.1,0.9,0.12,0.85,0.95),
}
CONTACTS = 32
RIM = ((1, 0.55), (2, 0.35), (3, 0.2))  # erosion radius, strength
FLECK_EVERY = 100                        # about one glitter speck per this many pixels

GENERIC = {
    'gba': cart_shells.GBA_CHARCOAL,
    'gb': cart_shells.DMG_GREY,
    'gbc': cart_shells.CGB_CLEAR,
    'snes': cart_shells.SNES_GREY,
    'snes-tzakol':cart_shells.SNES_GREY,
    'snes-us': cart_shells.SNES_US_GREY,
    'nes': cart_shells.NES_GREY,
    'n64': cart_shells.N64_GREY,
    'md': cart_shells.MD_BLACK,
    'md-jp': cart_shells.MD_BLACK,
    'md-ea': cart_shells.MD_BLACK,
    'nds': cart_shells.NDS_GREY,
    'pico8': cart_shells.PICO_GREY,
}


def svg(name, size, source=SLOT_MIT):
    """Render one of Slot's SVGs at `size`, stretching it if the aspect differs."""
    png = resvg_py.svg_to_bytes(svg_path=str(source / name), width=size[0] * 2)
    return Image.open(BytesIO(bytes(png))).convert('RGBA').resize(size, Image.LANCZOS)


def grey(a):
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), 'L')


def board(name, w, h):
    x0, x1, top, traces, contacts = BOARDS[name]
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    ys, xs = np.mgrid[0:h, 0:w]
    fx, fy = xs / w, ys / h
    inside = (fx >= x0) & (fx < x1) & (fy >= top)
    rgba[inside] = BOARD + (255,)
    phase = ((fx - x0) % ((x1 - x0) / CONTACTS)) / ((x1 - x0) / CONTACTS)
    rgba[inside & (fy >= traces) & (phase < 0.2)] = TRACE + (255,)
    rgba[inside & (fy >= contacts) & (phase < 0.6)] = GOLD + (255,)
    return Image.fromarray(rgba, 'RGBA')


def well_box(shape):
    w, h = shape.size
    x0, y0, x1, y1 = shape.well
    return round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)


def bevels(shape):
    """Masks of the 3 px (at 240 wide) bevel around the label well: upper-left and lower-right."""
    w, h = shape.size
    x0, y0, x1, y1 = well_box(shape)
    b = max(2, round(3 * w / 240))
    dark = np.zeros((h, w), dtype=np.float32)
    lit = np.zeros((h, w), dtype=np.float32)
    if shape.well_radius:
        # A rounded recess has a smooth change in lighting around its corners.
        # Finite differences of its blurred mask give the actual surface normals,
        # avoiding the old diagonal split and solid white lower half of the frame.
        inner = Image.new('L', (w, h))
        ImageDraw.Draw(inner).rounded_rectangle((x0, y0, x1-1, y1-1), shape.well_radius, fill=255)
        field = np.asarray(inner.filter(ImageFilter.GaussianBlur(1.5)), dtype=np.float32)/255
        dy, dx = np.gradient(field)
        slope = (dx + dy)*3.2
        return np.clip(slope, 0, .8), np.clip(-slope, 0, .55)
    for y in range(y0 - b, y1 + b):
        for x in range(x0 - b, x1 + b):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            upper = min(y - (y0 - b), x - (x0 - b)) <= min((y1 + b - 1) - y, (x1 + b - 1) - x)
            (dark if upper else lit)[y, x] = 1
    return dark, lit


def flecks(mask):
    h, w = mask.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.uint32)
    v = (xs * np.uint32(0x9e3779b9)) ^ (ys * np.uint32(0x85ebca6b))
    v ^= v >> 15
    v *= np.uint32(0x2c1b3c6d)
    v ^= v >> 12
    return ((v % FLECK_EVERY) == 0) * mask * (100 / 255)


HERO = ROOT / 'tools' / 'themebuild' / 'assets' / 'hero'


def export_model(shape, folder, hero):
    """Shelf layers from the cartridge's own 3D model at the native hero pose.

    tools/consolebuild/hero-shells.sh renders each mesh with neutral plastic.
    Its alpha is the silhouette; its luminance relative to that plastic becomes
    one multiplicative moulding layer, so the baker still tints per game.
    """
    w, h = shape.size
    image = Image.open(hero).convert('RGBA')
    if image.size != (w, h):
        raise ValueError(f'{hero}: {image.size} is not the {shape.name} canvas {w}x{h}')
    alpha = image.getchannel('A'); mask = np.asarray(alpha, dtype=np.float32) / 255
    rgb = np.asarray(image.convert('RGB'), dtype=np.float32).mean(axis=2)
    fixed_path=hero.with_name(hero.stem+'-fixed.png')
    fixed=Image.open(fixed_path).convert('RGB') if fixed_path.exists() else None
    fixed_rgb=np.asarray(fixed,dtype=np.float32).mean(axis=2) if fixed is not None else 0
    model = np.where(mask > 0, np.clip((rgb-fixed_rgb) / 128, 0, 1), 1)
    grey(mask).save(folder / 'mask.png')
    grey(model).save(folder / 'model.png')
    blank = Image.new('L', (w, h))
    for name in ('shade.png', 'light.png', 'rim.png', 'bevel-dark.png', 'bevel-lit.png'):
        blank.save(folder / name)
    grey(flecks(mask)).save(folder / 'flecks.png')
    board(shape.name, w, h).save(folder / 'board.png')
    spec = {'size': [w, h], 'well': list(well_box(shape)), 'model': True}
    measured = json.loads(hero.with_suffix('.json').read_text())
    if fixed is not None:
        fixed.save(folder/'model-fixed.png');spec['fixed']=True
        spec['label']=measured['label'];spec['wellRadius']=0
        Image.open(hero.with_name(hero.stem+'-label.png')).getchannel('A').save(folder/'label-mask.png')
        spec['labelMask']=True
        if shape.name=='pico8':spec['picoStickerCrop']=[16,24,144,196]
    if shape.name in ('gb', 'gbc', 'gba'):
        # The licensed Game Paks' recess is the label; the well stays the video window.
        spec['label'] = measured['label']
    if shape.accent:
        svg(shape.accent, (w, h), shape.source).save(folder/'accent.png')
        spec['accent'] = True
    if shape.well_radius and fixed is None:
        spec['wellRadius'] = shape.well_radius
        ys, xs = np.mgrid[0:h, 0:w]
        light = 5*(1-ys/h) - 8*(np.abs(xs-w/2)/(w/2))**6 - 4*(ys/h)**8
        grain = np.random.default_rng(34).normal(0, 1.2, (h, w))
        Image.fromarray(np.clip(128+light+grain, 0, 255).astype(np.uint8), 'L').save(folder/'surface.png')
        spec['surface'] = True
    fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True).encode())
    for file in sorted(folder.glob('*.png')):
        fingerprint.update(file.read_bytes())
    spec['revision'] = fingerprint.hexdigest()[:16]
    (folder / 'shape.json').write_text(json.dumps(spec), encoding='utf-8')


def export(shape, folder):
    folder.mkdir(parents=True, exist_ok=True)
    hero = HERO / f'{shape.name}.png'
    if hero.exists():
        return export_model(shape, folder, hero)
    w, h = shape.size
    alpha = svg(shape.outline, (w, h), shape.source).getchannel('A')
    mask = np.asarray(alpha, dtype=np.float32) / 255

    detail = np.asarray(svg(shape.detail, (w, h), shape.source), dtype=np.float32) / 255
    lum, a = detail[..., :3].mean(axis=2), detail[..., 3]
    if shape.detail_shadow:
        lum = np.zeros_like(lum)

    keep = np.ones_like(mask)
    for r, k in RIM:
        inner = np.asarray(alpha.filter(ImageFilter.MinFilter(2 * r + 1)), dtype=np.float32) / 255
        keep *= 1 - np.clip(mask - inner, 0, 1) * k
    dark, lit = bevels(shape)

    grey(mask).save(folder / 'mask.png')
    shadow=grey(a*(1-lum));highlight=grey(a*lum)
    if shape.name in ('gb','gbc','gba'):
        # Original font outlines, lit as a shallow moulding on the header.
        # The label/video well remains untouched; no photograph pixels ship.
        wording={'gb':'Nintendo GAME BOY','gbc':'GAME BOY COLOR','gba':'GAME BOY ADVANCE'}[shape.name]
        stamp=Image.new('L',(w,h));font=ImageFont.truetype(str(OPEN_SANS/'OpenSans-SemiBold.ttf'),40)
        bounds=font.getbbox(wording);glyph=Image.new('L',(bounds[2]-bounds[0]+4,bounds[3]-bounds[1]+4))
        ImageDraw.Draw(glyph).text((2-bounds[0],2-bounds[1]),wording,font=font,fill=255)
        glyph.thumbnail((230 if shape.name=='gba' else 211,16 if shape.name=='gba' else 20),Image.Resampling.LANCZOS)
        y=27 if shape.name=='gba' else 48
        stamp.paste(glyph,((w-glyph.width)//2,y))
        upper=ImageChops.subtract(stamp,ImageChops.offset(stamp,1,1))
        lower=ImageChops.subtract(ImageChops.offset(stamp,1,1),stamp)
        shadow=ImageChops.lighter(shadow,lower.point(lambda p:round(p*.6)))
        highlight=ImageChops.lighter(highlight,upper.point(lambda p:round(p*.55)))
    shadow.save(folder/'shade.png')
    highlight.save(folder/'light.png')
    grey(1 - keep).save(folder / 'rim.png')
    grey(dark).save(folder / 'bevel-dark.png')
    grey(lit).save(folder / 'bevel-lit.png')
    grey(flecks(mask)).save(folder / 'flecks.png')
    board(shape.name, w, h).save(folder / 'board.png')
    spec = {'size': [w, h], 'well': list(well_box(shape))}
    if shape.accent:
        svg(shape.accent, (w, h), shape.source).save(folder/'accent.png')
        spec['accent'] = True
    if shape.well_radius:
        spec['wellRadius'] = shape.well_radius
        # Subtle moulded plastic grain and diffuse light, in panel pixels. The
        # handheld composites this prepared layer; no numpy/SVG dependency there.
        ys, xs = np.mgrid[0:h, 0:w]
        light = 5*(1-ys/h) - 8*(np.abs(xs-w/2)/(w/2))**6 - 4*(ys/h)**8
        grain = np.random.default_rng(34).normal(0, 1.2, (h, w))
        surface = Image.fromarray(np.clip(128+light+grain, 0, 255).astype(np.uint8), 'L')
        surface.save(folder/'surface.png')
        spec['surface'] = True
    if shape.well_radius or shape.name in ('gb','gbc','gba'):
        # Changing these assets invalidates only this shape's baked faces.
        fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True).encode())
        for file in sorted(folder.glob('*.png')):
            fingerprint.update(file.read_bytes())
        spec['revision'] = fingerprint.hexdigest()[:16]
    (folder / 'shape.json').write_text(json.dumps(spec),
                                       encoding='utf-8')


def build(out, shapes):
    (out / 'shells').mkdir(parents=True, exist_ok=True)
    (out / 'backings').mkdir(parents=True, exist_ok=True)
    for name, shape in shapes.items():
        if name in ('psx','dreamcast','psp'):
            from . import discs,umd
            (umd if name=='psp' else discs).export(out/'shapes'/name)
            disc = render.Shape(out/'shapes'/name)
            flat = render.umd_texture(disc) if name=='psp' else render.disc_texture(disc)
            flat.save(out/'shells'/(name+'.disc.png'))
            flat.resize((512,512),Image.Resampling.LANCZOS).save(out/'shells'/(name+'.disc.tga'))
            render.disc_poster(disc, flat).save(out/'shells'/(name+'.png'))
            backing=Image.new('RGBA',shape.size,(0,0,0,255));backing.putalpha(disc.mask)
            backing.save(out/'backings'/(name+'.png'))
            continue
        export(shape, out / 'shapes' / name)
        if name == 'nds':
            # The card turns label-down into Slot-1; show its actual opposite
            # face, with opaque plastic and the 17 connector fingers.
            rear = Image.new('RGBA', shape.size)
            rear.putalpha(Image.open(out/'shapes/nds/mask.png'))
            draw = ImageDraw.Draw(rear)
            draw.rounded_rectangle((1,1,310,339),9,fill=(52,54,57,255))
            draw.rounded_rectangle((27,31,285,243), 8, fill=(43,45,48,255), outline=(69,71,74,255), width=2)
            draw.rectangle((24,258,288,340), fill=(16,18,20,255))
            for i in range(17):
                x=29+i*15
                draw.rectangle((x,265,x+10,325), fill=(181,143,63,255))
                draw.rectangle((x+2,268,x+3,321), fill=(224,188,104,255))
                draw.rectangle((x+11,259,x+14,340),fill=(52,54,57,255))
            rear.putalpha(Image.open(out/'shapes/nds/mask.png'))
            rear.save(out/'shapes/nds/rear.png')
            # Include the newly generated reverse face, not a previous build's
            # rear.png, in the cache key. Rebuilding unchanged assets is stable.
            folder=out/'shapes/nds';spec=json.loads((folder/'shape.json').read_text())
            spec.pop('revision',None)
            fingerprint=hashlib.sha256(json.dumps(spec,sort_keys=True).encode())
            for file in sorted(folder.glob('*.png')):fingerprint.update(file.read_bytes())
            spec['revision']=fingerprint.hexdigest()[:16]
            (folder/'shape.json').write_text(json.dumps(spec),encoding='utf-8')
        face = render.face(render.Shape(out / 'shapes' / name), GENERIC[name])
        face.save(out / 'shells' / f'{name}.png')
        backing = Image.new('RGBA', shape.size, (0, 0, 0, 255))
        backing.putalpha(Image.open(out / 'shapes' / name / 'mask.png'))
        backing.save(out / 'backings' / f'{name}.png')
