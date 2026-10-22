"""Neutral orthographic review of the physical cartridge media (Blender 4.5, MIT).

Renders each exported media GLB alone (front, rear, side, top, bottom and a
three-quarter view) and seated in its console. Independent of the authoring
scene; native GLES motion comes from offline-preview.c.
"""
import math
import os
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media  # noqa: E402
from snes import SPECS as SNES
from n64 import SPECS as N64

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/media/media-review'
CONSOLES = ROOT/'theme/art-book-slot/_slot/consoles'
SPECS = {'md': (-53, 10, 48, 1.7), 'md-jp': (-53, 10, 48, 1.7), 'pico8': (-34, 12, 64, 1)}
SPECS.update({n:(s['slot']*s['scale'],s['entry']*s['scale'],s['seat_depth']*s['scale'],1) for n,s in (SNES|N64).items()})


def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)


def add(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    for o in objects:
        attr = o.data.color_attributes.active_color
        mat = bpy.data.materials.new('Neutral '+o.name); mat.use_nodes = True
        nodes = mat.node_tree.nodes; links = mat.node_tree.links; nodes.clear()
        diffuse = nodes.new('ShaderNodeBsdfDiffuse')
        if attr and len(attr.data):
            colour = nodes.new('ShaderNodeVertexColor'); colour.layer_name = attr.name
            links.new(colour.outputs['Color'], diffuse.inputs['Color'])
        output = nodes.new('ShaderNodeOutputMaterial'); links.new(diffuse.outputs[0], output.inputs['Surface'])
        o.data.materials.clear(); o.data.materials.append(mat)
    return objects


def render(path, direction, scale, target=Vector((0, 0, 0))):
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 16
    scene.cycles.use_denoising = True; scene.cycles.device = 'CPU'
    scene.render.resolution_x = 720; scene.render.resolution_y = 480
    scene.render.image_settings.file_format = 'PNG'; scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    if not scene.world: scene.world = bpy.data.worlds.new('Neutral world')
    scene.world.use_nodes = True; bg = scene.world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (.16, .17, .19, 1); bg.inputs[1].default_value = .9
    loc = target+Vector(direction).normalized()*30
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
    cam.rotation_euler = (target-loc).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale; cam.data.clip_end = 100; scene.camera = cam
    right = cam.rotation_euler.to_matrix()@Vector((1, 0, 0)); up = cam.rotation_euler.to_matrix()@Vector((0, 1, 0))
    bpy.ops.object.light_add(type='AREA', location=target+(loc-target)*.6-right*6+up*8)
    light = bpy.context.object; light.data.energy = 3000; light.data.size = 8
    light.rotation_euler = (target-light.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)


# Blender axes: x right, y = -front, z = up (project y). Media meshes face +z
# project (towards Blender -y), so a front view looks from -y.
VIEWS = {'front': (0, -1, 0), 'rear': (0, 1, 0), 'side': (1, 0, 0), 'top': (0, 0, 1),
         'bottom': (0, 0, -1), 'three-quarter': (.55, -.75, .45)}


def main():
    variants = os.environ.get('SLOT_MEDIA_VARIANTS', ' '.join(media.MEDIA)).split()
    for variant in variants:
        spec = media.MEDIA[variant]; folder = OUT/variant; folder.mkdir(parents=True, exist_ok=True)
        q = media.SCALES[spec['folder']]; w, h, t = spec['size']
        extent = max(w, h*1.5)*q*.01*1.12
        for view, direction in VIEWS.items():
            clear(); add(CONSOLES/spec['folder']/(spec['part']+'.glb'))
            render(folder/(view+'.png'), direction, extent)
        if spec['folder'] in SPECS:
            slot, entry, sink, ys = SPECS[spec['folder']]
            clear(); add(CONSOLES/spec['folder']/'model.glb')
            cart = add(CONSOLES/spec['folder']/(spec['part']+'.glb'))
            # Seated pose from cartridge_scene(): mid-plane at the slot centre,
            # bottom edge `sink` units below the entry plane.
            centre_y = h*q/2+entry*ys-sink
            for o in cart: o.matrix_world = Matrix.Translation((0, -slot*.01, centre_y*.01))@o.matrix_world
            render(folder/'seated.png', (.0, -1, .9), 6.4)
            render(folder/'seated-side.png', (1, 0, .12), 5.2, Vector((0, -slot*.01, 0)))


if __name__ == '__main__':
    main()
