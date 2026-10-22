"""Local model/camera editor. Run python tools/tabletop/editor/server.py.

Serves only editor files and the explicit model roots on loopback. Save writes
a portable JSON profile and the native renderer's matching layout.scene. No
original model, firmware or game is changed. Upload explicitly deploys a saved
scene through the device snapshot/restore/audit transaction.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import secrets
import struct
import tarfile
import threading
import time
import sys
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.tabletop.editor.settings import TVS, TABLES, FIELDS, validate_extras, native_extras
from tools.tabletop.editor import room as room_profiles
from tools.tabletop.editor.upload import UPLOADS, THEME_NAME, DEVICE_LAYOUTS
from tools.slot_theme import LEGACY, DEVICE_THEMES
HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'build/tabletop'
ASSETS = BUILD / 'assets'
VENDOR = BUILD / 'editor-vendor'
CARTRIDGE_COUNT = 12
NAMES = ['table', 'tv', 'console', 'status'] + ['cart' + str(i) for i in range(CARTRIDGE_COUNT)]
# Consoles the tabletop renderer supports: native units per mm (console and media,
# as SlotTabletop.cpp units()) and the cartridge label surface/crop it draws.
SYSTEMS = {
    'snes': dict(units=1.6, label='media-label.mesh', crop=[42 / 360, 22 / 245, 276 / 360, 99 / 245]),
    'n64': dict(units=1.5, label='media-label.mesh', crop=[96 / 360, 22 / 241, 168 / 360, 197 / 241]),
    # No source label surface: the flat recessed well from tools/slotlaunch/media-specs.h.
    'nes': dict(units=196 / 120, quad=[16.0927152, 20.4462687, 28.013245, 44.8626866, 9.03],
                crop=[122 / 304, 4 / 337, 141 / 304, 226 / 337]),
    'md': dict(units=224 / 109, quad=[0.302777778, 2.39316239, 39.3611111, 31.4102564, 8.03],
               crop=[51 / 360, 22 / 270, 260 / 360, 210 / 270]),
    # Generated annular disc (radius, thickness mm) with its circular print, as SlotTabletop.cpp.
    'psx': dict(units=1.6, disc=[60, 1.2], crop=[0, 0, 1, 1]),
    'gb': dict(units=1.8666667, quad=[0, -4.8791, 20.92095, 18.7022, 3.875], crop=[47/312, 97/337, 218/312, 193/337]),
    'gbc': dict(units=2.1538462, quad=[0, -5, 20.9, 18.6, 3.72], crop=[48/312, 99/337, 216/312, 191/337]),
    'gba': dict(units=224/82, label='media-label.mesh', crop=[50/360, 52/212, 260/360, 135/212]),
    'nds': dict(units=2.75, consoleUnits=3.037594, quad=[0, 1.13569322, 14.1580645, 14.7123894, 1.73], crop=[23/312, 17/341, 266/312, 285/341]),
    'psp': dict(units=2.8335301, tableRotation=[90, 0, 0], quad=[0, 0, 33.019, 33.019, 5.98/2.8335301+.05], crop=[0, 0, 1, 1], cutout=True),
    'pico8': dict(units=2.2, label='media-label.mesh', crop=[26/264, 41/338, 205/264, 277/338]),
}
SAVED = ROOT / 'scene-layouts/snes-panasonic.json'
# "Save for all TV / handheld consoles" targets (handhelds as in the tabletop renderer).
GROUPS = {'tv': ('snes', 'n64', 'nes', 'md', 'psx'), 'handheld': ('gb', 'gbc', 'gba', 'nds', 'psp', 'pico8')}
TOKEN = secrets.token_urlsafe(24)
SAVE_LOCK = threading.RLock()


def slot_root():
    """The retained local assets shared by both device themes."""
    return ROOT / 'theme' / LEGACY / '_slot'


def saved_path(system, tv='panasonic'):
    return ROOT / 'scene-layouts' / (system + '-' + tv + '.json')


def native_path(system, tv='panasonic'):
    return ASSETS / 'layouts' / (system + '-' + tv + '.scene')


def query_tv(query):
    tv = (parse_qs(query).get('tv') or ['panasonic'])[0]
    if tv not in TVS:
        raise ValueError('Unsupported television')
    return tv


def console_path(system):
    local = slot_root() / 'local-models/consoles/gba/model.mesh'
    return local if system == 'gba' and local.is_file() else slot_root() / 'consoles' / system / 'model.mesh'


def query_system(query):
    system = (parse_qs(query).get('system') or ['snes'])[0]
    if system not in SYSTEMS:
        raise ValueError('Unsupported tabletop console')
    return system


def console_bottom(system):
    """Base height of the console mesh in mm below its origin (negative)."""
    bounds = mesh_bounds(console_path(system))
    return (-bounds[1][2] if system == 'psp' else bounds[0][1]) / SYSTEMS[system].get('consoleUnits', SYSTEMS[system]['units'])


def media_bottom(system):
    """Lowest face (mm, shell z) of the console's media as it lies on the table."""
    spec = SYSTEMS[system]
    if 'disc' in spec:
        return -spec['disc'][1] / 2
    return mesh_bounds(slot_root() / 'consoles' / system / 'media.mesh')[0][2] / spec['units']


def adopt(profile, system):
    """A SNES-authored layout for another console, as the renderer applies it:
    the same console node, lifted so this console's base sits where the SNES's did,
    and cartridge nodes lifted/lowered so this console's media rest on the table."""
    p = validate(dict(profile, system='snes'))
    if system != 'snes':
        console = p['objects']['console']
        console['position'][1] += console_bottom('snes') - console_bottom(system)
        rest = media_bottom('snes') - media_bottom(system)
        for name in NAMES[4:]:
            if name in p['objects']:
                p['objects'][name]['position'][1] += rest
        p['system'] = system
    return p


def adopt_tv(profile, tv):
    if profile['tv'] == tv:
        return profile
    import copy
    p = copy.deepcopy(profile)
    old = json.loads((ASSETS / p['tv'] / 'scene.json').read_text())
    new = json.loads((ASSETS / tv / 'scene.json').read_text())
    # Match native fallback: translate the new cabinet's front along the authored TV's local Z.
    rx, ry, rz = [math.radians(v) for v in p['objects']['tv']['rotation']]
    dz = old['bounds'][1][2] - new['bounds'][1][2]
    direction = [math.sin(ry)*math.cos(rx), -math.sin(rx), math.cos(ry)*math.cos(rx)]
    node = p['objects']['tv']
    node['position'] = [v + dz*d for v, d in zip(node['position'], direction)]
    p['objects']['status'] = dict(position=[0, new['bounds'][1][1]+2, new['glass'][1][2]-28], rotation=[0, 0, 0])
    p['tv'] = tv
    return p


def retarget(profile, system):
    """This layout for another console, as adopt() does for the SNES: the console node is
    lifted so the new console's base sits where the old one's did and the carts so their
    media rest on the table; the console/cartridge cameras follow those lifts."""
    import copy
    p = copy.deepcopy(validate(profile))
    source = p['system']
    if source != system:
        lift = console_bottom(source) - console_bottom(system)
        rest = media_bottom(source) - media_bottom(system)
        p['objects']['console']['position'][1] += lift
        for name in NAMES[4:]:
            if name in p['objects']:
                p['objects'][name]['position'][1] += rest
        for key, delta in (('console', lift), ('cartridge', rest)):
            cam = p.get('cameras', {}).get(key)
            if cam:
                cam['position'][1] += delta
                cam['target'][1] += delta
        p['system'] = system
    return validate(p)


def export_plan(system, tv, group):
    if group not in GROUPS:
        raise ValueError('Choose TV or handheld consoles')
    return [dict(system=s, saved=saved_path(s, tv).is_file(), current=s == system) for s in GROUPS[group]]


def export_profile(profile, group):
    """Save the layout for every console in the group (same TV); replaced profiles keep
    their previous version in scene-layouts/history (save_profile)."""
    p = validate(profile)
    results = []
    for item in export_plan(p['system'], p['tv'], group):
        save_profile(p if item['current'] else retarget(p, item['system']))
        results.append(dict(system=item['system'], replaced=item['saved'], current=item['current']))
    return results


def layout_pair(key):
    """'gba-pvm' -> ('gba', 'pvm') for a supported console and TV."""
    system, _, tv = str(key).partition('-')
    if system not in SYSTEMS or tv not in TVS:
        raise ValueError('Unsupported layout: ' + str(key))
    return system, tv


def layout_entry(system, tv):
    """A saved layout as an upload installs it: the editor's twelve-cartridge native text."""
    path = saved_path(system, tv)
    source = path.read_bytes()
    profile = expand_profile(json.loads(source))
    if (profile['system'], profile['tv']) != (system, tv):
        raise ValueError(path.name + ' holds another console or TV')
    return dict(system=system, tv=tv, profile=profile, native=native_text(profile), source=source, json=str(path))


def saved_layouts():
    """Every saved SYSTEM-TV layout, with the hash of the native file upload would install."""
    rows = []
    for system in SYSTEMS:
        for tv in TVS:
            if saved_path(system, tv).is_file():
                row = dict(key=system + '-' + tv, system=system, tv=tv)
                try:
                    row['sha256'] = hashlib.sha256(layout_entry(system, tv)['native'].encode('utf-8')).hexdigest()
                except (ValueError, KeyError, TypeError, OSError) as error:
                    row['error'] = str(error)
                rows.append(row)
    for key in ['room']+['home-'+tv for tv in TVS]:
        if (ROOT/'scene-layouts'/(key+'.json')).is_file():
            row=dict(key=key,kind='room' if key=='room' else 'home')
            try:row['sha256']=hashlib.sha256(scene_entry(key)['native'].encode()).hexdigest()
            except (ValueError,KeyError,TypeError,OSError) as error:row['error']=str(error)
            rows.append(row)
    return rows


def scene_entry(key):
    if key=='room' or key in ['home-'+tv for tv in TVS]:
        path=ROOT/'scene-layouts'/(key+'.json');source=path.read_bytes();profile=room_profiles.validate(json.loads(source))
        if room_profiles.profile_key(profile)!=key:raise ValueError('Saved scene identity mismatch')
        return dict(profile=profile,native=room_profiles.native_text(profile),source=source,json=str(path))
    return layout_entry(*layout_pair(key))


def device_layouts(texts=False):
    """Read-only, ONE SSH call: every runtime layout on the device (hash and optionally
    text) plus whether an upload could start now. Nothing on the device changes."""
    from tools.tabletop.device_probe import Remote
    source = '''import json,hashlib,sys
from pathlib import Path
base=Path(BASE)
state=dict(theme=DEFAULT_THEME)
try:
    sys.path.insert(0,'/userdata/system/slot-dev')
    import esdev
    state['themeSet']=esdev.get('ThemeSet')
    if state['themeSet'] in THEMES:
        state['theme']=state['themeSet']
        base=Path('/userdata/themes')/state['theme']/'_slot/tabletop/layouts'
    state['frontend']=bool(esdev.es_pid())
    state['gameRunning']=json.loads(esdev.api('/runningGame'))!={'msg':'NO GAME RUNNING'} if state['frontend'] else None
except BaseException as error:
    state['statusError']=str(error) or type(error).__name__
layouts={}
for p in (sorted(list(base.glob('*.scene'))+list(base.glob('room.world'))) if base.is_dir() else []):
    data=p.read_bytes()
    layouts[p.stem]=dict(sha256=hashlib.sha256(data).hexdigest(),text=data.decode('utf-8','replace') if TEXTS else None)
state['layouts']=layouts
print(json.dumps(state))'''
    source = source.replace('BASE', repr(DEVICE_LAYOUTS)).replace('TEXTS', repr(bool(texts)))
    source = source.replace('DEFAULT_THEME', repr(LEGACY)).replace('THEMES', repr(DEVICE_THEMES))
    state = json.loads(Remote().python(source, timeout=30))
    return state


def upload_plan(read_device=True):
    """Rows for the Upload… dialog: saved layouts and, from one device read, their hashes there."""
    result = dict(layouts=saved_layouts(), theme=THEME_NAME)
    if read_device:
        try:
            device = device_layouts()
            result['theme'] = device.get('theme', THEME_NAME)
            device['layouts'] = {key: dict(sha256=value['sha256']) for key, value in device['layouts'].items()}
            result['device'] = device
        except Exception as error:  # ssh/device failures are reported, never fatal
            detail = error.stderr.decode('utf-8', 'replace').strip() if getattr(error, 'stderr', None) else str(error)
            result['device'] = dict(error='Cannot read your device: ' + (detail or type(error).__name__))
    return result


def device_import():
    """Device layouts that differ from the saved ones (or are not saved here), parsed as
    editor profiles for the browser to keep as undoable drafts. Read-only."""
    device = device_layouts(texts=True)
    rows = []
    for key, value in sorted(device['layouts'].items()):
        try:
            system, tv = layout_pair(key)
        except ValueError:
            rows.append(dict(key=key, status='unsupported'))
            continue
        try:
            profile = expand_profile(parse_native(value['text'], system, tv))
        except (ValueError, KeyError, TypeError, IndexError) as error:
            rows.append(dict(key=key, system=system, tv=tv, status='unreadable', error=str(error)))
            continue
        status = 'not saved'
        if saved_path(system, tv).is_file():
            try:
                status = 'same' if layout_entry(system, tv)['native'] == native_text(profile) else 'differs'
            except (ValueError, KeyError, TypeError):
                status = 'differs'
        rows.append(dict(key=key, system=system, tv=tv, status=status, sha256=value['sha256'],
                         profile=profile if status != 'same' else None))
    return dict(layouts=rows, theme=device.get('theme', THEME_NAME), themeSet=device.get('themeSet'))


def batch_entries(keys, expect=None):
    """Saved layouts for one batch upload; expect ({key: sha256} from the dialog) refuses a
    layout saved again since the dialog compared it with the device."""
    entries = []
    for key in keys:
        entry = scene_entry(key)
        if expect is not None and hashlib.sha256(entry['native'].encode('utf-8')).hexdigest() != expect.get(key):
            raise ValueError(key + ' was saved again after the list was read; reopen Upload…')
        entries.append(entry)
    return entries


def device_layout(system, tv):
    """Read-only: the layout the device renders for this console/TV, if it has one."""
    device = device_layouts(texts=True)
    layouts = list(device['layouts'])
    state = device['layouts'].get(system + '-' + tv)
    if state is None:
        return dict(found=False, layouts=layouts)
    profile = expand_profile(parse_native(state['text'], system, tv))
    saved = saved_path(system, tv)
    same = saved.is_file() and native_text(json.loads(saved.read_text(encoding='utf-8'))) == native_text(profile)
    return dict(found=True, profile=profile, sha256=state['sha256'], layouts=layouts, matchesSaved=same)

def device_room(kind,tv):
    """Read a room/home derivative as an undoable draft; never save it here."""
    if kind not in ('room','home') or tv not in TVS:raise ValueError('Choose room or home and a supported TV')
    device=device_layouts(texts=True);key='room' if kind=='room' else 'home-'+tv
    state=device['layouts'].get(key)
    if state is None:return dict(found=False,layouts=list(device['layouts']),theme=device.get('theme'))
    profile=room_profiles.parse_world(state['text']) if kind=='room' else room_profiles.parse_home(state['text'],tv)
    saved=ROOT/'scene-layouts'/(key+'.json');same=False
    if saved.is_file():same=room_profiles.native_text(json.loads(saved.read_text(encoding='utf-8')))==room_profiles.native_text(profile)
    return dict(found=True,profile=profile,sha256=state['sha256'],matchesSaved=same,theme=device.get('theme'))


def vendor():
    if (VENDOR / 'ready.json').is_file():
        return
    version = '0.170.0'
    with urlopen('https://registry.npmjs.org/three/' + version, timeout=30) as response:
        package = json.load(response)
    with urlopen(package['dist']['tarball'], timeout=30) as response:
        data = response.read()
    integrity = package['dist']['integrity'].removeprefix('sha512-')
    if base64.b64encode(hashlib.sha512(data).digest()).decode() != integrity:
        raise ValueError('Three.js package integrity mismatch')
    wanted = ['build/three.module.js', 'build/three.core.js', 'examples/jsm/controls/OrbitControls.js',
              'examples/jsm/controls/TransformControls.js', 'LICENSE']
    VENDOR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for name in wanted:
            try:
                source = archive.extractfile('package/' + name)
            except KeyError:
                if name == 'build/three.core.js':
                    continue
                raise
            (VENDOR / Path(name).name).write_bytes(source.read())
    (VENDOR / 'ready.json').write_text(json.dumps(dict(version=version, sha256=hashlib.sha256(data).hexdigest())))


def read_profile(path):
    return parse_native(path.read_text())


def parse_native(text, system='snes', tv='panasonic'):
    """A native SLOTLAYOUT1 scene (as installed on the device) as an editor profile."""
    result = dict(version=1, system=system, tv=tv, objects={})
    lines = text.splitlines()
    if not lines or lines[0] != 'SLOTLAYOUT1':
        raise ValueError('Invalid native layout')
    for line in lines[1:]:
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'table_asset':
            result.setdefault('table', dict(scale=[1, 1, 1]))['model'] = fields[1]
            continue
        name, values = fields[0], list(map(float, fields[1:]))
        if name == 'viewport':
            result['viewport'] = dict(width=int(values[0]), height=int(values[1]))
        elif name == 'camera':
            result['camera'] = dict(position=values[:3], target=values[3:6], fov=values[6])
        elif name.startswith('view_'):
            result.setdefault('cameras', {})[name[5:]] = dict(position=values[:3], target=values[3:6], fov=values[6])
        elif name == 'transition':
            result['transitionSeconds'] = values[0]
        elif name == 'browse_view':
            from tools.tabletop.editor.settings import VIEWS
            result['browseView'] = VIEWS[int(values[0])]
        elif name == 'table_scale':
            result.setdefault('table', dict(model='table'))['scale'] = values
        elif name.startswith('display_'):
            enabled, layout, scale, padding, mask, bg, fg, accent = values
            result.setdefault('displays', {})[name[8:]] = dict(enabled=bool(enabled), layout=('split', 'text', 'artwork')[int(layout)],
                    textScale=scale, padding=padding, fields={key: bool(int(mask) & (1 << i)) for i, key in enumerate(FIELDS)},
                    background='#%06x' % int(bg), foreground='#%06x' % int(fg), accent='#%06x' % int(accent))
        else:
            result['objects'][name] = dict(position=values[:3], rotation=values[3:])
    if 'cameras' in result:
        result['cameras']['all'] = result['camera']
    return validate(result)


def vector(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 10000 for v in value):
        raise ValueError('Use three finite values within +/-10000')
    return list(map(float, value))


def validate(value):
    if value.get('version') != 1 or value.get('system') not in SYSTEMS or value.get('tv') not in TVS:
        raise ValueError('Unsupported scene profile')
    viewport = value['viewport']
    if (viewport.get('width'), viewport.get('height')) not in ((720, 480), (720, 540)):
        raise ValueError('Choose 3:2 or 4:3')
    camera = value['camera']
    eye, target = vector(camera['position']), vector(camera['target'])
    fov = camera['fov']
    if type(fov) not in (int, float) or not math.isfinite(fov) or not 5 <= fov <= 110 or sum((a - b) ** 2 for a, b in zip(eye, target)) < 100:
        raise ValueError('Invalid camera FOV or target distance')
    # Original eight-cartridge profiles remain valid, including archived layouts.
    names = NAMES if len(value['objects']) == len(NAMES) else NAMES[:12]
    if set(value['objects']) != set(names):
        raise ValueError('Scene must contain table, TV, console, status and eight or twelve cartridges')
    nodes = {name: dict(position=vector(value['objects'][name]['position']), rotation=vector(value['objects'][name]['rotation'])) for name in names}
    return dict(version=1, system=value['system'], tv=value['tv'], viewport=dict(viewport),
                camera=dict(position=eye, target=target, fov=float(fov)), objects=nodes, **validate_extras(value, vector))


def expand_profile(profile):
    """Add four independent carts without changing any authored pose or camera."""
    p = validate(profile)
    if 'cart8' not in p['objects']:
        x, y, z = p['objects']['cart0']['position']
        for i, (dx, dz, yaw) in enumerate(((0, -500, 10), (170, -500, -12),
                                         (0, -700, 20), (170, -700, -7)), start=8):
            p['objects']['cart' + str(i)] = dict(position=[x + dx, y, z + dz], rotation=[-90, yaw, 0])
    return p


def native_text(profile):
    p = validate(profile)
    def nums(values):
        return ' '.join(format(v, '.9g') for v in values)
    lines = ['SLOTLAYOUT1', 'viewport ' + nums([p['viewport']['width'], p['viewport']['height']]),
             'camera ' + nums(p['camera']['position'] + p['camera']['target'] + [p['camera']['fov']])]
    lines.extend(name + ' ' + nums(node['position'] + node['rotation']) for name, node in p['objects'].items())
    lines.extend(native_extras(p))
    return '\n'.join(lines) + '\n'


def mesh_bounds(path):
    raw = path.read_bytes()
    n = struct.unpack_from('<I', raw, 8)[0]
    stride = 36 if raw[:8] == b'SCTOON2\0' else 44
    vertices = [struct.unpack_from('<3f', raw, 20 + stride * i) for i in range(n)]
    return [[min(v[i] for v in vertices) for i in range(3)], [max(v[i] for v in vertices) for i in range(3)]]


def manifest(system='snes', tv='panasonic'):
    glyphs = (ROOT / 'tools/frontend/overlay/es-app/src/components/SlotStatusGlyphs.h').read_text()
    glyphs = {m[0]: dict(advance=int(m[1]), width=int(m[2]), rows=list(map(int, m[3].split(','))))
              for m in re.findall(r"\{'(.)',(\d+),(\d+),\{([\d,]+)\}\}", glyphs)}
    spec = SYSTEMS[system]
    # Named cartridge packages may supply their own curved/wrapped label mesh.
    # Follow the active asset like the native renderer; keep the historical
    # quad fallback when restoring a prior cartridge package.
    label_file = slot_root() / 'consoles' / system / 'media-label.mesh'
    label_name = 'media-label.mesh' if label_file.is_file() else spec.get('label')
    media = dict(shell=None if 'disc' in spec else '/assets/native/%s/media.mesh' % system, units=spec['units'], crop=spec['crop'],
                 label='/assets/native/%s/%s' % (system, label_name) if label_name else None,
                 quad=spec.get('quad'), disc=spec.get('disc'), cutout=spec.get('cutout', False))
    screens = (ROOT / 'tools/frontend/overlay/es-app/src/components/SlotScreens.h').read_text()
    # Generated source registration: active LCD corners in console native units.
    screen_match = re.search(r'\{"' + system + r'",(\d+),[^\n]+', screens)
    lcd = []
    if screen_match:
        vals = [float(v) for v in re.findall(r'(-?\d+(?:\.\d+)?)f', screen_match[0].split('},{{')[-1])]
        lcd = [vals[i*12:(i+1)*12] for i in range(int(screen_match[1]))]
    console = console_path(system)
    console_url = '/assets/local/consoles/gba/model.mesh' if 'local-models' in console.parts else '/assets/native/%s/model.mesh' % system
    pose = console.with_name('model-info.json')
    if system == 'gba' and pose.is_file():
        local = json.loads(pose.read_text())
        if 'lcd' in local:
            # Local source order TL, TR, BR, BL is registered by local_sp.py.
            lcd = [[v for point in local['lcd'] for v in point]]
    saved_layouts = sorted(p.stem for p in (ROOT / 'scene-layouts').glob('*.json'))
    return dict(token=TOKEN, project=str(ROOT), editorRevision=12, cartridgeCount=CARTRIDGE_COUNT, savedLayouts=saved_layouts,
                groups={key: list(value) for key, value in GROUPS.items()}, native='/assets/native/', prepared='/assets/prepared/',
                faces='/assets/faces/%s/' % system, system=system, systems=list(SYSTEMS), units=spec['units'], media=media,
                saved=saved_path(system, tv).is_file(), glyphs=glyphs, tv=tv, tvs=list(TVS), tables=TABLES,
                console=console_url, consoleUnits=spec.get('consoleUnits', spec['units']), tableRotation=spec.get('tableRotation', [0, 0, 0]), lcd=lcd,
                consoleBounds=mesh_bounds(console))


def surface_library():
    """Room surface textures: the built-in library, then the user's own imports."""
    library = ASSETS / 'surfaces' / 'library.json'
    entries = json.loads(library.read_text(encoding='utf-8'))['textures'] if library.is_file() else []
    for entry in entries:
        entry['own'] = False
    builtin = {entry['name'] for entry in entries}
    own = ROOT / 'scene-layouts/surfaces'
    for path in sorted(own.glob('*.png')) if own.is_dir() else []:
        if room_profiles.TEXTURE_NAME.fullmatch(path.stem) and path.stem not in builtin:
            entries.append(dict(name=path.stem, label=path.stem.removeprefix('own-').replace('-', ' ').capitalize(), tile=1000,
                                surfaces=list(room_profiles.SURFACES), own=True))
    return dict(textures=entries)


def import_surface(body):
    """Saves an image as the user's own room texture: centre square, 1024 px PNG (seamless
    tiling is the image's own property). Returns its library entry."""
    from PIL import Image
    label = str(body.get('label', '')).strip()
    slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')[:40]
    if not slug:
        raise ValueError('Name the texture first')
    name = 'own-' + slug
    match = re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)', body.get('image', ''))
    if not match:
        raise ValueError('Choose a PNG, JPEG or WebP image')
    with Image.open(io.BytesIO(base64.b64decode(match[2]))) as source:
        image = source.convert('RGB')
    side = min(image.size)
    if side < 64:
        raise ValueError('The image is too small (at least 64 px)')
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((1024, 1024), Image.LANCZOS)
    folder = ROOT / 'scene-layouts/surfaces'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (name + '.png')
    temporary = target.with_suffix('.' + secrets.token_hex(4) + '.tmp')
    image.save(temporary, 'PNG', optimize=True)
    os.replace(temporary, target)
    return next(entry for entry in surface_library()['textures'] if entry['name'] == name)


def save_profile(profile):
    system, tv = profile['system'], profile['tv']
    saved, native = saved_path(system, tv), native_path(system, tv)
    saved.parent.mkdir(exist_ok=True)
    contents = (json.dumps(profile, indent=2) + '\n').encode('utf-8')
    # Three.js converts degrees through radians on load. Keep authored JSON bytes
    # when that roundtrip makes no change to the native renderer's saved values.
    if saved.is_file() and native_text(json.loads(saved.read_text(encoding='utf-8'))) == native_text(profile):
        contents = saved.read_bytes()
    if saved.is_file() and saved.read_bytes() != contents:
        history = ROOT / 'scene-layouts/history'
        history.mkdir(parents=True, exist_ok=True)
        name = ('' if system == 'snes' and tv == 'panasonic' else system + '-' + tv + '-') + str(time.time_ns()) + '.json'
        backup = history / name
        backup.write_bytes(saved.read_bytes())
        if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(saved.read_bytes()).digest():
            raise OSError('Layout history verification failed')
    native.parent.mkdir(exist_ok=True)
    for target, value in ((saved, contents), (native, native_text(profile).encode('utf-8'))):
        temporary = target.with_suffix(target.suffix + '.' + secrets.token_hex(4) + '.tmp')
        temporary.write_bytes(value)
        os.replace(temporary, target)
    return dict(saved=True, json=str(saved), native=str(native))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, data, mime='application/json'):
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        try:
            if self.headers.get('Host') not in ('127.0.0.1:' + str(self.server.server_port), 'localhost:' + str(self.server.server_port)):
                return self.reply(403, dict(error='Loopback host required'))
            if path == '/api/manifest':
                return self.reply(200, manifest(query_system(parts.query), query_tv(parts.query)))
            if path == '/api/room/manifest':
                consoles={key:manifest(key,query_tv(parts.query)) for key in SYSTEMS}
                for model,base,units in [('snes-us','snes',1.55),('md-jp','md',224/109)]:
                    consoles[model]=dict(consoles[base],console='/assets/native/'+model+'/model.mesh',consoleUnits=units)
                return self.reply(200, dict(token=TOKEN,tables=TABLES,tvs=list(TVS),consoles=consoles))
            if path == '/api/room/profile':
                kind=(parse_qs(parts.query).get('scene') or ['room'])[0]
                if kind not in ('room','home'):raise ValueError('Choose room or home')
                tv=query_tv(parts.query);key='room' if kind=='room' else 'home-'+tv
                saved=ROOT/'scene-layouts'/(key+'.json')
                if saved.is_file():
                    raw=saved.read_bytes();profile=room_profiles.validate(json.loads(raw));sha=hashlib.sha256(raw).hexdigest()
                else:
                    profile=room_profiles.default_room() if kind=='room' else room_profiles.parse_home((HERE/('home-default-'+tv+'.scene')).read_text(),tv);sha=None
                return self.reply(200,dict(profile=profile,sha256=sha,saved=saved.is_file()))
            if path == '/api/room/surfaces':
                return self.reply(200, surface_library())
            if path.startswith('/assets/surfaces/') and path.endswith('.png'):
                return self.reply(200, room_profiles.texture_path(ROOT, path.removeprefix('/assets/surfaces/').removesuffix('.png')).read_bytes(), 'image/png')
            if path == '/api/room/device':
                try:
                    kind=(parse_qs(parts.query).get('scene') or ['room'])[0]
                    return self.reply(200,device_room(kind,query_tv(parts.query)))
                except Exception as error:
                    detail=error.stderr.decode('utf-8','replace').strip() if getattr(error,'stderr',None) else str(error)
                    return self.reply(502,dict(error='Cannot read the device scene: '+detail))
            if path == '/api/upload':
                return self.reply(200, UPLOADS.status())
            if path == '/api/upload-plan':
                return self.reply(200, upload_plan((parse_qs(parts.query).get('local') or ['0'])[0] != '1'))
            if path == '/api/device-import':
                try:
                    return self.reply(200, device_import())
                except Exception as error:  # ssh/device failures are reported, never fatal
                    detail = error.stderr.decode('utf-8', 'replace').strip() if getattr(error, 'stderr', None) else str(error)
                    return self.reply(502, dict(error='Cannot read the device layouts: ' + (detail or type(error).__name__)))
            if path == '/api/device-layout':
                try:
                    return self.reply(200, device_layout(query_system(parts.query), query_tv(parts.query)))
                except Exception as error:  # ssh/device failures are reported, never fatal
                    detail = error.stderr.decode('utf-8', 'replace').strip() if getattr(error, 'stderr', None) else str(error)
                    return self.reply(502, dict(error='Cannot read the device layout: ' + (detail or type(error).__name__)))
            if path == '/api/export-plan':
                group = (parse_qs(parts.query).get('group') or [''])[0]
                return self.reply(200, dict(targets=export_plan(query_system(parts.query), query_tv(parts.query), group)))
            if path in ('/api/profile', '/api/default'):
                # A console without its own saved layout starts from the user's SNES one.
                system = query_system(parts.query)
                tv = query_tv(parts.query)
                own, snes = saved_path(system, tv), saved_path('snes')
                if path == '/api/profile' and own.is_file():
                    profile = json.loads(own.read_text())
                elif path == '/api/profile' and snes.is_file():
                    fallback = next((p for p in (saved_path('snes', tv), saved_path(system), snes) if p.is_file()), snes)
                    profile = json.loads(fallback.read_text())
                    if profile['system'] != system:
                        profile = adopt(expand_profile(profile), system)
                else:
                    profile = adopt(read_profile(BUILD / 'editor-default.scene'), system)
                return self.reply(200, expand_profile(adopt_tv(profile, tv)))
            if path.startswith('/assets/native/'):
                base, relative = slot_root() / 'consoles', path.removeprefix('/assets/native/')
            elif path.startswith('/assets/local/'):
                base, relative = slot_root() / 'local-models', path.removeprefix('/assets/local/')
            elif path.startswith('/assets/prepared/'):
                base, relative = ASSETS, path.removeprefix('/assets/prepared/')
            elif path.startswith('/assets/faces/'):
                # Private review fronts (fetch_faces.py): snes in faces/, others in faces-SYSTEM/.
                system, _, relative = path.removeprefix('/assets/faces/').partition('/')
                if system not in SYSTEMS:
                    system, relative = 'snes', path.removeprefix('/assets/faces/')
                base = BUILD / ('faces' if system == 'snes' else 'faces-' + system)
                if re.fullmatch(r'(?:[0-9]|1[01])\.png', relative) and not (base / relative).is_file():
                    base, relative = slot_root() / 'shells', system + '.png'
            elif path.startswith('/vendor/'):
                base, relative = VENDOR, path.removeprefix('/vendor/')
            else:
                base, relative = HERE, 'index.html' if path == '/' else path.lstrip('/')
            target = (base / relative).resolve()
            if not target.is_relative_to(base.resolve()) or not target.is_file() or target.suffix not in ('.html', '.js', '.css', '.png', '.mesh', '.texture', '.json', '.txt'):
                return self.reply(404, dict(error='Not found'))
            mime = 'text/javascript' if target.suffix == '.js' else mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            self.reply(200, target.read_bytes(), mime)
        except (ValueError, KeyError, OSError) as error:
            self.reply(400, dict(error=str(error)))

    def do_POST(self):
        try:
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            if (host not in ('127.0.0.1:' + str(self.server.server_port), 'localhost:' + str(self.server.server_port))
                    or self.path not in ('/api/save', '/api/upload', '/api/export', '/api/upload-batch', '/api/room/save', '/api/room/upload', '/api/room/validate', '/api/room/surface')
                    or self.headers.get('X-Scene-Token') != TOKEN or origin != 'http://' + host):
                return self.reply(403, dict(error='Local editor session required'))
            length = int(self.headers.get('Content-Length', 0))
            if not 1 <= length <= (40_000_000 if self.path == '/api/room/surface' else 100000):
                raise ValueError('Invalid profile size' if self.path != '/api/room/surface' else 'Choose an image under 30 MB')
            body = json.loads(self.rfile.read(length))
            if self.path == '/api/room/surface':
                with SAVE_LOCK:
                    return self.reply(200, dict(texture=import_surface(body)))
            if self.path=='/api/room/validate':return self.reply(200,dict(profile=room_profiles.validate(body['profile'])))
            if self.path in ('/api/room/save','/api/room/upload'):
                with SAVE_LOCK:
                    if self.path=='/api/room/save':return self.reply(200,room_profiles.save(ROOT,body['profile'],body.get('expect')))
                    def prepare():
                        result=room_profiles.save(ROOT,body['profile'],body.get('expect'))
                        entry=scene_entry(result['key']);entry['saved']=result;return [entry]
                    result=UPLOADS.start_batch(prepare)
                return self.reply(202,result)
            if self.path in ('/api/export', '/api/upload-batch'):
                choice = body.get('open') or 'normal'
                target = None if choice == 'normal' else layout_pair(choice)
            if self.path == '/api/upload-batch':
                if not isinstance(body.get('layouts'), list) or not isinstance(body.get('expect'), dict):
                    raise ValueError('Choose saved layouts to upload')
                with SAVE_LOCK:
                    status = UPLOADS.start_batch(lambda: batch_entries(body['layouts'], body['expect']), target)
                return self.reply(202, status)
            if self.path == '/api/export':
                with SAVE_LOCK:
                    if not body.get('upload'):
                        return self.reply(200, dict(results=export_profile(body['profile'], body['group'])))
                    # "…and upload": the export runs under the upload lock, so a rejected
                    # upload saves nothing, and exactly the layouts just saved are sent.
                    results = []
                    def prepare():
                        results.extend(export_profile(body['profile'], body['group']))
                        return batch_entries([item['system'] + '-' + body['profile']['tv'] for item in results])
                    status = UPLOADS.start_batch(prepare, target)
                    return self.reply(202, dict(results=results, upload=status))
            profile = validate(body)
            with SAVE_LOCK:
                if self.path == '/api/upload':
                    result, code = UPLOADS.start(profile, native_text(profile), save_profile), 202
                else:
                    result, code = save_profile(profile), 200
            self.reply(code, result)
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.reply(400, dict(error=str(error)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not (BUILD / 'editor-default.scene').is_file():
        raise SystemExit('Generate editor-default.scene with the tabletop probe first; see tools/tabletop/editor/README.md')
    for system, tv in ((s, t) for s in SYSTEMS for t in TVS):
        if saved_path(system, tv).is_file():
            derived = native_path(system, tv)
            derived.parent.mkdir(exist_ok=True)
            derived.write_text(native_text(json.loads(saved_path(system, tv).read_text())))
    for key in ['room',*('home-'+tv for tv in TVS)]:
        saved=ROOT/'scene-layouts'/(key+'.json')
        if saved.is_file():
            value=json.loads(saved.read_text());text=room_profiles.native_text(value)
            target=ASSETS/'layouts'/(key+('.world' if key=='room' else '.scene'));target.parent.mkdir(exist_ok=True);target.write_text(text)
    vendor()
    UPLOADS.restore_status()
    print('Scene editor: http://127.0.0.1:' + str(args.port), flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
