"""Prepare dark_igorek's Sony PVM-1341 as a blank-glass TV (CC BY 4.0).

Blender 4.5 --factory-startup --disable-autoexec; source opened use_scripts=False.
Keep source materials/detail, exclude the loose power cord/plug and all consoles.
"""
import json,sys
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb
URL='https://sketchfab.com/3d-models/sony-pvm-1341-sony-playstation-5f80311f1a4646ef9673f20ee6dc6245'


def components(obj):
    """Physical islands, welding only coincident exported normal/UV corners."""
    mesh=obj.data;parent=list(range(len(mesh.vertices)));positions={}
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    def union(a,b):parent[find(a)]=find(b)
    for v in mesh.vertices:
        key=tuple(round(x,6) for x in v.co)
        if key in positions:union(v.index,positions[key])
        else:positions[key]=v.index
    for p in mesh.polygons:
        for v in p.vertices:union(p.vertices[0],v)
    result={}
    for p in mesh.polygons:result.setdefault(find(p.vertices[0]),[]).append(p.index)
    return list(result.values())


def main():
    source=Path(sys.argv[sys.argv.index('--')+1]);bpy=tb.bpy
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),use_scripts=False,load_ui=False)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(c.name=='Sony PVM' for c in o.users_collection)]
    assert len(meshes)==5
    for o in list(bpy.context.scene.objects):
        if o not in meshes:bpy.data.objects.remove(o,do_unlink=True)
    for o in meshes:
        world=o.matrix_world.copy();o.parent=None;o.data=o.data.copy();o.data.transform(world);o.matrix_world=Matrix.Identity(4);o.data.update()
    main=bpy.data.objects['main_body'];front=bpy.data.objects['front_panel'];front_lo,front_hi=tb.bounds([front])
    remove=set();removed=[]
    for group in components(main):
        points=[main.data.vertices[v].co for i in group for v in main.data.polygons[i].vertices]
        low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
        if low[0]<front_lo.x-.02 and high[2]<front_hi.z*.1:
            remove.update(group);removed.append(dict(polygons=len(group),bounds=[low,high]))
    assert len(removed)==6,'Expected cable, plug, strain relief and three contact islands'
    cabinet=tb.copy_triangles(main,'PVM cabinet and feet',lambda tri:tri.polygon_index not in remove)
    bpy.data.objects.remove(main,do_unlink=True);meshes.remove(main);meshes.append(cabinet)
    assembly=bpy.data.objects['glass_and_fence']
    glass_faces=max(components(assembly),key=len);glass_set=set(glass_faces)
    glass=tb.copy_triangles(assembly,'Blank live CRT glass',lambda tri:tri.polygon_index in glass_set)
    other=tb.copy_triangles(assembly,'PVM speaker mesh and indicator lenses',lambda tri:tri.polygon_index not in glass_set)
    bpy.data.objects.remove(assembly,do_unlink=True);meshes.remove(assembly);meshes.extend([glass,other])
    lo,hi=tb.bounds([glass]);assert hi.x-lo.x>.25 and hi.z-lo.z>.20,'Wrong glass island selected'
    blank=bpy.data.materials.new('Blank live CRT glass');blank.use_nodes=True
    shader=blank.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=(.012,.018,.018,1);shader.inputs['Roughness'].default_value=.3
    glass.data.materials.clear();glass.data.materials.append(blank)
    for p in glass.data.polygons:p.material_index=0
    low,high=tb.bounds(meshes);centre=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    for o in meshes:o.data.transform(Matrix.Translation(-centre));o.data.update()
    family=tb.ROOT/'third_party/models/darkigorek-pvm';family.mkdir(parents=True,exist_ok=True)
    for o in meshes:
        o['source_creator']='dark_igorek';o['source_licence']='CC-BY-4.0';o['source_url']=URL
    tb.export_master_glb(meshes,family/'model.glb')
    profile=dict(id='pvm',name='Sony PVM-1341',author='dark_igorek',source=URL,license='CC BY 4.0',
        license_url='https://creativecommons.org/licenses/by/4.0/',source_sha256=tb.sha256(source),prepared_sha256=tb.sha256(family/'model.glb'),
        archive_sha256='0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845',
        source_size_metres=list(high-low),removed_power_islands=removed,glass_polygons=len(glass_faces),
        changes=['Keep complete PVM cabinet, controls, feet, rear connections and source maps without decimation',
            'Remove the loose external power cable and plug (joined to source main_body)',
            'Separate curved glass from speaker/indicators; opaque blank glass for live metadata',
            'Exclude PSX, controllers, cables, stage and lights; centre cabinet on its own floor'])
    work=tb.ROOT/'build/slotted-presentation';work.mkdir(parents=True,exist_ok=True)
    (work/'pvm-source.json').write_text(json.dumps(profile,indent=2)+'\n')
    print('PVM PREPARED',json.dumps(profile),flush=True)


if __name__=='__main__':main()
