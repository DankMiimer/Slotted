"""Prepare dark_igorek's licensed PlayStation, Blender 4.5 -t 1 (MIT code).

Source scene is opened with scripts disabled. Keep only the console collection;
close the source lid, register its actual hinge and spindle, remove all images.
"""
import bpy,bmesh,json,sys,hashlib,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models,ps1
from import_authored import save
from import_snes import planar
from handhelds import panel_normals

URL='https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245'
AUTHOR='dark_igorek'
PARTS={'Ps1_body':('PS1 enclosure','ps1case',5800),
       'Ps1_body_details':('PS1 controls and fittings','ps1case',2500),
       'ps1_cap':('PS1 disc lid','ps1case',2400),
       'body_inner':('PS1 disc well','ps1well',1200),
       'laser_disc_rotor':('PS1 spindle','ps1drive',500),
       'laser_plate':('PS1 optical pickup','ps1drive',550),
       'ps1_plugs':('PS1 socket interiors','ps1socket',None)}

def main():
    args=sys.argv[sys.argv.index('--')+1:];source=Path(args[0]).resolve()
    out=Path(args[1]).resolve() if len(args)>1 else ROOT/'third_party/models/darkigorek-ps1'
    bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
    parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(c.name=='ps1' for c in o.users_collection)]
    assert {o.name for o in parts}==set(PARTS)
    lid=bpy.data.objects['ps1_cap'];opened=float(lid.rotation_euler.x)
    assert abs(opened+.87266475)<1e-5
    lid.rotation_euler.x=0;bpy.context.view_layer.update()
    def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
    allp=[p for o in parts for p in points(o)]
    lo=Vector([min(p[i] for p in allp) for i in range(3)])
    hi=Vector([max(p[i] for p in allp) for i in range(3)])
    span=hi-lo;scale=Vector((.270/span.x,.188/span.y,.060/span.z))
    hub=bpy.data.objects['laser_disc_rotor']
    centre=(lo+hi)/2;centre.y=hub.matrix_world.translation.y
    transform=Matrix.Diagonal((*scale,1))@Matrix.Translation(-centre)
    def native_mm(p):
        v=transform@p;return [v.x*1000,v.z*1000,-v.y*1000]
    hinge=native_mm(lid.matrix_world.translation)
    hub_anchor=transform@hub.matrix_world.translation
    hp=points(hub);disc=hub.matrix_world.translation.copy()
    # Label plane clears the measured spindle's outer flange; the bore leaves
    # its centre visible. 1.2-mm disc thickness is separate from console scale.
    disc.z=max(p.z for p in hp)+.0004
    reg=dict(hinge_xyz_mm=hinge,disc_label_xyz_mm=native_mm(disc),
             lid_top_y_mm=max(native_mm(p)[1] for p in points(lid)),
             source_lid_open_degrees=-opened*180/3.141592653589793,
             closed_source_whd=[span.x,span.z,span.y],
             physical_axis_scale=list(scale),
             reference='Sony SCPH-1001 instruction manual page 18: 270 x 60 x 188 mm; RCA video/audio, RFU DC, SERIAL I/O and AV MULTI OUT',
             reference_url='https://www.manualslib.com/manual/3466089/Sony-Playstation-Scph-1001.html?page=18',
             pickup_reference='iFixit original SCPH-1001 drive replacement guide 1595, photographs in PDF pages 3-5; pickup behind spindle',
             pickup_reference_url='https://documents.cdn.ifixit.com/pdf/ifixit/guide_1595_en.pdf',
             pickup_registration_degrees=90,
             uncertainty='Source hinge/spindle registration and individual moulding dimensions are inferred from authored geometry, not OEM metrology')
    for o in list(bpy.context.scene.objects):
        if o not in parts:bpy.data.objects.remove(o,do_unlink=True)
    models.M.clear();ps1.palette(models)
    for o in parts:
        original=o.name;name,color,budget=PARTS[original]
        o.data=o.data.copy();o.data.transform(transform@o.matrix_world)
        if original in ('laser_plate','body_inner'):
            # The source mixes early RCA rear ports with a later right-facing
            # optical unit. Register the complete cover/pickup behind the
            # spindle for the chosen early SCPH-1001 layout, without mirroring.
            o.data.transform(Matrix.Translation(hub_anchor)@Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Translation(-hub_anchor))
        o.parent=None;o.matrix_world=Matrix.Identity(4);o.name=name;o.data.name=name
        for key in list(o.keys()):del o[key]
        o.data.materials.clear();o.data.materials.append(models.M[color])
        for p in o.data.polygons:p.material_index=0
        for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
        for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
        o['slotters_material']=color;o['source_creator']=AUTHOR;o['source_url']=URL
        o['source_licence']='CC-BY-4.0';o['printed']=False
        o['hinged']=original=='ps1_cap';o['dimension_critical']=True;o['outline']=False
        if budget:o['runtime_triangle_budget']=budget
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        bm.to_mesh(o.data);bm.free();o.data.update()
        planar(o);panel_normals(models,o)
    out.mkdir(parents=True,exist_ok=True);save(parts,out/'model.glb')
    report=dict(hardware='PlayStation SCPH-1001 exterior and early optical-unit orientation',
        author=AUTHOR,url=URL,licence='CC-BY-4.0',
        licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name,source_file_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        archive_sha256='0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845',
        licence_evidence='Original Sketchfab API metadata and original-format download dialog, checked 16 October 2026',
        registration=reg,modifications=['Keep only seven console meshes; exclude monitor, controllers, cables, lights, cameras',
            'Close the explicitly 50-degree source lid; bake world transforms',
            'Register closed envelope to 270 x 60 x 188 mm; retain actual lid hinge and spindle location',
            'Retain early RCA/RFU/serial/multi-out rear; rotate source optical pickup and its complete cover 90 degrees behind spindle to match early layout',
            'Remove all images, UVs and material graphs; semantic palette and stable panel normals',
            'Retain full prepared geometry with separate runtime fitting budgets'])
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print('REGISTRATION',json.dumps(reg),flush=True)

if __name__=='__main__':main()
