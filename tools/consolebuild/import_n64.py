"""Source-specific N64 preparation. Blender 4.5 -t 1 --disable-autoexec (MIT).

Joseph Rohm's NUS-001 recreation (FBX, CC BY 4.0). The download stays in
research/n64; the prepared physical source has no images, UVs or controller.
"""
import bpy,bmesh,json,sys,hashlib,re
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models
from import_authored import save
from handhelds import panel_normals
from import_snes import clip_box,planar
from n64 import SPECS,BAY,bay_warp,palette,FLAPS

URL='https://sketchfab.com/3d-models/nintendo-64-0bec1e1ed1bf4a96af858008b72437a3'
AUTHOR='Joseph Rohm'
# Source objects by base name (Maya duplicates carry .001 and _N suffixes).
PARTS={'main_n64':('N64 upper enclosure','n64upper',None),
       'bottom_part':('N64 lower enclosure','n64lower',None),
       'top_part':('N64 memory expansion door','n64upper',None),
       'vent_part':('N64 cartridge bay grille','n64grille',400),
       'button_1':('N64 power slider','n64button',240),
       'button_2':('N64 reset button','n64button',240),
       'pCylinder4':('N64 controller port surrounds','n64port',None),
       'pCylinder5':('N64 controller port surrounds','n64port',None),
       'pCube5':('N64 controller port inserts','n64socket',None),
       'pCube8':('N64 controller port inserts','n64socket',None),
       'pCylinder1':('N64 front feet','n64foot',None),'pCylinder2':('N64 front feet','n64foot',None),
       'bottom_support':('N64 rear feet','n64foot',None),
       'back_divider':('N64 rear connector bay','n64socket',None),
       'port_base':('N64 multi-out surround','n64socket',None),
       'port':('N64 multi-out socket','black',None),
       'slot_cover_1':(FLAPS[0],'n64upper',None),
       'slot_cover_2':(FLAPS[1],'n64upper',None)}
# Project-mm moves (x right, y up, z front). The source multi-out sits 17-35 mm
# inside the rear bay; the widened slot's lining would cut through it, so it
# moves 14 mm rearward towards the rear face.
OFFSETS={'N64 multi-out surround':(0,0,-14),'N64 multi-out socket':(0,0,-14)}

def base(name):
    if name.startswith('slot_cover_'):return name.split('.')[0]
    return re.sub(r'(_\d+)?(\.\d+)?$','',name) if not name.startswith('button_') else name.split('.')[0]

def under(o,root):
    while o:
        if o==root:return True
        o=o.parent
    return False

def weld(o):
    # FBX corners are split by hard normals; weld before normals are rebuilt.
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bad=[f for f in bm.faces if f.calc_area()<1e-14]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
    bm.to_mesh(o.data);bm.free();o.data.update()

def finish(o,name,color,budget):
    o.name=name;o.data.name=name
    for key in list(o.keys()):del o[key]
    o.data.materials.clear();o.data.materials.append(models.M[color])
    for p in o.data.polygons:p.material_index=0
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    for attr in list(o.data.color_attributes):o.data.color_attributes.remove(attr)
    o['slotters_material']=color;o['source_creator']=AUTHOR;o['source_url']=URL
    o['source_licence']='CC-BY-4.0';o['printed']=False;o['hinged']=name in FLAPS
    o['dimension_critical']=True
    # A charcoal console reads by its bands. Expanded hulls only add false
    # creases at the dense housing seams, ribs and port mouldings.
    o['outline']=False
    if budget:o['runtime_triangle_budget']=budget
    weld(o);planar(o);panel_normals(models,o)
    return o

def carve(o,s):
    bottom=s['entry']-s['seat_depth']-2.5;top=s['entry']+16;w,d=s['opening']
    clip_box(o,((0,-w/2000,1),(0,w/2000,-1),
        (1,(-s['slot']-d/2)/1000,1),(1,(-s['slot']+d/2)/1000,-1),
        (2,bottom/1000,1),(2,top/1000,-1)))
    # Relief below the hinge axis lets the leaf thickness sweep outward under
    # the upper rim. The visible opening above the hinge remains 27.9 mm deep.
    clip_box(o,((0,-w/2000,1),(0,w/2000,-1),
        (1,(-s['slot']-d/2-1.2)/1000,1),(1,(-s['slot']+d/2+1.2)/1000,-1),
        (2,bottom/1000,1),(2,(s['entry']-.8)/1000,-1)))

def main():
    args=sys.argv[sys.argv.index('--')+1:];path=Path(args[0]).resolve();s=SPECS['n64']
    out=Path(args[1]).resolve() if len(args)>1 else ROOT/'third_party/models'/s['creator']
    models.PRECISE=True;models.setup();palette(models)
    bpy.ops.import_scene.fbx(filepath=str(path));bpy.context.view_layer.update()
    root=bpy.data.objects['N64'];inv=root.matrix_world.inverted()
    # Bake every console mesh into the N64 group's own frame: x right, y up,
    # z front. The scene yaw (-16.37 degrees) and Maya Y-up rotation go away.
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and under(o,root)]
    flaps=[o for o in meshes if base(o.name).startswith('slot_cover_')];kept=[o for o in meshes if o not in flaps]
    local={o:inv@o.matrix_world for o in meshes}
    def points(objs):return [local[o]@v.co for o in objs for v in o.data.vertices]
    allp=points(kept);fl=points(flaps)
    lo=Vector([min(p[i] for p in allp) for i in range(3)]);hi=Vector([max(p[i] for p in allp) for i in range(3)])
    span=hi-lo;centre=(lo+hi)/2;w,h,d=s['size']
    # The slot and bay are symmetric about source x=0; the housing envelope is
    # 0.044 units (0.8 mm) asymmetric. Keep the slot on the native centre line.
    centre.x=0
    scale=Vector((w/span.x,h/span.y,d/span.z))   # mm per source unit, per axis
    flap_lo=[min(p[i] for p in fl) for i in range(3)];flap_hi=[max(p[i] for p in fl) for i in range(3)]
    measured=dict(source_size=list(span),source_ratio_d_h=[span.z/span.x,span.y/span.x],
        mm_per_unit=list(scale),flap_halfwidth_mm=(flap_hi[0]-flap_lo[0])/2*scale.x,
        flap_halfwidth_after_bay_mm=bay_warp(flap_hi[0],flap_hi[1],(flap_lo[2]+flap_hi[2])/2)*scale.x,
        flap_centre_z_mm=((flap_lo[2]+flap_hi[2])/2-centre.z)*scale.z,
        flap_depth_mm=(flap_hi[2]-flap_lo[2])*scale.z,flap_top_y_mm=(flap_hi[1]-centre.y)*scale.y)
    print('MEASURED',json.dumps(measured),flush=True)
    result={}
    for o in kept+flaps:
        key=base(o.name)
        if key not in PARTS:raise RuntimeError('Unmapped source object '+o.name)
        data=o.data.copy();o.data=data;data.transform(local[o])
        for v in data.vertices:
            x,y,z=v.co;x=bay_warp(x,y,z)
            # Blender: x right, y rear, z up; one physical scale per axis, metres.
            v.co=Vector(((x-centre.x)*scale.x,-(z-centre.z)*scale.z,(y-centre.y)*scale.y))*.001
        data.update();o.parent=None;o.matrix_world=Matrix.Identity(4)
        if local[o].determinant()<0:data.flip_normals()
        result.setdefault(PARTS[key],[]).append(o)
    for o in list(bpy.context.scene.objects):
        if not any(o in objs for objs in result.values()):bpy.data.objects.remove(o,do_unlink=True)
    parts=[];flap_report={}
    for (name,color,budget),objs in sorted(result.items()):
        if len(objs)>1:
            bpy.ops.object.select_all(action='DESELECT')
            for o in objs:o.select_set(True)
            bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join()
        o=objs[0]
        if name in OFFSETS:
            dx,dy,dz=OFFSETS[name];o.data.transform(Matrix.Translation(Vector((dx,-dz,dy))*.001))
        if name=='N64 upper enclosure':carve(o,s)
        if name in FLAPS:
            # Keep a 0.2-mm lateral gap inside each side of the receiving bay.
            span_x=max(v.co.x for v in o.data.vertices)-min(v.co.x for v in o.data.vertices)
            o.data.transform(Matrix.Diagonal(((s['opening'][0]-.4)/1000/span_x,1,1,1)))
            points=[(v.co.z*1000,-v.co.y*1000) for v in o.data.vertices]
            profile=sorted(set((round(y,6),round(z,6)) for y,z in points))
            side=-1 if name==FLAPS[0] else 1
            hinge=((min(p[0] for p in profile)+max(p[0] for p in profile))/2,
                   (min if side<0 else max)(p[1] for p in profile))
            flap_report[name]=dict(hinge_yz_mm=hinge,profile_yz_mm=profile,side=side,
                reference='Source section and outer edge; pivot placement is a running-fit inference')
        o=finish(o,name,color,budget)
        if name=='N64 upper enclosure':
            # Planar dissolve can bridge an open skin's concave relief. Clip
            # the final tessellation again, so no new diagonal spans the bay.
            carve(o,s);o.data.materials.append(models.M[color]);panel_normals(models,o)
        parts.append(o)
    out.mkdir(parents=True,exist_ok=True);save(parts,out/'model.glb')
    archive=ROOT/'research/n64/rohm/original.zip'
    report=dict(hardware='n64',author=AUTHOR,url=URL,licence='CC-BY-4.0',
      licence_url='https://creativecommons.org/licenses/by/4.0/',
      source_file=path.name,source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
      archive_file='rohm/original.zip (Sketchfab "nintendo-64.zip", original format)',
      archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
      download_approved='User selected this source and approved the original-format download on 15 October 2026',
      licence_evidence='Sketchfab API model record and download dialog: CC BY 4.0; record kept in ignored research/n64/rohm/model.json',
      source_axes='FBX group N64: x right, y up, z front (Maya), scene rotated by -16.37 degrees',
      prepared_axes='glTF x right/y up/z front; metres',measured=measured,
      envelope_whd_mm=s['size'],bay=BAY,offsets_mm=OFFSETS,flaps=flap_report,
      slot=dict(centre_z_mm=s['slot'],entry_y_mm=s['entry'],opening_wd_mm=s['opening'],seat_depth_mm=s['seat_depth']),
      modifications=['Bake the yawed Maya group into its own frame; drop the controller, cable, cartridge and rug',
        'Physical envelope corrections per axis before one uniform native scale',
        'Widen only the cartridge bay and slot (smooth local x warp) so a 116-mm Game Pak fits',
        'Retain the two closed source dust flaps; register their outer-edge axes and cross sections; lateral running gaps',
        'Raise entry to the actual source flap surface; clip the visible slot and concealed hinge relief without booleans',
        'Move the multi-out 14 mm rearward so the widened slot lining clears it',
        'Remove images, UVs and normal maps; source palette, panel normals and part names',
        'Suppress expanded outline hulls on every part'],
      parts={o.name:dict(material=o['slotters_material'],triangles=len(o.data.loop_triangles),outline=False,
        runtime_budget=o.get('runtime_triangle_budget')) for o in parts})
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REPORT',json.dumps(report['parts']),flush=True)

if __name__=='__main__':main()
