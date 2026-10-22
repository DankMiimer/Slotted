"""Pack registered textured sources into the native mesh + UV/albedo sidecar (MIT).

    python -m tools.consolebuild.textured gbc

Reads build/textured/<model>/ written by a Blender adapter (e.g. bpoole_gbc.py)
and writes theme/art-book-slot/_slot/consoles/<model>/:
  model.mesh          SCTOON2 positions, normals, fallback colours (legacy readers)
  model.texture       SCTEX003: vertex/index/PNG-file hashes, paint luminance, UVs
  model.albedo.png    RGBA atlas; alpha marks repaintable plastic
  paint.mask          SCPAINT1 fallback weights for the untextured path
  mesh-info.json, registration.json
The atlas keeps each source image's own UV layout. Images are only reduced,
never enlarged. Game art baked into a source (screens, fixed media labels) is
blanked; removed parts' texture regions are cleared before reuse.
"""
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SLOT = ROOT / 'theme/art-book-slot/_slot'
LCD = (14, 27, 27)          # unlit reflective LCD under glass, display RGB
NEUTRAL = (180, 180, 180)   # cleared, unused atlas area

CONFIG = {
    'psx': dict(family='darkigorek-psx-textured',size=2048,tile_size=4096,primary='ps1_body_mat',
        tiles={'ps1_body_mat':(0,0,.5,.5),'ps1_details_mat':(.5,0,1,.5)},constants={'plugs':(0,0,0)},
        blank=[],paint=dict(hue=(0,360),saturation=0,max_saturation=.22,value=.40),
        creators=[dict(author='dark_igorek',licence='CC-BY-4.0',
            url='https://sketchfab.com/3d-models/sony-pvm-1341-sony-playstation-5f80311f1a4646ef9673f20ee6dc6245')]),
    'gb': dict(family='verheyen-dmg',size=2048,primary='Scene_-_Root',repeat_u=2,blank_lcd=True,
        blank=[],paint=dict(hue=(15,75),saturation=.02,max_saturation=.24,value=.45),
        creators=[dict(author='Bram Verheyen',licence='CC-BY-NC-4.0',
            url='https://sketchfab.com/3d-models/gameboy-classic-854c46e14ce24779ad64ae74cb9b9089')]),
    'psp': dict(family='ostrovsky-psp',size=2048,primary='sony_psp',vertex_decimals=5,normal_decimals=4,
        blank=[dict(uv=(.0058,.4077,.4011,.6317),colour=LCD,reason='baked PSP home screen')],
        constants={'Slot UMD interior':(.008,.009,.012),'Slot UMD holder':(.35,.38,.4)},
        paint=dict(hue=(0,360),saturation=0,max_saturation=.18,value=.035,max_value=.34),
        creators=[dict(author='Ilya Ostrovsky',licence='CC-BY-4.0',
            url='https://sketchfab.com/3d-models/sony-psp-dca89d10ec304d0cab76837750df7761')]),
    'nds': dict(family='cianon-ds-lite',size=2048,primary='03_-_Default',blank_lcd=True,
        # The fixed game card painted on the source's Slot-1 notch (primary UV space, v up).
        blank=[dict(uv=(.7275,.625,.8032,.6543),colour=(14,14,16),reason='fixed game-card picture on the Slot-1 notch')],
        constants={'Slot DS mouth':(.006,.006,.007)},
        paint=dict(hue=(0,360),saturation=0,max_saturation=.18,value=.035,max_value=.34),
        creators=[dict(author='Cianon',licence='CC-BY-4.0',
            url='https://sketchfab.com/3d-models/nintendo-ds-lite-ca529eb7208746e89b7a28fd2246659d')]),
    'gba': dict(family='graphicsgeek-ags-textured',size=2048,tile_size=2048,primary='Gameboy_1001_MAT',
        # Three 1024 px material tiles, kept at native resolution in one 2048 px atlas.
        tiles={'Gameboy_1001_MAT':(0,0,.5,.5),'Gameboy_1002_MAT':(.5,0,1,.5),'Gameboy_1003_MAT':(0,.5,.5,1)},
        constants={'Screen_MAT':(.0060367,.0117506,.0068896)},
        blank=[],paint=dict(hue=(0,360),saturation=0,max_saturation=.16,value=.45),
        creators=[dict(author='thegraphicsgeek',licence='CC-BY-4.0',
            url='https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f')]),
    'dreamcast': dict(family='zerescas-dreamcast', size=2048, primary='Case',
        tiles={'Case':(0,0,.5,.5), 'Door_and_ports':(.5,0,1,.5)},
        blank=[], paint=dict(hue=(0,360), saturation=0, max_saturation=.17, value=.48),
        creators=[dict(author='Zerescas', licence='CC-BY-4.0',
            url='https://sketchfab.com/3d-models/sega-dreamcast-f82d99e4739e42f4abfc37cb97918cfc')]),
    'gbc': dict(
        family='bpoole-cgb',
        size=2048,
        primary='Gameboy_Mat',
        # Every texel no kept face samples is cleared, which removes the fixed
        # Game Pak's label art. The baked battle screenshot on the kept LCD
        # panel is blanked explicitly (primary image UV space: u0, v0, u1, v1).
        blank=[dict(uv=(.2335, .4450, .4090, .6040), colour=LCD, reason='baked game screenshot on the LCD panel')],
        # Glass: black scratched overlay, composited over the LCD (no blending at runtime).
        inset={'Gameboy_Glass': dict(crop=(.030, .034, .220, .205), over=LCD)},
        paint=dict(hue=(55, 110), saturation=.35, value=.30),
        creators=[dict(author='BPoole', licence='CC-BY-4.0',
                       url='https://sketchfab.com/3d-models/game-boy-color-model-a3dad19c800f4c61a931865f14870768')],
    ),
}


def fnv(data):
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xffffffffffffffff
    return h


def rect_pixels(uv, size):
    """UV rectangle (v up) -> PIL box (y down)."""
    u0, v0, u1, v1 = uv
    return (round(u0 * size), round((1 - v1) * size), round(u1 * size), round((1 - v0) * size))


def place(free, width, height):
    """Top-left of the first fully free width x height box (8 px search grid)."""
    table = np.pad(free.astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    rows, cols = free.shape
    for y in range(0, rows - height, 8):
        for x in range(0, cols - width, 8):
            if table[y + height, x + width] - table[y, x + width] - table[y + height, x] + table[y, x] == width * height:
                return x, y, x + width, y + height
    raise ValueError(f'No free atlas space for a {width}x{height} inset')


def coverage(points, triangles, size):
    """Rasterised UV coverage (v up) of the given corner triangles."""
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    for tri in triangles:
        draw.polygon([(points[i][0] * size, (1 - points[i][1]) * size) for i in tri], fill=255)
    return mask


def pack(model):
    config = CONFIG[model]
    work = ROOT / 'build/textured' / model
    parts = json.loads((work / 'parts.json').read_text())
    registration = json.loads((work / 'registration.json').read_text())
    data = np.load(work / 'corners.npz')
    position, normal, uv, triangle = data['position'], data['normal'], data['uv'].astype(np.float64), data['triangle']
    if 'vertex_decimals' in config:
        # Eliminate floating-point noise at shared imported corners. At five
        # decimals this moves PSP geometry by <0.000004 mm, without reducing
        # topology, and retains 16-bit indices for the complete source.
        position=np.round(position,config['vertex_decimals'])
        normal=np.round(normal,config.get('normal_decimals',config['vertex_decimals']))
        uv=np.round(uv,config['vertex_decimals'])
    size = int(os.environ.get('SLOT_ATLAS_SIZE', config['size']))  # review override
    materials = parts['materials']
    primary = materials.index(config['primary'])
    images = parts['images']

    def source_image(name):
        entry = images[name]['image']
        return Image.open(work / 'images' / entry['file']).convert('RGBA')

    corner_material = np.repeat(triangle[:, 1], 3)
    source = source_image(config['primary'])
    if config.get('repeat_u'):
        # Some imported GB faces use repeated U coordinates. Keep the repeated
        # image continuous across U=1, rather than clamping or tearing triangles.
        count=config['repeat_u'];repeated=Image.new('RGBA',(source.width*count,source.height))
        for tile in range(count):repeated.paste(source,(tile*source.width,0))
        uv[:,0]/=count;source=repeated
    if config.get('tiles'):
        # Pack independent material UV spaces before the common coverage/paint
        # pass. No image is enlarged; preserve untouched images in build/.
        side = config.get('tile_size', source.width)
        combined = Image.new('RGBA', (side, side), (*NEUTRAL,255))
        tiled = np.zeros(len(corner_material), bool)
        for name, rect in config['tiles'].items():
            box = rect_pixels(rect, side)
            image = source_image(name)
            width, height = box[2]-box[0], box[3]-box[1]
            if width > image.width or height > image.height:
                raise ValueError('Material tile would enlarge '+name)
            combined.paste(image.resize((width,height),Image.Resampling.LANCZOS), box[:2])
            selected = corner_material == materials.index(name)
            uv[selected] = np.array(rect[:2]) + uv[selected]*np.array((rect[2]-rect[0],rect[3]-rect[1]))
            tiled |= selected
        if set(materials) - set(config['tiles']) - set(config.get('constants', {})) - set(config.get('inset', {})):
            raise ValueError('Unmapped tiled source material')
        corner_material[tiled] = primary
        source = combined
    if source.width < size or source.height < size:
        raise ValueError('Atlas would enlarge the source image')
    atlas = source.resize((size, size), Image.Resampling.LANCZOS)
    # Classify repaintable plastic at full source resolution, then reduce.
    hsv = np.asarray(source.convert('HSV'), dtype=np.float32)
    lo, hi = config['paint']['hue']
    plastic = ((hsv[..., 0] >= lo * 255 / 360) & (hsv[..., 0] <= hi * 255 / 360)
               & (hsv[..., 1] >= config['paint']['saturation'] * 255)
               & (hsv[..., 1] <= config['paint'].get('max_saturation',1) * 255)
               & (hsv[..., 2] >= config['paint']['value'] * 255)
               & (hsv[..., 2] <= config['paint'].get('max_value',1) * 255))
    plastic = Image.fromarray(plastic.astype(np.uint8) * 255).resize((size, size), Image.Resampling.BOX)
    corner_part = np.repeat(triangle[:, 0], 3)
    roles = [p.get('role', '') for p in parts['parts']]
    tris = np.arange(len(position)).reshape(-1, 3)
    painted = coverage(uv, [t for t in tris if roles[corner_part[t[0]]] == 'paint' and corner_material[t[0]] == primary], size)
    used = coverage(uv, [t for t in tris if corner_material[t[0]] == primary], size)
    # Keep a 6 px apron of original texels around used islands for mip filtering;
    # clear everything else (unused or removed-part art) to a neutral grey.
    free = np.asarray(used.filter(ImageFilter.MaxFilter(13))) == 0
    rgba_clear = np.array(atlas)
    rgba_clear[free] = (*NEUTRAL, 255)
    atlas = Image.fromarray(rgba_clear, 'RGBA')
    report = dict(cleared_texels=int(free.sum()), blank=[], inset={})
    draw = ImageDraw.Draw(atlas)
    alpha_cut = Image.new('L', (size, size), 255)
    cut = ImageDraw.Draw(alpha_cut)
    if config.get('blank_lcd'):
        screen=coverage(uv,[t for t in tris if roles[corner_part[t[0]]]=='lcd'],size).filter(ImageFilter.MaxFilter(3))
        atlas.paste((*LCD,255),(0,0,size,size),screen);alpha_cut.paste(0,(0,0,size,size),screen)
        report['blank'].append(dict(reason='source LCD surfaces reserved for live metadata',texels=int(np.count_nonzero(screen))))
    for blank in config['blank']:
        box = rect_pixels(blank['uv'], size)
        draw.rectangle(box, fill=(*blank['colour'], 255))
        cut.rectangle(box, fill=0)
        report['blank'].append(dict(box=box, reason=blank['reason']))
    uv_atlas = uv.copy()
    for name,linear in config.get('constants',{}).items():
        # Original uniform material swatches; no source image is enlarged.
        index=materials.index(name);box=place(free,16,16)
        free[box[1]:box[3],box[0]:box[2]]=False
        srgb=[v*12.92 if v<=.0031308 else 1.055*v**(1/2.4)-.055 for v in linear]
        draw.rectangle(box,fill=(*[round(v*255) for v in srgb],255));cut.rectangle(box,fill=0)
        uv_atlas[corner_material==index]=((box[0]+8)/size,1-(box[1]+8)/size)
        report.setdefault('constants',{})[name]=dict(box=box,linear=linear)
    for name, inset in config.get('inset', {}).items():
        index = materials.index(name)
        image = source_image(name)
        cw, ch = image.size
        crop = image.crop(rect_pixels(inset['crop'], cw))
        # Same reduction as the primary image; never enlarged.
        w, h = max(1, round(crop.width * size / source.width)), max(1, round(crop.height * size / source.height))
        box = place(free, w + 8, h + 8)
        box = (box[0] + 4, box[1] + 4, box[0] + 4 + w, box[1] + 4 + h)
        free[box[1] - 4:box[3] + 4, box[0] - 4:box[2] + 4] = False
        crop = crop.resize((w, h), Image.Resampling.LANCZOS)
        under = Image.new('RGBA', crop.size, (*inset['over'], 255))
        under.alpha_composite(crop)
        atlas.paste(under, box[:2])
        cut.rectangle(box, fill=0)
        selected = corner_material == index
        c0, c1 = np.array(inset['crop'][:2]), np.array(inset['crop'][2:])
        d0 = np.array((box[0] / size, 1 - box[3] / size))
        d1 = np.array((box[2] / size, 1 - box[1] / size))
        local = (uv[selected] - c0) / (c1 - c0)
        if local.min() < -.001 or local.max() > 1.001:
            raise ValueError(f'{model}: {name} UVs leave the inset crop')
        # Half-texel inset keeps bilinear samples inside the composited crop.
        half = .5 / size
        uv_atlas[selected] = (d0 + half) + np.clip(local, 0, 1) * (d1 - d0 - 2 * half)
        report['inset'][name] = dict(box=box, source_crop=inset['crop'])
    others = set(corner_material.tolist()) - {primary} - {materials.index(n) for n in config.get('inset', {})} - {materials.index(n) for n in config.get('constants', {})}
    if others:
        raise ValueError(f'{model}: unmapped materials {[materials[i] for i in others]}')
    # The paint coverage keeps the same apron as the colour so bilinear/mip
    # samples at UV seams do not fade back to the original plastic.
    apron = np.asarray(painted.filter(ImageFilter.MaxFilter(13)))
    alpha = np.minimum(np.minimum(np.asarray(plastic), apron), np.asarray(alpha_cut))
    alpha = np.where(free, 0, alpha).astype(np.uint8)
    rgba = np.array(atlas)
    rgba[..., 3] = alpha
    from ..publication.derivatives import approved_albedo
    rgba = approved_albedo(ROOT, 'theme/art-book-slot/_slot/consoles/' + model + '/model.albedo.png', rgba)
    alpha = rgba[..., 3]
    luminance = rgba[..., :3].astype(np.float32) @ np.array([.299, .587, .114], np.float32) / 255
    paint_luma = float(np.median(luminance[alpha > 127])) if (alpha > 127).sum() > 1000 else .55
    # Native vertices: GL texture rows run top-down, so t = 1 - v.
    t = np.column_stack((uv_atlas[:, 0], 1 - uv_atlas[:, 1])).astype(np.float32)
    px = np.clip((t * size).astype(int), 0, size - 1)
    colour = rgba[px[:, 1], px[:, 0], :3].astype(np.float32) / 255
    lcd = np.array([roles[p] == 'lcd' for p in corner_part])
    colour[lcd] = np.array(LCD, np.float32) / 255
    weight = np.where(rgba[px[:, 1], px[:, 0], 3] > 127, 192, 0).astype(np.uint8)
    unique, lookup, indices, uvs, weights = [], {}, [], [], []
    for i in range(len(position)):
        vertex = struct.pack('<9f', *position[i], *normal[i], *colour[i])
        key = vertex + struct.pack('<2f', *t[i])
        if key not in lookup:
            lookup[key] = len(unique)
            unique.append(vertex)
            uvs.append(t[i])
            weights.append(int(weight[i]))
        indices.append(lookup[key])
    if len(unique) > 65535:
        raise ValueError(f'{model}: {len(unique)} vertices exceed the 16-bit native index format')
    moving = [i for i, p in enumerate(parts['parts']) if p.get('moving')]
    door = next((3 * k for k in range(len(triangle)) if triangle[k, 0] in moving), len(indices))
    raw = b''.join(unique)
    index_bytes = struct.pack('<%dH' % len(indices), *indices)
    target = SLOT / 'consoles' / model
    target.mkdir(parents=True, exist_ok=True)
    (target / 'model.mesh').write_bytes(struct.pack('<8sIII', b'SCTOON2\0', len(unique), len(indices), door) + raw + index_bytes)
    albedo = Image.fromarray(rgba, 'RGBA')
    albedo.save(target / 'model.albedo.png', optimize=True)
    decoded = np.asarray(Image.open(target / 'model.albedo.png').convert('RGBA'))
    if not np.array_equal(decoded, rgba):
        raise RuntimeError('PNG round trip changed albedo pixels')
    # The loader hashes the PNG's bytes (cheaper than its 16 MB of pixels).
    file_hash = fnv((target / 'model.albedo.png').read_bytes())
    uv_bytes = np.array(uvs, np.float32).tobytes()
    (target / 'model.texture').write_bytes(struct.pack('<8sIIIfQQQ', b'SCTEX003', len(unique), size, size, paint_luma,
                                                      fnv(raw), fnv(index_bytes), file_hash) + uv_bytes)
    (target / 'paint.mask').write_bytes(struct.pack('<8sIQ', b'SCPAINT1', len(unique), fnv(raw)) + bytes(weights))
    info = dict(vertices=len(unique), indices=len(indices), triangles=len(indices) // 3, door_first=door,
                vertex_decimals=config.get('vertex_decimals'),
                normal_decimals=config.get('normal_decimals'),
                texture=dict(format='SCTEX003', size=[size, size], paint_luma=paint_luma,
                             albedo_sha256=hashlib.sha256((target / 'model.albedo.png').read_bytes()).hexdigest(),
                             painted_texels=int((alpha > 127).sum()), lighting='albedo + simple lighting; no PBR/normal maps'),
                licence=' + '.join(sorted({'MIT'} | {c['licence'] for c in config['creators']})),
                source='Registered textured source adapted by tools/consolebuild/' + registration.get('adapter', model),
                creators=config['creators'], atlas=report,
                mesh_sha256=hashlib.sha256((target / 'model.mesh').read_bytes()).hexdigest())
    (target / 'mesh-info.json').write_text(json.dumps(info, indent=2) + '\n', newline='\n')
    (target / 'registration.json').write_text(json.dumps(registration, indent=2) + '\n', newline='\n')
    family = ROOT / 'third_party/models' / config['family']
    family.mkdir(parents=True, exist_ok=True)
    source_images = {name: entry['image'] for name, entry in images.items() if entry['image']}
    (family / 'source.json').write_text(json.dumps(dict(
        registration, source_images=source_images, atlas=report,
        prepared=dict(mesh_sha256=info['mesh_sha256'], albedo_sha256=info['texture']['albedo_sha256'],
                      vertices=info['vertices'], triangles=info['triangles']),
        reproduction=f'tools/consolebuild/textured.sh {registration.get("adapter")} SOURCE {model}'),
        indent=2) + '\n', newline='\n')
    native_header()
    if model == 'dreamcast':
        from .dreamcast import native_header as optical_header
        optical_header()
    if model == 'psx':
        from .ps1 import native_header as psx_header
        psx_header()
    print(f'{model}: {len(unique)} vertices, {len(indices)//3} triangles, atlas {size}px, paint luma {paint_luma:.3f}')
    return info


def native_header():
    lines = ['/* Generated by tools.consolebuild.textured from registered textured sources. MIT. */']
    gbc = SLOT / 'consoles/gbc/registration.json'
    label = json.loads(gbc.read_text())['cart_label_native'] if gbc.exists() else -6.5 * (168 / 78)
    lines.append(f'static const double cgb_cart_label_native = {label:.14g};')
    gb=SLOT/'consoles/gb/registration.json'
    dmg_label=json.loads(gb.read_text())['cart_label_native'] if gb.exists() else -13*(168/90)
    lines.append(f'static const double dmg_authored_cart_label_native = {dmg_label:.14g};')
    psp=SLOT/'consoles/psp/registration.json'
    registration=json.loads(psp.read_text()) if psp.exists() else {}
    for name,default in [('hinge_native',[0,-33.6*480/169.4,-8.5*480/169.4]),('umd_label_native',[0,0,-23])]:
        lines.append('static const double psp_authored_'+name+'[3] = {'+','.join(f'{v:.14g}' for v in registration.get(name,default))+'};')
    (ROOT / 'tools/slotlaunch/textured-data.h').write_text('\n'.join(lines) + '\n', newline='\n')
    ds_lid_header()
    ags_lid_header()


def ds_lid_header():
    """A registered textured DS Lite supplies the lid axis and presentation angle."""
    nds = SLOT / 'consoles/nds/registration.json'
    if not (nds.exists() and (SLOT / 'consoles/nds/model.texture').exists()):
        return
    registration = json.loads(nds.read_text())
    target = ROOT / 'tools/slotlaunch/lid-data.h'
    hinge = 'static const double ds_lid_hinge[]={' + ','.join(f'{v:.9f}' for v in registration['hinge_native']) + '};'
    opened = f'static const double ds_lid_open_radians={math.radians(registration["open_degrees"]):.12f};'
    lines = [hinge if line.startswith('static const double ds_lid_hinge') else
             opened if line.startswith('static const double ds_lid_open_radians') else line
             for line in target.read_text().splitlines()]
    target.write_text('\n'.join(lines) + '\n', newline='\n')


def ags_lid_header():
    """A registered textured GBA SP supplies the packaged lid axis and opening angle."""
    gba = SLOT / 'consoles/gba/registration.json'
    if not (gba.exists() and (SLOT / 'consoles/gba/model.texture').exists()):
        return
    registration = json.loads(gba.read_text())
    target = ROOT / 'tools/slotlaunch/lid-data.h'
    hinge = 'static const double ags_lid_hinge[]={' + ','.join(f'{v:.9f}' for v in registration['hinge_native']) + '};'
    opened = f'static const double ags_lid_open_radians={registration["open_radians"]:.12f};'
    lines = [hinge if line.startswith('static const double ags_lid_hinge') else
             opened if line.startswith('static const double ags_lid_open_radians') else line
             for line in target.read_text().splitlines()]
    target.write_text('\n'.join(lines) + '\n', newline='\n')


def apply_specs(specs):
    """Registered textured sources replace their console's seating constants."""
    for name, spec in specs.items():
        path = SLOT / 'consoles' / name / 'registration.json'
        if path.exists() and (SLOT / 'consoles' / name / 'model.texture').exists():
            spec.update(json.loads(path.read_text()).get('spec', {}))


def body(model, probe):
    """Fallback sprite from the native renderer's own browse pose (2x, reduced).

    Run under Linux with the host probe (tools/frontend/tests/build_probe.sh)."""
    import os, subprocess, tempfile
    with tempfile.TemporaryDirectory() as folder:
        raw = Path(folder) / 'browse.bmp'
        env = dict(os.environ, SLOT_MODEL_STYLE='realistic', SLOT_CONSOLE_COLOR='original', SLOT_GBA_SP='graphicsgeek')
        run = subprocess.run(['sh', str(ROOT / 'tools/frontend/tests/run_probe.sh'), str(probe), str(SLOT), str(raw), model, 'browse'],
                             env=env, capture_output=True, text=True)
        if run.returncode or 'validated UV/albedo' not in Path('/tmp/art-book-slot-launch/animation.log').read_text()[-4000:]:
            raise RuntimeError('Textured browse render failed: ' + run.stdout + run.stderr)
        with Image.open(raw) as image:
            image.convert('RGBA').resize((720, 480), Image.Resampling.LANCZOS).save(SLOT / 'consoles' / model / 'body.png')
    print(model, 'body.png from the native renderer')


if __name__ == '__main__':
    arguments = sys.argv[1:]
    if arguments[:1] == ['--body']:
        for name in arguments[2:]:
            body(name, Path(arguments[1]))
    else:
        for name in arguments or list(CONFIG):
            pack(name)
