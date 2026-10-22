"""Render a prepared TV at the scene's standard view angle (Blender 4.5, MIT).

Usage: blender -b --factory-startup --disable-autoexec --python render_tv_standard.py -- ID PREPARED.glb
ID is `panasonic`, `retro`, `pvm` or `oldtv`. The camera reproduces the native renderer's own projection
(tools/slotlaunch/psx.h): a pinhole camera 1200 units from the floor point under the cabinet's
centre, elevated PHI above the floor, with the cabinet turned YAW about the vertical axis, so a
TV rendered here and a console drawn by the native renderer share one perspective and one
floor plane. One native unit is RENDER_SCALE pixels in the image.

Writes build/slotted-presentation/<id>-render.png and <id>-source.json (live-glass quad, floor
contact point and footprint, in image pixels) for tools.themebuild.television. Source models are
the already-prepared blank-glass GLBs; no broadcast image is involved.
"""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
IDENT, PREPARED = sys.argv[sys.argv.index('--') + 1], Path(sys.argv[sys.argv.index('--') + 2])
PHI = math.radians(35)       # PSX_PHI: camera elevation
YAW = math.radians(-22)      # southwest TV turn; home consoles use the opposite +22 degrees
DISTANCE = 1200.0            # psx_project's perspective distance
RENDER_SCALE = 2             # image pixels per native unit
SIZE = (1800, 1500)
# Native height of each cabinet (units): chosen so the live glass stays readable at the standard angle.
HEIGHT = dict(panasonic=262.0, retro=238.0, pvm=205.0, oldtv=190.0)   # on-screen cabinet height ~345 px of the 360 px scene
INSET = dict(panasonic=.09, retro=.05, pvm=.06, oldtv=.05)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(PREPARED))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:
    world = o.matrix_world.copy()
    o.parent = None
    o.data.transform(world)
    o.matrix_world = Matrix.Identity(4)
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
glass = next(o for o in meshes if o.name.startswith('Blank live CRT glass') or any(m and m.name.startswith('Blank live CRT glass') for m in o.data.materials))
points = [v.co.copy() for o in meshes for v in o.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
# The prepared Retro TV faces -Y and sits on the floor; the Panasonic is authored the same way.
# Re-centre both on their footprint, floor at z = 0, then scale to native units.
source_size = list(high-low)
k = HEIGHT[IDENT] / (high.z - low.z)
place = Matrix.Scale(k, 4) @ Matrix.Translation(-Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z)))
for o in meshes:
    o.data.transform(place)
    o.data.update()
points = [v.co.copy() for o in meshes for v in o.data.vertices]
low = Vector([min(p[i] for p in points) for i in range(3)])
high = Vector([max(p[i] for p in points) for i in range(3)])
# Front plane of the glass (faces -Y): bounding rectangle and its inset.
base_points=[Vector((p.x,p.y,0)) for p in points if p.z<=low.z+4.0]
front = [v.co.copy() for p in glass.data.polygons if p.normal.y < -.8 for v in (glass.data.vertices[i] for i in p.vertices)]
assert front, 'glass has no camera-facing faces'
gx0, gx1 = min(v.x for v in front), max(v.x for v in front)
gz0, gz1 = min(v.z for v in front), max(v.z for v in front)
gy = min(v.y for v in front)
dx, dz = (gx1 - gx0) * INSET[IDENT], (gz1 - gz0) * INSET[IDENT]
def depth_at(x, z):
    """Median depth of the curved glass near an inset corner, so the quad lies on the glass, not in front of it."""
    near = sorted(v.y for v in front if abs(v.x - x) < (gx1 - gx0) * .08 and abs(v.z - z) < (gz1 - gz0) * .08)
    return near[len(near) // 2] if near else gy


corners = [(gx0 + dx, gz1 - dz), (gx1 - dx, gz1 - dz), (gx1 - dx, gz0 + dz), (gx0 + dx, gz0 + dz)]
quad_model = [Vector((x, depth_at(x, z), z)) for x, z in corners]
# Turn every cabinet about the vertical axis through its footprint centre. Native yaw -22 moves the
# front toward screen-left; in this frame (front = -Y) that is a -22 degree turn about +Z.
turn = Matrix.Rotation(YAW, 4, 'Z')
for o in meshes:
    o.data.transform(turn)
    o.data.update()
quad_model = [turn @ v for v in quad_model]
base_points=[turn @ v for v in base_points]
footprint = [turn @ Vector((x, y, 0)) for x, y in ((low.x, low.y), (high.x, low.y), (high.x, high.y), (low.x, high.y))]

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = SIZE
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = 'AgX'
background = bpy.data.worlds.new('Neutral studio')
background.use_nodes = True
background.node_tree.nodes['Background'].inputs[0].default_value = (.4, .44, .5, 1)
background.node_tree.nodes['Background'].inputs[1].default_value = .4
scene.world = background
camera_data = bpy.data.cameras.new('Standard view camera')
camera = bpy.data.objects.new('Camera', camera_data)
scene.collection.objects.link(camera)
camera.location = Vector((0, -math.cos(PHI), math.sin(PHI))) * DISTANCE
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'PERSP'
camera_data.clip_start = 10.0
camera_data.clip_end = 100000.0
camera_data.sensor_fit = 'HORIZONTAL'
camera_data.sensor_width = 36.0
camera_data.lens = RENDER_SCALE * DISTANCE * camera_data.sensor_width / SIZE[0]
camera_data.shift_y = (HEIGHT[IDENT] * .5 * math.cos(PHI) * RENDER_SCALE) / SIZE[0]
scene.camera = camera
target = Vector((0, 0, HEIGHT[IDENT] * .5))
for name, offset, energy, area in [('Key', (-.6, -.8, 1.1), 90, .8), ('Fill', (.7, -.3, .7), 45, .9)]:
    scale = HEIGHT[IDENT] / .4
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy * scale ** 2          # geometry x scale needs energy x scale^2 for equal exposure
    light.shape = 'DISK'
    light.size = area * scale
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = target + Vector(offset) * scale
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()
render = ROOT / 'build/slotted-presentation' / f'{IDENT}-render.png'
render.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(render)
bpy.context.view_layer.update()
if '--registration-only' not in sys.argv:
    bpy.ops.render.render(write_still=True)


def pixel(v):
    p = world_to_camera_view(scene, camera, v)
    return [p.x * SIZE[0], (1 - p.y) * SIZE[1]]


quad = [pixel(v) for v in quad_model]
base = pixel(Vector((0, 0, 0)))
feet = [pixel(v) for v in footprint]
contact=max((pixel(v) for v in base_points),key=lambda p:p[1])
profile = json.loads((ROOT / 'build/slotted-presentation' / f'{IDENT}-source.json').read_text()) if (ROOT / 'build/slotted-presentation' / f'{IDENT}-source.json').exists() else {}
profile.update(quad_pixels=quad, base_pixels=base, footprint_pixels=feet, contact_pixels=contact, render_scale=RENDER_SCALE, native_height=HEIGHT[IDENT],
               source_size_metres=source_size,
               view=dict(elevation_degrees=35, yaw_degrees=-22, distance=DISTANCE, projection='perspective, matches slotlaunch/psx.h'))
profile['changes'] = [c for c in profile.get('changes', []) if 'render' not in c.lower() and 'inset' not in c.lower()] + [
    'Standard three-quarter studio render (35 degree elevation, 22 degree turn, perspective matching the native renderer), transparent background',
    'Live screen inset %d%% inside the camera-facing glass, projected onto the angled glass' % round(INSET[IDENT] * 100)]
(ROOT / 'build/slotted-presentation' / f'{IDENT}-source.json').write_text(json.dumps(profile, indent=2) + '\n')
print('TV RENDERED', IDENT, 'quad', [[round(c) for c in q] for q in quad], 'base', [round(c) for c in base])
