"""Cianon's Nintendo DS Lite, source UVs and every visible triangle. CC BY 4.0.

Blender 4.5 --factory-startup --disable-autoexec. Processing code MIT.

The source is one open clamshell: a body, a lid and a fully transparent glass
overlay (28 triangles) over the top screen. Both screens are painted into the
base-colour atlas, so each is split into its own LCD part and blanked for live
game metadata. The lid already rotates about its own knuckle (a circular
section across the hinge); the whole lid group is registered about that axis
and, for the existing 145-degree presentation pose, opened by the difference.
The source paints only a notch where Slot-1 would be, with a fixed game-card
picture on it; the picture is cleared and an original dark mouth is added.
Coordinates: Blender frame x right, y rear, z up (glTF import); native frame is
produced by textured_blender.to_native.
"""
import json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

URL = 'https://sketchfab.com/3d-models/nintendo-ds-lite-ca529eb7208746e89b7a28fd2246659d'
WIDTH_MM = 133.0                    # Nintendo's published closed width
Q = 404 / 133                       # native units per mm (existing DS register)
BOTTOM_NATIVE = -87.5               # underside height of the preceding model
OPEN_DEGREES = 145.0                # accepted presentation pose
SLOT_NATIVE = (-28.0, -70.4)        # existing card path: x offset, face height
MOUTH_MM = (35.0, 4.6, 1.0)         # opening width, height, proud of the rear face


def circle(points):
    a = np.c_[2 * points[:, 0], 2 * points[:, 1], np.ones(len(points))]
    solution, *_ = np.linalg.lstsq(a, (points ** 2).sum(1), rcond=None)
    centre = solution[:2]
    radius = math.sqrt(solution[2] + (centre ** 2).sum())
    return centre, radius, float(np.abs(np.hypot(*(points - centre).T) - radius).max())


def box(name, centre, size, material):
    bpy = tb.bpy
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.context.view_layer.update()
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    o.data.materials.append(material)
    return o


def main():
    source = Path(sys.argv[sys.argv.index('--') + 1])
    objects = tb.import_source(source)
    bpy = tb.bpy
    body, lid, glass = objects['Object_4'], objects['Object_7'], objects['Object_10']
    assert (len(body.data.polygons), len(lid.data.polygons), len(glass.data.polygons)) == (926, 232, 28)
    glass_triangles = len(glass.data.polygons)
    bpy.data.objects.remove(glass, do_unlink=True)  # alpha-0 overlay: invisible

    # Screens: the only large flat faces of the deck and of the lid's inner fascia.
    def deck_screen(tri):
        return tri.area > 900 and tri.normal.z > .99
    bottom = tb.copy_triangles(body, 'Bottom LCD', deck_screen)
    body_rest = tb.copy_triangles(body, 'DS Lite lower housing', lambda tri: not deck_screen(tri))
    normal = Vector((0, 0, 0))
    lid.data.calc_loop_triangles()
    for tri in lid.data.loop_triangles:
        if 900 < tri.area < 1100 and tri.normal.y < -.5 and tri.normal.z > .3:
            normal = tri.normal.copy()

    def lid_screen(tri):
        return 900 < tri.area < 1100 and tri.normal.dot(normal) > .99
    assert normal.length > .9
    top = tb.copy_triangles(lid, 'Top LCD', lid_screen)
    lid_rest = tb.copy_triangles(lid, 'DS Lite upper housing', lambda tri: not lid_screen(tri))
    assert len(bottom.data.polygons) == 2 and len(top.data.polygons) == 2
    for o in (body, lid):
        bpy.data.objects.remove(o, do_unlink=True)

    # The lid's own knuckle: a circular section across the hinge, fitted at both ends.
    points = np.array([tuple(v.co) for v in lid_rest.data.vertices])
    centres = []
    for x in (-40.9, 42.2):
        ring = points[(np.abs(points[:, 0] - x) < .3) & (points[:, 1] < 27) & (points[:, 2] < 27)][:, 1:]
        centre, radius, error = circle(ring)
        assert len(ring) >= 12 and error < .3 and 3 < radius < 4.5, (x, len(ring), radius, error)
        centres.append(centre)
    hinge_yz = np.mean(centres, axis=0)
    # Source opening angle: the inner screen normal is (0, -sin t, -cos t) for a lid open by t.
    source_open = math.degrees(math.acos(-normal.z))
    extra = math.radians(OPEN_DEGREES - source_open)
    hinge = Vector((0, hinge_yz[0], hinge_yz[1]))
    # Native +X closes the lid, so opening further is a negative turn about the same axis.
    turn = Matrix.Translation(hinge) @ Matrix.Rotation(-extra, 4, 'X') @ Matrix.Translation(-hinge)
    for o in (lid_rest, top):
        o.data.transform(turn)
        o.data.update()
    moved = (turn.to_3x3() @ normal)
    assert abs(moved.y + math.sin(math.radians(OPEN_DEGREES))) < 1e-4 and abs(moved.z + math.cos(math.radians(OPEN_DEGREES))) < 1e-4

    kept = [body_rest, bottom, lid_rest, top]
    all_lo, all_hi = tb.bounds(kept)
    lcd_lo, lcd_hi = tb.bounds([bottom])
    lo, hi = tb.bounds([body_rest])
    mm = WIDTH_MM / (hi.x - lo.x)
    k = mm * Q                                  # native units per source unit
    bottom_face = 1.4                           # flat underside of the lower housing
    centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, bottom_face + -BOTTOM_NATIVE / k))
    # Original Slot-1 mouth on the rear face, over the existing card path.
    rear_y = max(v.co.y for v in body_rest.data.vertices if abs(v.co.x) < 30)
    material = bpy.data.materials.new('Slot DS mouth')
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.006, .006, .007, 1)
    width, height, proud = (v / mm for v in MOUTH_MM)
    mouth_x = centre.x + SLOT_NATIVE[0] / k
    mouth_z = bottom_face + (SLOT_NATIVE[1] - BOTTOM_NATIVE) / k
    mouth = box('DS Slot-1 mouth', (mouth_x, rear_y + proud / 2 - .25 / mm, mouth_z), (width, proud + .5 / mm, height), material)
    kept.append(mouth)

    native_hinge = [0.0, (hinge_yz[1] - centre.z) * k, -(hinge_yz[0] - centre.y) * k]
    tb.to_native(kept, centre, mm, Q)
    work = tb.ROOT / 'build/textured/nds'
    work.mkdir(parents=True, exist_ok=True)
    flags = {body_rest.name: dict(role='paint'), bottom.name: dict(role='lcd'),
             lid_rest.name: dict(role='paint', moving=True), top.name: dict(role='lcd', moving=True)}
    for o in (lid_rest, top):
        o['hinged'] = True
    for o in kept:
        o['source_part'] = {'DS Lite lower housing': 'base', 'Bottom LCD': 'base screen', 'DS Lite upper housing': 'Clamshell',
                            'Top LCD': 'Clamshell screen', 'DS Slot-1 mouth': 'original fitting'}[o.name]
    depth_native = (hi.y - lo.y) * k
    registration = dict(
        model='nds', adapter='cianon_ds.py', author='Cianon', title='Nintendo DS Lite', url=URL,
        licence='CC-BY-4.0', licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name, source_sha256=tb.sha256(source), mm_per_source_unit=mm, native_units_per_mm=Q,
        scale_basis='Uniform, 133 mm published width; artist proportions retained (73.9 mm deep matches the published depth)',
        source_size_mm=[(all_hi.x - all_lo.x) * mm, (all_hi.y - all_lo.y) * mm, (all_hi.z - all_lo.z) * mm],
        source_triangles=1186, removed_source_parts=['Glass overlay (28 triangles, fully transparent)'], decimation=False,
        hinge_native=native_hinge, open_degrees=OPEN_DEGREES, source_open_degrees=source_open,
        hinge_basis='Axis of the lid knuckle (circle fitted to both ends); the source has no mechanism, so the sweep, not an OEM drawing, checks clearance',
        card_slot_native=list(SLOT_NATIVE), mouth_mm=list(MOUTH_MM),
        lcd_size_mm=[(lcd_hi.x - lcd_lo.x) * mm, (lcd_hi.y - lcd_lo.y) * mm],
        spec=dict(ry=depth_native / 2, depth=24, slot=-(depth_native / 2 + 1)),
        modifications=['Remove the transparent glass overlay; split both screens from their shells and blank them for live metadata',
                       'Clear the source game-card picture painted on the Slot-1 notch; add an original dark Slot-1 mouth over the card path',
                       'Register the lid about its own knuckle and open it from the source %.1f degrees to the %d-degree presentation pose' % (source_open, OPEN_DEGREES),
                       'Retain all 1,158 other source triangles, UVs and the 2048 px base-colour atlas (not enlarged)',
                       'Source albedo with simple lighting; no normal/roughness/metallic maps'])
    tb.write_corners(kept, work, flags)
    (work / 'registration.json').write_text(json.dumps(registration, indent=2) + '\n')
    tb.export_master_glb(kept, work / 'model-master.glb')
    target = tb.ROOT / 'theme/art-book-slot/_slot/consoles/nds'
    provenance = dict(source_creator='Cianon', source_licence='CC-BY-4.0', source_url=URL)
    for name, physical in [('model.glb', False), ('model-master.glb', False), ('model-physical.glb', True)]:
        tb.export_geometry_glb(kept, target / name, Q, physical=physical, provenance=provenance)
    print('NDS PREPARED', json.dumps(registration), flush=True)


if __name__ == '__main__':
    main()
