"""Prepare Denys Hroshko's Retro TV as a selectable presentation TV (Blender 4.5).

Usage: blender -b --factory-startup --disable-autoexec --python import_retro_tv.py -- SOURCE.glb
Source: https://sketchfab.com/3d-models/tv-old-tv-retro-tv-f13b9a45c0d649dc90ebac5f7717cebf
CC BY-NC 4.0 (noncommercial; applies to the render and the prepared model).
The source is one mesh/material facing +X. Its screen faces are identified by
their region in the base-colour UV layout, separated and given blank glass; the
cabinet keeps its source maps. Then: python -m tools.themebuild.television
"""
import hashlib, json, math, sys
from pathlib import Path
import bmesh, bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(sys.argv[sys.argv.index('--') + 1])
WORK = ROOT / 'build/model-options/retro'
URL = 'https://sketchfab.com/3d-models/tv-old-tv-retro-tv-f13b9a45c0d649dc90ebac5f7717cebf'
# Grey screen panel in the base-colour atlas (u0, v0, u1, v1).
SCREEN_UV = (.02, .22, .225, .53)
SIZE = 960

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
tv = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
world = tv.matrix_world.copy()
tv.parent = None
tv.data.transform(world)
tv.matrix_world = Matrix.Identity(4)
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
tv.name = 'Retro TV cabinet'

# Select the screen by UV region, then face it toward -Y (the camera side).
uv = tv.data.uv_layers.active.data
screen_faces = []
for p in tv.data.polygons:
    centre = sum((uv[i].uv for i in p.loop_indices), Vector((0, 0))) / len(p.loop_indices)
    if SCREEN_UV[0] < centre.x < SCREEN_UV[2] and SCREEN_UV[1] < centre.y < SCREEN_UV[3]:
        screen_faces.append(p.index)
normal = sum((tv.data.polygons[i].normal * tv.data.polygons[i].area for i in screen_faces), Vector()).normalized()
if normal.x < .8:
    raise ValueError('Screen selection does not face +X as inspected: %s' % tuple(normal))
turn = Matrix.Rotation(-math.pi / 2 - math.atan2(normal.y, normal.x), 4, 'Z')  # screen normal -> -Y
tv.data.transform(turn)
points = [v.co for v in tv.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)]); high = Vector([max(p[i] for p in points) for i in range(3)])
tv.data.transform(Matrix.Translation((-(low.x + high.x) / 2, -(low.y + high.y) / 2, -low.z)))
tv.data.update()

bm = bmesh.new(); bm.from_mesh(tv.data); bm.faces.ensure_lookup_table()
for f in bm.faces:
    f.select = f.index in set(screen_faces)
bm.to_mesh(tv.data); bm.free()
bpy.context.view_layer.objects.active = tv; tv.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='SELECTED'); bpy.ops.object.mode_set(mode='OBJECT')
glass = next(o for o in bpy.context.scene.objects if o is not tv)
glass.name = 'Blank live CRT glass'
blank = bpy.data.materials.new('Blank live CRT glass'); blank.use_nodes = True
shader = blank.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.012, .018, .018, 1)
shader.inputs['Roughness'].default_value = .3
glass.data.materials.clear(); glass.data.materials.append(blank)

WORK.mkdir(parents=True, exist_ok=True)
prepared = WORK / 'prepared.glb'
bpy.ops.object.select_all(action='DESELECT'); tv.select_set(True); glass.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(prepared), export_format='GLB', use_selection=True,
                          export_cameras=False, export_lights=False, export_animations=False, export_extras=False)

# Near-front studio view matching the Panasonic's: slight elevation and offset.
points = [v.co for o in (tv, glass) for v in o.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)]); high = Vector([max(p[i] for p in points) for i in range(3)])
size = high - low; target = (low + high) / 2
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.resolution_x = SIZE; scene.render.resolution_y = SIZE; scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = 'AgX'
background = bpy.data.worlds.new('Neutral studio'); background.use_nodes = True
background.node_tree.nodes['Background'].inputs[0].default_value = (.4, .44, .5, 1)
background.node_tree.nodes['Background'].inputs[1].default_value = .4; scene.world = background
camera_data = bpy.data.cameras.new('Near front readable camera'); camera = bpy.data.objects.new('Camera', camera_data)
scene.collection.objects.link(camera)
reach = max(size) * 4
camera.location = target + Vector((-.035 * size.x, -reach, .042 * reach))
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'; camera_data.ortho_scale = max(size.x, size.z) * 1.16; scene.camera = camera
for name, offset, energy, area in [('Key', (-.6, -.8, 1.1), 90, .8), ('Fill', (.7, -.3, .7), 45, .9)]:
    k = max(size) / .51
    light = bpy.data.lights.new(name, 'AREA'); light.energy = energy * k * k; light.shape = 'DISK'; light.size = area * k
    obj = bpy.data.objects.new(name, light); scene.collection.objects.link(obj)
    obj.location = target + Vector(offset) * k
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
render = ROOT / 'build/slotted-presentation/retro-render.png'
scene.render.filepath = str(render)
bpy.ops.render.render(write_still=True)

# Live quad: only the camera-facing glass (the UV region also holds the inner
# bezel walls), projected and inset for the tube's rounded corners.
front = [glass.matrix_world @ glass.data.vertices[i].co for p in glass.data.polygons if p.normal.y < -.9 for i in p.vertices]
projected = [world_to_camera_view(scene, camera, p) for p in front]
xs = [p.x * SIZE for p in projected]; ys = [(1 - p.y) * SIZE for p in projected]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
inset = .05; dx = (x1 - x0) * inset; dy = (y1 - y0) * inset
quad = [[x0 + dx, y0 + dy], [x1 - dx, y0 + dy], [x1 - dx, y1 - dy], [x0 + dx, y1 - dy]]
profile = dict(id='retro', name='TV, Old TV, Retro TV', author='Denys Hroshko', source=URL,
               license='CC BY-NC 4.0', license_url='https://creativecommons.org/licenses/by-nc/4.0/',
               source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               prepared_sha256=hashlib.sha256(prepared.read_bytes()).hexdigest(),
               screen_faces=len(screen_faces), glass_bounds_pixels=[x0, y0, x1, y1], quad_pixels=quad,
               changes=['Turned to face the camera; centred on the floor', 'Screen faces (UV-identified) separated as blank live glass',
                        'Cabinet keeps its source base-colour/ORM/normal maps', 'Near-front studio render, transparent background',
                        'Live screen inset 5% inside the camera-facing glass'])
(ROOT / 'build/slotted-presentation/retro-source.json').write_text(json.dumps(profile, indent=2) + '\n')
print('RETRO TV RENDERED', len(screen_faces), 'screen faces', [round(v) for v in (x0, y0, x1, y1)])
