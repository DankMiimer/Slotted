"""Private slot-facing views for feed QA; never writes an authored layout. MIT.

Run in WSL after validate_selected_cartridges. A moved console can be outside an
older authored close-up. These diagnostic cameras follow the physical slot in
console space, without changing the user's saved camera or installed scene.
"""
import json
import math
import os
from pathlib import Path
import subprocess
from .selected_cartridges import ROOT, SLOT, KEYS
from tools.tabletop.editor.server import parse_native, native_text, adopt

OUT = ROOT / 'build/cartridge-validation-20261019'
# Slot target (millimetres in the console frame), direction towards the eye,
# and distance. This is a review fixture, not a new default composition.
SLOTS = {
    'gb': ([0, 77.124143/1.8666667, -26.624431/1.8666667+3.9], [.2, .6, -1], 180),
    'gbc': ([0, 70.888721/2.1538462, -16.127651/2.1538462+3.9], [.2, .6, -1], 180),
    'gba': ([0, -26.03, 24.45], [.3, -.65, 1], 180),
    'nds': ([-28/3.037594, -65.175/3.037594, -113.29114/3.037594+16.5], [.3, -.65, -1], 130),
    'nes': ([-45/(196/120), (-53.55+.6)/(196/120), 120/(196/120)], [.1, .6, 1], 250),
    'md': ([0, 17/(224/109), -53/(224/109)], [.25, 1, .5], 220),
}


def rotate(v, angles):
    x, y, z = v
    rx, ry, rz = map(math.radians, angles)
    x, y = math.cos(rz)*x-math.sin(rz)*y, math.sin(rz)*x+math.cos(rz)*y
    y, z = math.cos(rx)*y-math.sin(rx)*z, math.sin(rx)*y+math.cos(rx)*z
    x, z = math.cos(ry)*x+math.sin(ry)*z, -math.sin(ry)*x+math.cos(ry)*z
    return [x, y, z]


def prepare():
    dest = OUT / 'diagnostic-prepared'
    dest.mkdir(exist_ok=True)
    for p in (OUT/'prepared').iterdir():
        if p.name == 'layouts':
            continue
        link = dest/p.name
        if not link.exists():
            link.symlink_to(p, target_is_directory=p.is_dir())
    layouts = dest/'layouts'
    layouts.mkdir(exist_ok=True)
    manifest = {}
    for key in KEYS:
        tv = 'panasonic' if key in ('nes', 'md') else 'pvm'
        source = OUT/'prepared/layouts'/(key+'-'+tv+'.scene')
        p = parse_native(source.read_text(), key, tv) if source.exists() else adopt(
            parse_native((OUT/'prepared/layouts/snes-panasonic.scene').read_text()), key)
        node = p['objects']['console']
        center, direction, distance = SLOTS[key]
        target = [a+b for a, b in zip(node['position'], rotate(center, node['rotation']))]
        length = math.sqrt(sum(v*v for v in direction))
        eye = [a+b for a, b in zip(target, rotate([v*distance/length for v in direction], node['rotation']))]
        p.setdefault('cameras', {})['console'] = dict(position=eye, target=target, fov=45)
        (layouts/(key+'-'+tv+'.scene')).write_text(native_text(p))
        manifest[key] = dict(source=str(source), diagnosticCamera=p['cameras']['console'])
    (OUT/'diagnostic-cameras.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return dest


def main():
    prepared = prepare()
    env = dict(os.environ, LD_LIBRARY_PATH=str(ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'),
               SDL_VIDEODRIVER='offscreen', EGL_PLATFORM='surfaceless', LIBGL_ALWAYS_SOFTWARE='1')
    for key in KEYS:
        dest = OUT/'diagnostic'/key
        dest.mkdir(parents=True, exist_ok=True)
        tv = 'panasonic' if key in ('nes', 'md') else 'pvm'
        r = subprocess.run([str(OUT/'probe-host'), str(SLOT), str(prepared), str(dest), key, tv,
                            str(OUT/'faces'/key)+'/'], env=env, capture_output=True, text=True)
        (dest/'probe.log').write_text(r.stdout+r.stderr)
        print(key, r.returncode, flush=True)
        if r.returncode:
            raise RuntimeError(r.stdout+r.stderr)


if __name__ == '__main__':
    main()
