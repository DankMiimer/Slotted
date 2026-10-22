"""Prepare the selected CC BY Panasonic TV; run in Blender with autoexec disabled.

Usage: blender -b --disable-autoexec --python import_tv.py -- SOURCE.glb
The source's broadcast-image screen material is replaced, never redistributed.
"""
import hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(sys.argv[sys.argv.index('--')+1])
OUT=ROOT/'theme/art-book-slot/_slot/stage/tv'
PREPARED=ROOT/'third_party/models/damiantoons-panasonic'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
screen=None
for o in meshes:
    name=o.parent.name if o.parent else o.name
    world=Matrix.Scale(.01,4)@o.matrix_world
    o.parent=None;o.matrix_world=world;o.name=name.replace('_',' ')
    if any(m and m.name=='TVScreen' for m in o.data.materials):screen=o
if screen is None:raise ValueError('Expected the authored TVScreen mesh')
material=bpy.data.materials.new('Blank live CRT glass');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value=(.012,.018,.018,1)
shader.inputs['Roughness'].default_value=.3
screen.data.materials.clear();screen.data.materials.append(material)
# Export only retained materials/images. The source's TV programme images are
# disconnected before export, along with their normal/roughness textures.
PREPARED.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=screen
bpy.ops.export_scene.gltf(filepath=str(PREPARED/'model.glb'),export_format='GLB',use_selection=True,
    export_cameras=False,export_lights=False,export_animations=False,export_extras=False)

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.44,.5,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.4;scene.world=world
camera_data=bpy.data.cameras.new('Near front readable camera');camera=bpy.data.objects.new('Camera',camera_data)
scene.collection.objects.link(camera);camera.location=(-.07,-1.8,.31)
target=Vector((0,.18,.226));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=.51;scene.camera=camera
for name,location,energy,size in [('Key',(-.6,-.8,1.1),90,.8),('Fill',(.7,-.3,.7),45,.9)]:
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size
    obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=location
    obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler()
OUT.mkdir(parents=True,exist_ok=True)
render=ROOT/'build/slotted-presentation/panasonic-render.png';scene.render.filepath=str(render)
bpy.ops.render.render(write_still=True)
points=[screen.matrix_world@v.co for v in screen.data.vertices]
x0,x1=min(v.x for v in points),max(v.x for v in points)
z0,z1=min(v.z for v in points),max(v.z for v in points)
inset=.09;dx=(x1-x0)*inset;dz=(z1-z0)*inset;y=min(v.y for v in points)
quad=[]
for x,z in [(x0+dx,z1-dz),(x1-dx,z1-dz),(x1-dx,z0+dz),(x0+dx,z0+dz)]:
    projected=world_to_camera_view(scene,camera,Vector((x,y,z)))
    quad.append([projected.x*960,(1-projected.y)*960])
profile=dict(name='Panasonic CRT TV (1990s)',author='DamianToons',
    source='https://sketchfab.com/3d-models/panasonic-crt-tv-1990s-45f7728e4f534d9393ef1d681137b6d9',
    license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    prepared_sha256=hashlib.sha256((PREPARED/'model.glb').read_bytes()).hexdigest(),
    quad_pixels=quad,
    changes=['Original scale normalized by 0.01','Broadcast screen materials/images excluded',
             'Blank live glass material','Near front studio render with transparent background',
             'Live screen inset 9% for the curved glass/bezel'])
(ROOT/'build/slotted-presentation/panasonic-source.json').write_text(json.dumps(profile,indent=2)+'\n')
print('Rendered Panasonic TV. Finish with python -m tools.themebuild.television')
