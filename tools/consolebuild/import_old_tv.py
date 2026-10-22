"""Prepare pibanezl's Old TV as a selectable presentation/tabletop TV (Blender 4.5).

Usage: blender -b --factory-startup --disable-autoexec --python import_old_tv.py -- SOURCE.glb
Source: https://sketchfab.com/3d-models/old-tv-833d046f00394fb1a69514b3c96e86bd
CC BY 4.0 (research/tv-pibanezl-old-tv/source.json). The source is five meshes facing -Y;
`TV_LP_09` is exactly the visible tube face and becomes the blank live glass, the cabinet
keeps its source maps. Real size: a 14-inch set, i.e. the tube face's diagonal is the
13.2-inch (335 mm) viewable diagonal of a 14-inch tube; uniform scale, artist proportions.
Writes third_party/models/pibanezl-old-tv/model.glb (metres, floor z = 0, centred on its
footprint) and build/slotted-presentation/oldtv-source.json; then run
render_tv_standard.py -- oldtv PREPARED.glb and python -m tools.themebuild.television.
"""
import hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(sys.argv[sys.argv.index('--') + 1])
URL = 'https://sketchfab.com/3d-models/old-tv-833d046f00394fb1a69514b3c96e86bd'
SCREEN = 'TV_LP_09'
VIEWABLE_MM = 13.2 * 25.4

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:
    world = o.matrix_world.copy()
    o.parent = None
    o.data.transform(world)
    o.matrix_world = Matrix.Identity(4)
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
glass = next(o for o in meshes if o.name.startswith(SCREEN))
normal = sum((p.normal * p.area for p in glass.data.polygons), Vector()).normalized()
if normal.y > -.8:
    raise ValueError('Screen mesh does not face -Y as inspected: %s' % tuple(normal))
g = [v.co for v in glass.data.vertices]
diagonal = math.hypot(max(p.x for p in g) - min(p.x for p in g), max(p.z for p in g) - min(p.z for p in g))
k = VIEWABLE_MM / 1000 / diagonal                     # metres per source unit
points = [v.co for o in meshes for v in o.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)]); high = Vector([max(p[i] for p in points) for i in range(3)])
place = Matrix.Scale(k, 4) @ Matrix.Translation(-Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z)))
for o in meshes:
    o.data.transform(place)
    o.data.update()
    if o is not glass:
        o.name = 'Old TV ' + o.name.split(' ')[0]
glass.name = 'Blank live CRT glass'
blank = bpy.data.materials.new('Blank live CRT glass'); blank.use_nodes = True
shader = blank.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.012, .018, .018, 1)
shader.inputs['Roughness'].default_value = .3
glass.data.materials.clear(); glass.data.materials.append(blank)

family = ROOT / 'third_party/models/pibanezl-old-tv'
family.mkdir(parents=True, exist_ok=True)
prepared = family / 'model.glb'
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(prepared), export_format='GLB', use_selection=True,
                          export_cameras=False, export_lights=False, export_animations=False, export_extras=False)
points = [v.co for o in meshes for v in o.data.vertices]
size = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
profile = dict(id='oldtv', name='Old TV', author='pibanezl (@hypermegadev)', source=URL,
               license='CC BY 4.0', license_url='https://creativecommons.org/licenses/by/4.0/',
               source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               prepared_sha256=hashlib.sha256(prepared.read_bytes()).hexdigest(),
               screen_faces=len(glass.data.polygons), viewable_diagonal_mm=VIEWABLE_MM,
               cabinet_mm=[round(v * 1000, 1) for v in size],
               changes=['World transforms applied; centred on its footprint, floor at z = 0, front -Y, metres',
                        'Uniform scale to a 14-inch set: tube face diagonal = 13.2-inch (335 mm) viewable',
                        'Source tube-face mesh (TV_LP_09) kept as blank live glass; its source maps dropped',
                        'Cabinet keeps all source triangles, UVs and 2k base-colour maps'])
out = ROOT / 'build/slotted-presentation'
out.mkdir(parents=True, exist_ok=True)
(out / 'oldtv-source.json').write_text(json.dumps(profile, indent=2) + '\n')
print('OLD TV PREPARED', prepared, 'cabinet mm', profile['cabinet_mm'], 'glass faces', profile['screen_faces'])
