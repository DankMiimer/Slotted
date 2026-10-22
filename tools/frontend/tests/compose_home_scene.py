"""Host preview of the inserted home-console scene: console + TV on one floor (MIT).

    sh run_probe.sh python3 compose_home_scene.py PROBE SLOT OUTDIR [MODEL...] [--tv retro]

Mirrors SlotPresentation::prepareGeometry/render: the console comes from the native probe's `front`
pose (with its printed `bounds` and `ground`), the TV from `stage/tv/<id>.png` and its profile, and the
metadata surface is a stand-in text panel warped onto the registered glass quad. It reproduces the
layout arithmetic, not the frontend's fonts, so it is for review of placement, scale and overlap.
"""
import json, math, os, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

probe, slot, out = map(Path, sys.argv[1:4])
rest = sys.argv[4:]
tv_id = 'panasonic'
if '--tv' in rest:
    tv_id = rest[rest.index('--tv') + 1]
    rest = [a for a in rest if a not in ('--tv', tv_id)]
models = rest or ['snes', 'nes', 'n64', 'md', 'psx', 'dreamcast', 'pico8']
out.mkdir(parents=True, exist_ok=True)
profile = next(p for p in json.loads((slot / 'stage/tv/profiles.json').read_text())['profiles'] if p['id'] == tv_id)
tv = Image.open(slot / profile['image']).convert('RGBA')
dw, dh = profile['display']
base = profile['base']
quad = np.array(profile['quad'])


def edge(a, b):
    return math.hypot((quad[b][0] - quad[a][0]) * dw, (quad[b][1] - quad[a][1]) * dh)


screen_w, screen_h = math.floor(min(edge(0, 1), edge(3, 2))), math.floor(min(edge(0, 3), edge(1, 2)))


def radial(width, height, colour, peak, power):
    y, x = np.mgrid[0:height, 0:width]
    r = np.hypot((x + .5 - width / 2) / (width / 2), (y + .5 - height / 2) / (height / 2))
    a = np.clip(1 - r, 0, 1) ** power * peak
    im = np.zeros((height, width, 4), np.uint8)
    im[..., :3] = colour
    im[..., 3] = np.round(a * 255)
    return Image.fromarray(im, 'RGBA')


shadow = Image.open(slot / 'stage/shadow.png').convert('RGBA')
glow = Image.open(slot / 'stage/floor.png').convert('RGBA')


def paste_centre(canvas, image, size, centre):
    image = image.resize((max(1, round(size[0])), max(1, round(size[1]))), Image.Resampling.LANCZOS)
    canvas.alpha_composite(image, (round(centre[0] - image.width / 2), round(centre[1] - image.height / 2)))


def stand_in_screen():
    surface = Image.new('RGBA', (screen_w, screen_h), (14, 25, 27, 255))
    d = ImageDraw.Draw(surface)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((10, 6), 'Super Mario World', fill=(246, 244, 239), font=font)
    d.text((10, 28), 'Players: 2   1990', fill=(170, 216, 188), font=small)
    d.line((10, 50, screen_w - 10, 50), fill=(66, 102, 90))
    d.rectangle((10, 58, 10 + screen_w * .3, 58 + screen_h * .35), fill=(70, 90, 140))
    for i in range(3):
        d.text((screen_w * .38, 58 + i * 20), ('Mario sets out to rescue', 'the princess across the', 'Dinosaur Land islands.')[i], fill=(229, 225, 213), font=small)
    d.text((10, screen_h - 22), 'L1 / R1  1 / 5  Overview', fill=(229, 225, 213), font=small)
    return surface


def warp(surface, corners, canvas_size):
    """Perspective-map the surface onto four canvas points (TL, TR, BR, BL)."""
    w, h = surface.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    a = []
    for (x, y), (u, v) in zip(corners, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    coeffs = np.linalg.solve(np.array(a, float), np.array([c for p in src for c in p], float))
    return surface.transform(canvas_size, Image.Transform.PERSPECTIVE, tuple(coeffs), Image.Resampling.BICUBIC)


for model in models:
    raw = out / (model + '.bmp')
    env = dict(os.environ, SLOT_MODEL_STYLE='realistic', SLOT_CONSOLE_COLOR='original', SLOT_GBA_SP='graphicsgeek')
    run = subprocess.run([str(probe), str(slot), str(raw), model, 'front'], env=env, capture_output=True, text=True)
    bounds = ground = contact = None
    for line in run.stdout.splitlines():
        if line.startswith('bounds'):
            bounds = list(map(float, line.split()[2:6]))
        if line.startswith('ground'):
            ground = list(map(float, line.split()[2:6]))
        if line.startswith('contact'):
            contact = list(map(float, line.split()[2:4]))
    if not bounds or not ground or not contact:
        print(model, 'skipped: no ground/bounds', run.stdout[-200:], run.stderr[-200:])
        continue
    b0, b1, bw, bh = bounds
    cx, cy, ex, ey = ground
    units=dict(snes=1.6,**{'snes-us':1.55,'n64':1.5,'psx':1.6,'dreamcast':1.3,'nes':1.63333333,
                          'md':2.05504587,'md-jp':2.05504587,'pico8':2.2})
    floor_y = min(478-(dh-profile['contact'][1]),124+profile['contact'][1])
    scale = min(profile['units_per_mm']/units[model],326/bw,
                (floor_y-124)/max(1,contact[1]-b1),(478-floor_y)/max(1,b1+bh-contact[1]))
    tv_pos = (716-dw,floor_y-profile['contact'][1])
    centre_x = (12+tv_pos[0]-16)/2
    rect = (centre_x-(b0+bw/2)*scale,floor_y-contact[1]*scale,720*scale,480*scale)
    console_floor = (rect[0]+cx*scale,rect[1]+cy*scale,ex*scale,ey*scale)
    scene = Image.new('RGBA', (720, 480), (8, 9, 13, 255))
    paste_centre(scene, glow, (760, 150), (360, floor_y + 8))
    paste_centre(scene, shadow, (max(60, console_floor[2] * 1.25), max(26, console_floor[3] * 1.3)), (console_floor[0], console_floor[1]))
    tv_x = tv_pos[0] + base[0]
    paste_centre(scene, shadow, (profile['footprint'][0] * 1.08, profile['footprint'][1] * 1.2), (tv_x, tv_pos[1]+base[1]))
    d = ImageDraw.Draw(scene)
    start = console_floor[0] + console_floor[2] / 2
    length = tv_x - profile['footprint'][0] / 2 - start
    if length > 0:
        d.rectangle((start, floor_y + 5, start + length, floor_y + 7), fill=(0x30, 0x31, 0x2F, 255))
    scene.alpha_composite(tv.resize((round(dw), round(dh)), Image.Resampling.LANCZOS), (round(tv_pos[0]), round(tv_pos[1])))
    corners = [(tv_pos[0] + qx * dw, tv_pos[1] + qy * dh) for qx, qy in quad]
    screen = warp(stand_in_screen(), corners, scene.size)
    mask = warp(Image.new('L', (screen_w, screen_h), 255), corners, scene.size)
    scene.paste(screen, (0, 0), mask)
    console = Image.open(raw).convert('RGBA').resize((round(720 * scale), round(480 * scale)), Image.Resampling.LANCZOS)
    scene.alpha_composite(console, (round(rect[0]), round(rect[1])))
    clipped = scene.crop((0, 120, 720, 480))
    top = Image.new('RGBA', (720, 480), (8, 9, 13, 255))
    top.alpha_composite(clipped, (0, 120))
    top.convert('RGB').save(out / f'{model}-{tv_id}-scene.png')
    (out/f'{model}-{tv_id}-layout.json').write_text(json.dumps(dict(model=model,tv=tv_id,bounds=bounds,ground=ground,
        contact=contact,scale=scale,rect=rect,tv_pos=tv_pos,front_y=floor_y,console_floor=console_floor),indent=2)+'\n')
    print(f'{model}: scale {scale:.3f} floor {floor_y:.0f}; console floor {tuple(round(v) for v in console_floor)}; '
          f'glass {screen_w}x{screen_h}; TV at {tuple(round(v) for v in tv_pos)}')
