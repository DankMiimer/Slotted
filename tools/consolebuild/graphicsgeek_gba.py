"""thegraphicsgeek's Game Boy Advance SP, source UVs and base-colour maps. CC BY 4.0.

Blender 4.5 --factory-startup --disable-autoexec. Processing code MIT.

The source is one open SP of 66,826 triangles in 46 parts and three material
tiles (1001 base, 1002 buttons/ports/lid, 1003 shoulder keys/lettering/label),
each with its own 1024 px base-colour map and UVs offset by whole tiles. The
two transparent glass overlays are dropped; everything else is kept. The model
is registered into the frame of the earlier packaged SP, so the existing
Game Pak path, bay constants and reading pose still apply: the artist's 84 x 82 mm
footprint is corrected to Nintendo's published 82 x 84.6 mm (thickness untouched),
the underside sits at native y -85.1 and the Game Pak bay's end wall at native z 18.0.
The source bay is 6.1 mm tall; the registered Game Pak is 7.3 mm, so the roof of the
bay is raised until the shell clears it. The lid keeps the source's own opening angle.
Source axes (Blender): x right, y rear, z up.
"""
import json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

URL = 'https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f'
Q = 224 / 82                         # native units per mm (existing SP register)
WIDTH_MM, DEPTH_MM = 82.0, 84.6      # published footprint
BOTTOM_NATIVE = -85.1                # underside, as in the packaged derivative
BAY_END_NATIVE = 18.0                # bay end wall, 0.8 behind the Game Pak leading edge (18.8)
CART_CENTRE_NATIVE, CART_HALF_THICKNESS_MM = -71.1, 3.64   # registered Game Pak (7.3 mm)
LID = ('TopScreen_Frame_geo', 'Top_LargeHinge_geo', 'Top_SmallHinge_geo', 'ScreenGuard_geo', 'LogoSticker_geo', 'Sceren_geo')
PAINT = ('Base_geo', 'TopScreen_Frame_geo', 'Top_LargeHinge_geo', 'Top_SmallHinge_geo', 'Battery_Lid_geo',
         'L_ShoulderBtn_geo', 'R_ShoulderBtn_geo', 'HingeCorner_LMid_geo', 'HingeCorner_RMid_geo')
RENAMED = {'Base_geo': 'SP lower housing', 'TopScreen_Frame_geo': 'SP display lid', 'Sceren_geo': 'SP LCD glass'}


def circle(points):
    a = np.c_[2 * points[:, 0], 2 * points[:, 1], np.ones(len(points))]
    solution, *_ = np.linalg.lstsq(a, (points ** 2).sum(1), rcond=None)
    centre = solution[:2]
    radius = math.sqrt(solution[2] + (centre ** 2).sum())
    return centre, radius, float(np.abs(np.hypot(*(points - centre).T) - radius).max())


def normalise_uv_tiles(o):
    """UVs sit in whole-tile offsets (u + 1, u + 2) under a repeat sampler: fold to 0..1."""
    layer = o.data.uv_layers.active
    shift = math.floor(min(item.uv.x for item in layer.data) + 1e-4)
    for item in layer.data:
        item.uv.x -= shift
    return shift


def main():
    source = Path(sys.argv[sys.argv.index('--') + 1])
    objects = tb.import_source(source)
    bpy = tb.bpy
    assert len(objects) == 46 and sum(len(o.data.polygons) for o in objects.values()) == 66826
    for name in ('ScreenGlass_geo', 'ScreenCover_geo'):
        bpy.data.objects.remove(objects.pop(name), do_unlink=True)   # alpha-blended lens overlays
    for o in objects.values():
        normalise_uv_tiles(o)
        o.data.transform(Matrix.Scale(1000, 4))     # the GLB is in metres; work in millimetres
        o.data.update()
    base = objects['Base_geo']

    # Bay: measured from the source, then the roof is raised to clear the registered Game Pak.
    floor_z = tb.ray(base, (0, -20, 4), (0, 0, -1)).z
    roof_z = tb.ray(base, (0, -20, 4), (0, 0, 1)).z
    end_y = tb.ray(base, (0, -20, 4), (0, 1, 0)).y
    mm_per_native_z = 1 / Q
    cart_top = (CART_CENTRE_NATIVE - BOTTOM_NATIVE) / Q + CART_HALF_THICKNESS_MM
    raise_by = max(0.0, cart_top + .15 - roof_z)
    raised = 0
    for v in base.data.vertices:
        # Roof, mouth top edge and the lip rounding above it (z up to ~9.1) move together; the deck top is at 12+.
        if v.co.y < end_y + .1 and abs(v.co.x) < 33.8 and roof_z - .3 < v.co.z < 11.0:
            v.co.z += raise_by
            raised += 1
    base.data.update()
    assert raised > 100, raised

    # The hinge pin: circular sections (r 2.5 mm, residual < 0.05 mm) inside both fixed hinge corners.
    centres = []
    for name in ('HingeCorner_LMid_geo', 'HingeCorner_RMid_geo'):
        pts = np.array([tuple(v.co) for v in objects[name].data.vertices])
        for x in (-41.2, 41.2):
            ring = pts[np.abs(pts[:, 0] - x) < .06][:, 1:]
            if len(ring) < 12:
                continue
            centre, radius, error = circle(ring)
            assert error < .05 and 2.3 < radius < 2.8, (name, x, len(ring), radius, error)
            centres.append(centre)
    assert len(centres) == 2, centres
    hinge_yz = np.mean(np.array(centres), axis=0)
    lcd = objects['Sceren_geo']
    lcd.data.calc_loop_triangles()
    normal = sum((t.normal for t in lcd.data.loop_triangles), Vector((0, 0, 0))).normalized()
    if normal.y > 0:
        normal = -normal
    source_open_degrees = math.degrees(math.acos(-normal.z))

    # Footprint correction and registration into the packaged SP's native frame.
    lo, hi = tb.bounds([base])
    sx, sy = WIDTH_MM / (hi.x - lo.x), DEPTH_MM / (hi.y - lo.y)
    cx = (lo.x + hi.x) / 2
    y0 = end_y + BAY_END_NATIVE / (sy * Q)
    k = Q * .01
    transform = Matrix.Translation((0, 0, BOTTOM_NATIVE * .01)) @ Matrix.Diagonal((sx * k, sy * k, k, 1)) @ Matrix.Translation((-cx, -y0, -lo.z))
    kept = []
    flags = {}
    for key, o in list(objects.items()):
        o.name = RENAMED.get(key, 'SP ' + key[:-4])
        o['source_part'] = key
        if key in LID:
            o['hinged'] = True
        flags[o.name] = {}
        if key in PAINT:
            flags[o.name]['role'] = 'paint'
        if key == 'Sceren_geo':
            flags[o.name]['role'] = 'lcd'
        if key in LID:
            flags[o.name]['moving'] = True
        kept.append(o)
    source_size = tb.bounds(kept)
    for o in kept:
        o.data.transform(transform)
        o.data.update()
    # The footprint correction tilts the lid plane slightly: take the opening angle from the registered LCD.
    lcd.data.calc_loop_triangles()
    registered_normal = sum((t.normal for t in lcd.data.loop_triangles), Vector((0, 0, 0))).normalized()
    if registered_normal.y > 0:
        registered_normal = -registered_normal
    open_degrees = math.degrees(math.acos(-registered_normal.z))
    native_hinge = [0.0, (hinge_yz[1] - lo.z) * Q + BOTTOM_NATIVE, -(hinge_yz[0] - y0) * sy * Q]
    front_native = -(lo.y - y0) * sy * Q
    lcd_lo, lcd_hi = tb.bounds([lcd])
    work = tb.ROOT / 'build/textured/gba'
    work.mkdir(parents=True, exist_ok=True)
    registration = dict(
        model='gba', adapter='graphicsgeek_gba.py', author='thegraphicsgeek', title='Gameboy Advance SP', url=URL,
        licence='CC-BY-4.0', licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name, source_sha256=tb.sha256(source), native_units_per_mm=Q,
        scale_basis='Footprint corrected from the artist\'s %.1f x %.1f mm to Nintendo\'s published 82 x 84.6 mm (x %.4f, y %.4f); thickness uniform at %.4f native/mm'
                    % (hi.x - lo.x, hi.y - lo.y, sx, sy, Q),
        source_size_mm=[source_size[1].x - source_size[0].x, source_size[1].y - source_size[0].y, source_size[1].z - source_size[0].z],
        source_triangles=66826, excluded_source_materials=['ScreenGlass_MAT (alpha-blended lens overlay with GAME BOY ADVANCE SP lettering)'],
        removed_source_parts=['ScreenGlass (2 triangles) and ScreenCover (40): alpha-blended lens overlays'],
        decimation=False, hinge_native=native_hinge, open_degrees=open_degrees, source_open_degrees=source_open_degrees, open_radians=math.radians(open_degrees),
        hinge_basis='Circular sections of the hinge pin inside both fixed hinge corners (r 2.5 mm); the source has no mechanism',
        bay=dict(floor_mm=floor_z, roof_mm=roof_z, roof_raised_mm=raise_by, end_wall_native=BAY_END_NATIVE,
                 cart_centre_native=CART_CENTRE_NATIVE, vertices_raised=raised),
        lcd_size_mm=[(lcd_hi.x - lcd_lo.x) * 100 / Q, math.dist((lcd_hi.y, lcd_hi.z), (lcd_lo.y, lcd_lo.z)) * 100 / Q],
        spec=dict(ry=DEPTH_MM * Q / 2, depth=21, slot=front_native),
        modifications=['Drop the two transparent lens overlays (42 triangles); keep all 66,784 others, their UVs and the three 1024 px base-colour maps',
                       'Fold each material tile\'s UV offset to 0..1 and pack the maps into one 2048 px atlas at native resolution',
                       'Correct the footprint to 82 x 84.6 mm and register into the packaged SP\'s frame so the Game Pak path is unchanged',
                       'Raise the cartridge bay roof %.2f mm (%d vertices) so the registered Game Pak shell clears it' % (raise_by, raised),
                       'Keep the source opening angle (%.1f degrees, %.2f after the footprint correction) and register the lid about the hinge pin axis' % (source_open_degrees, open_degrees),
                       'Source albedo with simple lighting; normal/roughness/metallic/AO maps are not rendered']
    )
    tb.write_corners(kept, work, flags)
    (work / 'registration.json').write_text(json.dumps(registration, indent=2) + '\n')
    tb.export_master_glb(kept, work / 'model-master.glb')
    target = tb.ROOT / 'theme/art-book-slot/_slot/consoles/gba'
    provenance = dict(source_creator='thegraphicsgeek', source_licence='CC-BY-4.0', source_url=URL)
    for name, physical in [('model.glb', False), ('model-master.glb', False), ('model-physical.glb', True)]:
        tb.export_geometry_glb(kept, target / name, Q, physical=physical, provenance=provenance)
    print('GBA PREPARED', json.dumps(registration), flush=True)


if __name__ == '__main__':
    main()
