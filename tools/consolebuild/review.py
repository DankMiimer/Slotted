"""Render exported meshes at matched orthographic cameras (Blender 4.5, MIT).

Neutral geometry review, independent of the procedural authoring scene. Native
GLES motion comes from offline-preview.c, not this renderer.
"""
import sys
import os
import math
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/exemplars'


def legacy_media(system):
    """Neutral reconstruction of fba7ffe's flat extruded runtime envelopes.

    There was no separate editable media mesh. These equations/alpha samples
    match cartridge_outline()/psp_slab() in the extracted original C source.
    """
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    if system in ('gb','gbc','gba'):
        im=bpy.data.images.load(str(OUT/f'before/theme/art-book-slot/_slot/shells/{system}.png'))
        width,height=im.size;pixels=im.pixels[:];left=[];right=[]
        for i in range(33):
            y=(height-1)*i//32;xs=[x for x in range(width) if pixels[4*((height-1-y)*width+x)+3]>240/255]
            if not xs:continue
            halfw={'gb':56,'gbc':64,'gba':72}[system]
            left.append(((2*min(xs)/width-1)*halfw,(1-2*y/height)*halfw*height/width))
            right.append(((2*(max(xs)+1)/width-1)*halfw,(1-2*y/height)*halfw*height/width))
        points=left+right[::-1];depth=9
    else:
        points=[];radius=85
        for i in range(65):
            a=math.radians(180+180*i/64)
            points.append((157*math.cos(a)*radius/162,(1-157*math.sin(a))*radius/162))
        points.append((157*radius/162,-112*radius/162))
        for i in range(33):
            t=i/32
            points.append(((314*(1-t)**2+324*t*(1-t)+10*t*t-162)*radius/162,
                           -(286*(1-t)**2+704*t*(1-t)+286*t*t-162)*radius/162))
        depth=16
    n=len(points);vertices=[(x*.01,-z*.01,y*.01) for z in (-depth/2,depth/2) for x,y in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new('Previous native media envelope');mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new('Previous slab reconstruction',mesh);bpy.context.collection.objects.link(o)
    mat=bpy.data.materials.new('Neutral previous media');mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.5,.5,.45,1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
    o.data.materials.append(mat)


def load(path):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    return add(path)


def add(path):
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    for o in objects:
        attr=o.data.color_attributes.active_color
        mat=bpy.data.materials.new('Neutral '+o.name);mat.use_nodes=True
        mat.node_tree.nodes.clear();nodes=mat.node_tree.nodes;links=mat.node_tree.links
        diffuse=nodes.new('ShaderNodeBsdfDiffuse')
        if attr and len(attr.data):
            colour=nodes.new('ShaderNodeVertexColor');colour.layer_name=attr.name
            links.new(colour.outputs['Color'],diffuse.inputs['Color'])
        else:diffuse.inputs['Color'].default_value=(.6**2.2,.6**2.2,.6**2.2,1)
        output=nodes.new('ShaderNodeOutputMaterial');links.new(diffuse.outputs[0],output.inputs['Surface'])
        o.data.materials.clear();o.data.materials.append(mat)
    return objects


def loaded_dmg(base):
    load(base/'gb/model.glb')
    objects=add(base/'gb/media.glb');q=168/90
    assert objects, 'Loaded DMG review needs its physical cartridge'
    # The label faces the rear, with its top level with the 148-mm housing.
    # The wall occludes the lower case in a true geometric render.
    transform=Matrix.Translation((0,9.098*q*.01,41.25*q*.01))@Matrix.Rotation(math.pi,4,'Z')
    for obj in objects:obj.matrix_world=transform@obj.matrix_world


def loaded_handheld(base,system):
    load(base/system/'model.glb');objects=add(base/system/'media.glb')
    if system=='gbc':
        q=168/78;transform=Matrix.Translation((0,2.6*q*.01,34*q*.01))@Matrix.Rotation(math.pi,4,'Z')
    else:
        q=224/82
        transform=Matrix(((1,0,0,0),(0,0,-1,-24.45*q*.01),(0,1,0,-26.03*q*.01),(0,0,0,1)))
    for o in objects:o.matrix_world=transform@o.matrix_world


def render(path,view,system,media=False):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=720;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.render.use_freestyle=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    if not scene.world:scene.world=bpy.data.worlds.new('Neutral world')
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.2,.2,.2,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    locations={'front':(0,-12,0),'rear':(0,12,0),'side':(12,0,0),'top':(0,0,12)}
    loc=Vector(locations[view]);bpy.ops.object.camera_add(location=loc);cam=bpy.context.object
    cam.rotation_euler=(-loc).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO'
    cam.data.ortho_scale=4.8 if system in ('gb','gbc') else 6.6 if system=='gba' else 5.6
    if media:cam.data.ortho_scale=2.6 if system in ('gbc','gba') else 2.0 if system=='gb' else 2.7
    scene.camera=cam
    # Same broad white key relative to the camera in every orthographic view.
    right=cam.rotation_euler.to_matrix()@Vector((1,0,0));up=cam.rotation_euler.to_matrix()@Vector((0,1,0))
    bpy.ops.object.light_add(type='AREA',location=loc*.55-right*3+up*4)
    light=bpy.context.object;light.data.energy=950;light.data.size=5
    light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)


def main():
    for version in os.environ.get('SLOT_REVIEW_VERSIONS','before after').split():
        if version not in ('before','after'):raise ValueError('Unknown review version: '+version)
        base=OUT/'before/theme/art-book-slot/_slot/consoles' if version=='before' else ROOT/'theme/art-book-slot/_slot/consoles'
        for system in os.environ.get('SLOT_REVIEW_SYSTEMS','gb psp').split():
            if system not in ('gb','psp','gbc','gba'):raise ValueError('Unknown review system: '+system)
            folder=OUT/version/system;folder.mkdir(parents=True,exist_ok=True)
            for view in ('front','rear','side','top'):
                load(base/system/'model.glb');render(folder/(view+'.png'),view,system)
            if version=='after' and system=='gb':
                loaded_dmg(base);render(folder/'rear-loaded.png','rear',system)
            if version=='after' and system in ('gbc','gba'):
                for view in ('rear','top','front'):
                    loaded_handheld(base,system);render(folder/(view+'-loaded.png'),view,system)
            for view in ('front','rear','side','top'):
                if (base/system/'media.glb').exists():load(base/system/'media.glb')
                else:legacy_media(system)
                render(folder/('media-'+view+'.png'),view,system,True)


if __name__=='__main__':main()
