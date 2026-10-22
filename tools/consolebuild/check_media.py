"""Independent exported-triangle feed checks for the physical media (Blender 4.5, MIT).

Moves every native media triangle along the seated path that cartridge_scene()
uses after alignment, in each console's own native frame, and intersects it with
every native console triangle. A deliberately offset copy must collide.
"""
import json
import os
import struct
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONSOLES = ROOT/'theme/art-book-slot/_slot/consoles'
SPECS = json.loads((CONSOLES/'specs.json').read_text())


def read(folder, stem):
    data = (CONSOLES/folder/(stem+'.mesh')).read_bytes()
    _, n, count, door = struct.unpack_from('<8sIII', data)
    v = struct.unpack_from('<%df' % (n*9), data, 20)
    points = [Vector(v[i:i+3]) for i in range(0, n*9, 9)]
    indices = struct.unpack_from('<%dH' % count, data, 20+n*36)
    faces = [tuple(indices[i:i+3]) for i in range(0, count, 3)]
    return points, faces, door//3


def tree(points, faces):
    return BVHTree.FromPolygons(points, faces, all_triangles=True, epsilon=0)


def poses(variant):
    """Rigid transforms (function of a media point) along the seated path."""
    spec = media.MEDIA[variant]; s = SPECS[spec['folder']]; q = media.SCALES[spec['folder']]
    w, h, t = spec['size']; half = h*q/2
    if s['kind'] == 0:
        for i in range(101):
            move = i/100; cy = half+s['entry']+55-(s['sink']+55)*move
            yield move, lambda p, cy=cy: Vector((p.x, p.y+cy, p.z+s['slot'])), True
    elif s['kind'] == 2:
        for i in range(101):
            # Slide in on the tray, then the final press, door excluded while open.
            move = min(1, i/80); press = max(0, (i-80)/20)
            face = media.NES_TRAY_TOP*s['yscale']+.6+t*q-7*s['yscale']*press
            z = s['ry']+half+9+(35-s['ry']-half-9)*move
            yield i/100, lambda p, face=face, z=z: Vector((-45-p.x, face-t*q/2+p.z, z+p.y)), i == 100
    else:
        hover = s['slot']-half-18; target = s['slot']+half-3
        for i in range(101):
            z = hover+(target-hover)*i/100+(3 if i == 100 else 0)
            yield i/100, lambda p, z=z: Vector((-28-p.x, -70.4+t*q/2-p.z, z-p.y)), True


def main():
    report = {}
    for variant, spec in media.MEDIA.items():
        cp, cf, door = read(spec['folder'], 'model'); mp, mf, _ = read(spec['folder'], spec['part'])
        # N64 leaves articulate through contact; the dedicated checker poses
        # both leaves at every feed sample and checks them against body/cart.
        housing = tree(cp, cf[:door] if variant=='n64' else cf); fixed = tree(cp, cf[:door] if door else cf)
        rows = []
        for travel, place, closed in poses(variant):
            moved = [place(p) for p in mp]
            pairs = (housing if closed else fixed).overlap(tree(moved, mf))
            row = {'travel': round(travel, 3), 'intersecting_triangle_pairs': len(pairs)}
            if pairs:
                row['console_triangle_centres'] = [list(sum((cp[k] for k in cf[a]), Vector())/3) for a, b in pairs[:8]]
            rows.append(row)
        # Into a slot wall (top-loaders, DS) or the NES tunnel roof.
        offset = Vector((0, 40, 0)) if SPECS[spec['folder']]['kind'] == 2 else Vector((24, 0, 0))
        control = [place(p)+offset for p in mp]
        positive = len(housing.overlap(tree(control, mf)))
        report[variant] = dict(console=spec['folder'], samples=rows, collision_positive_control_pairs=positive,
                               max_pairs=max(r['intersecting_triangle_pairs'] for r in rows))
    out = Path(os.environ.get('SLOT_MEDIA_EVIDENCE',str(ROOT/'build/media')))/'clearance.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({v: dict(max_pairs=r['max_pairs'], positive=r['collision_positive_control_pairs']) for v, r in report.items()}))
    assert all(r['collision_positive_control_pairs'] > 0 for r in report.values()), 'Missing positive control'
    assert all(r['max_pairs'] == 0 for r in report.values()), 'Feed intersects housing; inspect clearance.json'


if __name__ == '__main__':
    main()
