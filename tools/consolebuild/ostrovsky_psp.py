"""Ilya Ostrovsky's textured Sony PSP and a separately hinged UMD cover.

Blender 4.5, --factory-startup --disable-autoexec. Source and full textured
master stay intact in research/build. The runtime keeps source detail/UVs;
only the staging ground is removed. Processing code MIT, source CC BY 4.0.
"""
import json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb

URL='https://sketchfab.com/3d-models/sony-psp-dca89d10ec304d0cab76837750df7761'
Q=480/169.4
DOOR_HALF_WIDTH=38.0
HINGE=(0,-36.5,-10.6)  # native-axis millimetres: x, height, front
SEAT=(0,.4,-8.2)       # rear-facing label; shell extends 4.2 mm forward


def clipped_object(source,name,planes):
    """Clip source triangles without decimation, interpolating UVs/normals.

    The author supplied a single connected rear moulding. Split at the two
    straight cover seams; preserve every face outside those narrow cuts.
    Coordinates here are millimetres: x right, y rear, z up.
    """
    mesh=source.data;mesh.calc_loop_triangles();layer=mesh.uv_layers.active
    points=[];normals=[];uvs=[];faces=[];materials=[]
    for tri in mesh.loop_triangles:
        polygon=[(mesh.vertices[mesh.loops[i].vertex_index].co.copy(),
                  mesh.corner_normals[i].vector.copy(),layer.data[i].uv.copy()) for i in tri.loops]
        for axis,limit,sign in planes:
            result=[]
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                da=(a[0][axis]-limit)*sign;db=(b[0][axis]-limit)*sign
                if da>=-1e-6:result.append(a)
                if (da>1e-6 and db<-1e-6) or (db>1e-6 and da<-1e-6):
                    t=da/(da-db)
                    result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
            polygon=result
            if not polygon:break
        for j in range(1,len(polygon)-1):
            triangle=[polygon[0],polygon[j],polygon[j+1]]
            if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-7:continue
            first=len(points);faces.append((first,first+1,first+2));materials.append(tri.material_index)
            for p,n,uv in triangle:points.append(p);normals.append(n.normalized());uvs.append(uv)
    data=tb.bpy.data.meshes.new(name);data.from_pydata(points,[],faces);data.update()
    for material in mesh.materials:data.materials.append(material)
    layer=data.uv_layers.new(name='Source UVs')
    for i,uv in enumerate(uvs):layer.data[i].uv=uv
    for p,m in zip(data.polygons,materials):p.material_index=m;p.use_smooth=True
    data.normals_split_custom_set(normals)
    obj=tb.bpy.data.objects.new(name,data);tb.bpy.context.collection.objects.link(obj)
    obj['source_part']='bottompart_low';return obj


def box(name,centre,size,material):
    # Original concealed drive/holder fittings, matching the old mechanism.
    bpy=tb.bpy;bpy.ops.mesh.primitive_cube_add(size=1,location=centre)
    o=bpy.context.object;o.name=name;o.scale=size;bpy.context.view_layer.update()
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    o.data.materials.append(material);return o


def main():
    source=Path(sys.argv[sys.argv.index('--')+1]);objects=tb.import_source(source)
    bpy=tb.bpy;bpy.data.objects.remove(objects.pop('ground'),do_unlink=True)
    for o in objects.values():o.data.transform(Matrix.Rotation(math.pi/4,4,'X'))
    lo,hi=tb.bounds(objects.values());centre=(lo+hi)/2;mm=169.4/(hi.x-lo.x)
    for o in objects.values():o.data.transform(Matrix.Scale(mm,4)@Matrix.Translation(-centre));o.data.update()
    lo,hi=tb.bounds(objects.values());source_size=list(hi-lo)
    work=tb.ROOT/'build/textured/psp';work.mkdir(parents=True,exist_ok=True)
    # Complete, registered original before the cover split, with every source map.
    tb.export_master_glb(list(objects.values()),work/'registered-source-mm.glb')
    rear=objects.pop('bottompart_low')
    moving=clipped_object(rear,'PSP UMD cover',[(0,-DOOR_HALF_WIDTH,1),(0,DOOR_HALF_WIDTH,-1)])
    left=clipped_object(rear,'PSP rear left wing',[(0,-DOOR_HALF_WIDTH,-1)])
    right=clipped_object(rear,'PSP rear right wing',[(0,DOOR_HALF_WIDTH,1)])
    bpy.data.objects.remove(rear,do_unlink=True)
    names={'screen_low':'PSP LCD glass','toppart_low':'PSP front housing',
           'middlepart_low':'PSP perimeter and fittings','cap_low':'PSP Memory Stick cover'}
    kept=[left,right,moving]
    for name,o in objects.items():
        o['source_part']=name;o.name=names.get(name,'PSP '+name.replace('_low',''));kept.append(o)
    black=bpy.data.materials.new('Slot UMD interior');black.use_nodes=True
    black.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.008,.009,.012,1)
    metal=bpy.data.materials.new('Slot UMD holder');metal.use_nodes=True
    metal.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.35,.38,.4,1)
    kept.append(box('PSP UMD drive floor',(0,3.4,.4),(72,.7,67),black))
    # Opaque inner face gives the opened cover thickness without retaining a
    # second closed housing behind it. These are original hidden fittings.
    # The central printed rear is at y=9.708 mm (the outer grip bulges reach
    # 13 mm). Keep the lining below that measured panel, never over its logo.
    inside=box('PSP UMD cover inside',(0,9.2,0),(74,.5,70),black);kept.append(inside)
    rails=[box('PSP UMD holder rail '+str(i),(x,9.0,-2.4),(1.2,.8,48),metal) for i,x in enumerate((-33.5,33.5))]
    rails.append(box('PSP UMD holder stop',(0,9.0,-34.1),(60,.8,1.2),metal));kept+=rails
    flags={o.name:dict(role='paint') for o in [objects['toppart_low'],left,right,moving]}
    flags[objects['screen_low'].name]=dict(role='lcd')
    for o in [moving,inside,*rails]:o['hinged']=True;flags.setdefault(o.name,{})['moving']=True
    tb.to_native(kept,(0,0,0),1,Q)
    registration=dict(model='psp',adapter='ostrovsky_psp.py',author='Ilya Ostrovsky',title='Sony PSP',
        url=URL,licence='CC-BY-4.0',licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name,source_sha256=tb.sha256(source),mm_per_source_unit=mm,native_units_per_mm=Q,
        scale_basis='Uniform, 169.4 mm complete source width; preserve artist height/depth',source_size_mm=source_size,
        source_triangles=58250,removed_source_parts=['ground (50 triangles)'],decimation=False,
        door_split_x_mm=[-DOOR_HALF_WIDTH,DOOR_HALF_WIDTH],hinge_native=[v*Q for v in HINGE],
        umd_label_native=[v*Q for v in SEAT],umd_size_mm=[64,65,4.2],
        hinge_uncertainty='Source has no mechanism; lower cover hinge and hidden holder are fitted approximations',
        spec=dict(ry=source_size[2]*Q/2,depth=source_size[1]*Q/2,slot=HINGE[2]*Q),
        modifications=['Remove staging ground; undo source 45-degree display tilt',
            'Retain full console detail without decimation; split connected rear cover at straight seams',
            'Add original concealed drive floor, inner cover and independently moving UMD holder',
            'Clear baked home screen for live LCD metadata',
            'Reduce 4096px albedo to 2048px; original maps/master preserved',
            'Source albedo with simple lighting; normal/roughness/metallic maps not rendered'])
    tb.write_corners(kept,work,flags)
    (work/'registration.json').write_text(json.dumps(registration,indent=2)+'\n')
    tb.export_master_glb(kept,work/'model-master.glb')
    target=tb.ROOT/'theme/art-book-slot/_slot/consoles/psp'
    provenance=dict(source_creator='Ilya Ostrovsky',source_licence='CC-BY-4.0',source_url=URL)
    for name,physical in [('model.glb',False),('model-master.glb',False),('model-physical.glb',True)]:
        tb.export_geometry_glb(kept,target/name,Q,physical=physical,provenance=provenance)
    print('PSP PREPARED',json.dumps(registration),flush=True)


if __name__=='__main__':main()
