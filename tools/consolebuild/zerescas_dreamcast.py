"""Adapt Zerescas's CC BY 4.0 Dreamcast, retaining source UVs/material detail.

Run in Blender with --factory-startup --disable-autoexec. Download stays intact;
full textured master stays in ignored build/. No source game disc is exported.
"""
import json, sys
import numpy as np
from pathlib import Path
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

URL = 'https://sketchfab.com/3d-models/sega-dreamcast-f82d99e4739e42f4abfc37cb97918cfc'
Q = 1.3
NAMES = {'Case':'Dreamcast enclosure', 'Bottom':'Dreamcast underside',
    'Door':'Dreamcast disc lid', 'Cube.005':'Dreamcast rear hinge cover',
    'Buttons':'Dreamcast power and open buttons', 'Cylinder.003':'Dreamcast spindle',
    'Cylinder.004':'Dreamcast spindle base', 'Laser':'Dreamcast laser',
    'Disc Reader':'Dreamcast optical pickup', 'Disc Reader Top':'Dreamcast drive cover',
    'Triange on front':'Dreamcast status light', 'Gamepads Ports Panel':'Dreamcast controller ports',
    'Back ports':'Dreamcast rear ports'}


def main():
    source = Path(sys.argv[sys.argv.index('--')+1])
    objects = tb.import_source(source)
    lo, hi = tb.bounds([objects['Case']])
    mm = 190 / (hi.x-lo.x)
    all_lo, all_hi = tb.bounds(list(objects.values()))
    centre = (all_lo+all_hi)/2
    # Rear lid tabs meet the source's two hinge bearings. Native z points front.
    hinge = Vector((0, 1.325, .984))
    hub_lo, hub_hi = tb.bounds([objects['Cylinder.003']])
    spindle = (hub_lo+hub_hi)/2
    # The artist's drive/lid slopes by ~3 degrees while the base is level.
    # Recover the original disc's plane; match that seat without tilting the
    # complete console or keeping any of the fixed game-disc geometry/art.
    disc = np.array([list(v.co) for v in objects['Disc'].data.vertices])
    _, _, axes = np.linalg.svd(disc-disc.mean(0), full_matrices=False)
    normal = axes[-1] if axes[-1,2]>0 else -axes[-1]
    plane = float((disc @ normal).max())
    spindle.z = (plane-normal[0]*spindle.x-normal[1]*spindle.y)/normal[2]
    # The source disc is thinner than a real 1.2-mm GD-ROM. Raise its label
    # plane 0.8 mm so the physical underside clears the source drive cover.
    spindle.z += .8/mm
    disc_tilt = float(np.arctan2(normal[2], -normal[1]))
    def native(p):
        p = (p-centre)*mm*Q
        return [p.x, p.z, -p.y]
    kept = []
    for name, o in objects.items():
        if name == 'Disc':
            tb.bpy.data.objects.remove(o, do_unlink=True)
            continue
        o.name = NAMES[name]
        o['hinged'] = name == 'Door'
        kept.append(o)
    work = tb.ROOT / 'build/textured/dreamcast'; work.mkdir(parents=True, exist_ok=True)
    tb.to_native(kept, centre, mm, Q)
    reg = dict(adapter='zerescas_dreamcast.py', author='Zerescas', licence='CC-BY-4.0',
        licence_url='https://creativecommons.org/licenses/by/4.0/', url=URL,
        source_file=source.name, source_sha256=tb.sha256(source),
        archive_sha256=tb.sha256(source.with_name('dreamcast-original.zip')),
        scale_mm_per_source_unit=mm, native_units_per_mm=Q,
        scale_basis='Uniform, 190 mm source enclosure width; artist proportions preserved',
        hinge_source=list(hinge), hinge_native=native(hinge),
        disc_centre_native=native(spindle), disc_radius_mm=60, disc_tilt_radians=disc_tilt,
        disc_source_normal=normal.tolist(),
        disc_label_raise_mm=.8,
        removed_source_parts=['Disc'], excluded_source_materials=['Disc'],
        spec=dict(rx=(all_hi.x-all_lo.x)*mm*Q/2, ry=(all_hi.y-all_lo.y)*mm*Q/2,
                  depth=(all_hi.z-all_lo.z)*mm*Q/2),
        modifications=['Uniform native registration; retain all 13 console parts without decimation',
            'Register rear hinge and spindle; animate source Door separately',
            'Remove fixed Sonic Adventure 2 disc and exclude its entire image/material',
            'Two 4K source base-colour maps packed as 1024px tiles in a 2048px atlas',
            'Preserve print, sockets and buttons under enclosure repainting',
            'Source albedo plus simple lighting; no PBR/normal/ORM maps'])
    flags = {'Dreamcast enclosure':dict(role='paint'), 'Dreamcast disc lid':dict(role='paint',moving=True),
             'Dreamcast rear hinge cover':dict(role='paint')}
    tb.write_corners(kept, work, flags)
    (work/'registration.json').write_text(json.dumps(reg, indent=2)+'\n')
    tb.export_master_glb(kept, work/'model-master.glb')
    target = tb.ROOT / 'theme/art-book-slot/_slot/consoles/dreamcast'; target.mkdir(parents=True,exist_ok=True)
    provenance = dict(source_creator='Zerescas', source_licence='CC-BY-4.0', source_url=URL)
    for name, physical in [('model.glb',False),('model-master.glb',False),('model-physical.glb',True)]:
        tb.export_geometry_glb(kept, target/name, Q, physical=physical, provenance=provenance)
    print('DREAMCAST PREPARED', json.dumps(reg), flush=True)


if __name__ == '__main__': main()
