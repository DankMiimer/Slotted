"""Prepare Dave Parker's fit-tested GBA shell with photographed exterior details.

Blender 4.5 -t 1. MIT processing; the two CAD shell halves retain CC BY 4.0.
No downloaded code is executed: binary STL data is read directly.
"""
import bpy,bmesh,json,sys,struct,hashlib,math
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models
from handhelds import panel_normals
from import_authored import save
URL='https://www.printables.com/model/190861-gameboy-advance-cartridge-gba-cart'
FILES=('printables_190861_gba_cart_top.stl','printables_190861_gba_cart_bottom.stl')

def profile_mm(w,h,r,centre=(0,0)):
    return [(x/10,y/10) for x,y in models.rounded_rect(w,h,(r,)*4,centre,12)]

def cut_mm(o,profile,top,depth):models.cut_profile(o,'GBA physical moulding',profile,top/10,depth/10)

def fill_mm(o,profile,top,depth):
    filler=models.contour_shell('Restore replacement cutout',profile,top/10,depth/10,models.M['darkgrey'],0)
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Restore replacement face','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=filler
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(filler,do_unlink=True)

def read_stl(path,top):
    raw=path.read_bytes();count=struct.unpack_from('<I',raw,80)[0];assert len(raw)==84+count*50
    vertices=[];faces=[]
    for i in range(count):
        coords=struct.unpack_from('<9f',raw,84+50*i+12);indices=[]
        for j in range(0,9,3):
            x,y,z=coords[j:j+3]
            if top:x,z=-x,7.7-z
            # Physical x right/y up/z label; convert to Blender x/rear/up.
            indices.append(len(vertices));vertices.append((x*.001,-(z-3.85)*.001,(y-17.2)*(34.5/34.4)*.001))
        faces.append(indices)
    mesh=bpy.data.meshes.new('GBA fitted CAD half');mesh.from_pydata(vertices,[],faces);mesh.update()
    o=bpy.data.objects.new('GBA front shell' if top else 'GBA rear shell',mesh);bpy.context.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o.data.materials.append(models.M['darkgrey'])
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    o['slotters_material']='darkgrey';o['source_creator']='Dave Parker';o['source_url']=URL
    o['source_licence']='CC-BY-4.0';o['printed']=False;o['hinged']=False
    o['dimension_critical']=True;o['outline']=False
    return o

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    source=Path(args[0]).resolve() if args else ROOT/'research/hardware-review/downloads'
    out=Path(args[1]).resolve() if len(args)>1 else ROOT/'third_party/models/dave-gba'
    models.PRECISE=True;models.setup();front,rear=[read_stl(source/n,i==0) for i,n in enumerate(FILES)]
    # Keep the known native/shelf label crop. Replacement CAD's recess is filled
    # first, then cut to the existing 44.3 x 23-mm well at (0,-2).
    fill_mm(front,profile_mm(44.2,23.35,1,(0,-1.90)),3.85,.55)
    cut_mm(front,profile_mm(44.3,23,1,(0,-2)),3.95,.5)
    # Original shell photograph: a shallow bowed/crescent groove, not the
    # replacement print's rounded rectangular grip pocket. C photographic fit.
    fill_mm(front,profile_mm(50.25,4.35,2,(0,13.18)),3.85,.75)
    xs=[-25+50*i/64 for i in range(65)]
    upper=[(x/10,(12+3.8*(1-(x/25)**2))/10) for x in xs]
    lower=[(x/10,(12+2.5*(1-(x/25)**2))/10) for x in reversed(xs)]
    cut_mm(front,upper+lower,3.95,.65)
    # Recessed identifying letters are real geometry; their placement is an
    # original reconstruction from a front photograph, not a logo image trace.
    cutter=models.text('GAME BOY ADVANCE',(0,1.12,.385),.25,models.M['darkgrey'],True,width=4.1)
    cutter.data.extrude=.00012
    bpy.ops.object.select_all(action='DESELECT');cutter.select_set(True);bpy.context.view_layer.objects.active=cutter
    bpy.ops.object.convert(target='MESH');cutter=bpy.context.object
    bpy.context.view_layer.objects.active=front
    mod=front.modifiers.new('Recessed GBA crown lettering','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Original rear photograph: small moulded identifier panel and the round
    # injection mark below it. Existing STL already supplies screw/guide cuts.
    cut_mm(rear,profile_mm(26,10,.7,(0,6.3)),-3.65,.3)
    cut_mm(rear,[(2*math.cos(i*math.tau/48)/10,(-2.5+2*math.sin(i*math.tau/48))/10) for i in range(48)],-3.72,.2)
    for o in (front,rear):
        # Boolean n-gons can span a recess wall and a planar skin. Register
        # normals on the actual triangles that will be exported, so a wall
        # normal cannot bleed diagonally across the lower label surround.
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        o.data.update()
        panel_normals(models,o)
        normals=[tuple(n.vector) for n in o.data.corner_normals]
        for p in o.data.polygons:
            if abs(p.normal.y)>.9999:
                p.use_smooth=False
                for li in p.loop_indices:normals[li]=tuple(p.normal)
        o.data.normals_split_custom_set(normals)
    out.mkdir(parents=True,exist_ok=True);save([front,rear],out/'model.glb')
    report=dict(author='Dave Parker',url=URL,licence='CC-BY-4.0',
        licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_files={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in FILES},
        source_scad_sha256=hashlib.sha256((source/'printables_190861_gba_cart.scad').read_bytes()).hexdigest(),
        source_assembly='Top rotate Y 180 degrees then translate z 7.7; bottom unchanged',
        source_assembled_wht_mm=[60,34.4,7.7],prepared_wht_mm=[60,34.5,7.7],
        evidence='Printables author reports original fit tests in GBA, SP and DS Lite; replacement CAD, not OEM metrology',
        inspection_references=['https://commons.wikimedia.org/wiki/File:Nintendo-Game-Boy-Advance-Cartridge.jpg',
            'https://commons.wikimedia.org/wiki/File:Game_Boy_Advance_game_cartridges_-_rear_view.jpg'],
        modifications=['Assemble actual supplied halves and normalize height by +0.291% to retain the shelf contract',
            'Restore replacement label/grip pockets; cut existing native 44.3 x 23 label well and photographic bowed grip groove',
            'Recess original crown lettering; original rear identifier recess and injection mark',
            'Keep original guide rails, keyed mode slots, interlocks, screw opening and tapered front skin',
            'Stable crease/planar normals; exclude all images, UVs and downloaded code'],
        uncertainty='Fit-tested replacement CAD plus photographic exterior reconstruction; small moulding dimensions remain C/D estimates')
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    license_path=ROOT/'research/hardware-review/independent/BOSL-LICENSE.txt'
    if license_path.exists():(out/'BOSL-LICENSE.txt').write_bytes(license_path.read_bytes())
    print('GBA CAD source prepared',json.dumps(report['prepared_wht_mm']),flush=True)

if __name__=='__main__':main()
