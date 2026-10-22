"""Source-specific SNES preparation. Blender 4.5 -t 1 --disable-autoexec (MIT).

Downloads stay in research/snes. Prepared physical sources have no images/UVs.
"""
import bpy,bmesh,json,sys,hashlib,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/consolebuild'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models
from import_authored import save
from handhelds import panel_normals
from snes import SPECS,palette

def source_weld(o):
    # STL coordinates are hundreds of source units before physical conversion.
    # The metre-scale 1e-8 tolerance rounds away there, leaving clipped
    # triangles disconnected; normal repair then flips individual faces
    # arbitrarily. Weld at one millionth of the envelope (under 0.0004 mm).
    return max(max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices) for i in range(3))*1e-6

def clean_mesh(o,weld=.00000001):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=weld)
    bad=[f for f in bm.faces if f.calc_area()<1e-16]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();o.data.update()

def planar(o,angle=1):
    bpy.context.view_layer.objects.active=o
    d=o.modifiers.new('Coplanar source tessellation','DECIMATE')
    d.decimate_type='DISSOLVE';d.angle_limit=math.radians(angle);d.delimit={'NORMAL','MATERIAL'}
    bpy.ops.object.modifier_apply(modifier=d.name);o.data.update()

def finish(o,name,color,author,url,budget=None):
    o.name=name
    for key in list(o.keys()):del o[key]
    o.data.materials.clear();o.data.materials.append(models.M[color])
    for p in o.data.polygons:p.material_index=0
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    o['slotters_material']=color;o['source_creator']=author;o['source_url']=url
    o['source_licence']='CC-BY-4.0';o['printed']=False;o['hinged']=False
    o['dimension_critical']=True
    if 'enclosure' in name.lower() or 'panel' in name.lower():o['outline']=False
    if name.startswith('US '):
        # Dense interior seams and the controls already read in the bands.
        # Expanded hulls add false creases at their shared housing boundaries,
        # and pierce the switches' shallow finger recesses as dotted lines.
        o['outline']=False
    if budget:o['runtime_triangle_budget']=budget
    planar(o);panel_normals(models,o)
    return o

def clip_box(o,planes,weld=.00000001):
    # The authored skins are not closed solids. Clip each source triangle
    # against the physical aperture rather than using a solid boolean, which
    # creates spurious caps across these open skins. New liners are original.
    def halves(poly,axis,limit,sign):
        inside=[];outside=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=(a[axis]-limit)*sign;db=(b[axis]-limit)*sign
            (inside if da>=0 else outside).append(a)
            if (da<0)!=(db<0):
                p=a+(b-a)*(da/(da-db));inside.append(p);outside.append(p)
        return inside,outside
    o.data.calc_loop_triangles();vertices=[];faces=[]
    for tri in o.data.loop_triangles:
        poly=[o.data.vertices[i].co.copy() for i in tri.vertices]
        for axis,limit,sign in planes:
            if len(poly)<3:break
            poly,outside=halves(poly,axis,limit,sign)
            if len(outside)>=3:
                first=len(vertices);vertices.extend(outside);faces.append(tuple(range(first,len(vertices))))
    old=o.data;data=bpy.data.meshes.new(old.name+' open aperture')
    data.from_pydata(vertices,[],faces);data.update();o.data=data;bpy.data.meshes.remove(old)
    clean_mesh(o,weld)

def carve(o,s):
    bottom=s['entry']-s['seat_depth']-2.5;top=s['entry']+12;w,d=s['opening']
    clip_box(o,((0,-w/2000,1),(0,w/2000,-1),
        (1,(-s['slot']-d/2)/1000,1),(1,(-s['slot']+d/2)/1000,-1),
        (2,bottom/1000,1),(2,top/1000,-1)))

def blank_panel(o,rect,level):
    x0,y0,x1,y1=rect
    # The plane must lie inside the rectangle. A plane at the same height
    # elsewhere once added a patch floating 3.5 mm above the eject lever.
    planes=[p for p in o.data.polygons if p.normal.z>.999 and abs(p.center.z-level)<.02
            and x0<p.center.x<x1 and y0<p.center.y<y1]
    if not planes:raise RuntimeError(f'No source plane at {level} inside {rect}')
    exact=max(planes,key=lambda p:p.area).center.z;weld=source_weld(o)
    clip_box(o,((0,x0,1),(0,x1,-1),(1,y0,1),(1,y1,-1),
                (2,exact-1.5,1),(2,exact+1.5,-1)),weld)
    vertices=[tuple(v.co) for v in o.data.vertices];faces=[tuple(p.vertices) for p in o.data.polygons]
    i=len(vertices);vertices += [(x0,y0,exact),(x1,y0,exact),(x1,y1,exact),(x0,y1,exact)]
    faces.append((i,i+1,i+2,i+3))
    old=o.data;data=bpy.data.meshes.new('Source panel without lettering')
    data.from_pydata(vertices,[],faces);data.update();o.data=data;bpy.data.meshes.remove(old);clean_mesh(o,weld)

def pal(objects,s,transform):
    mapping={
      '00':('PAL inset panel','snespanel',None),
      '01':('PAL left enclosure shoulder','snesgrey',None),
      '02':('PAL rear enclosure shoulder','snesgrey',None),
      '03':('PAL right enclosure shoulder','snesgrey',None),
      '04':('PAL front enclosure fascia','snespanel',None),
      '05':('PAL eject lever','buttonlight',320),
      '06':('PAL rear socket','blackbody',None),
      '07':('PAL indicator surround','snesgrey',None),
      '08':('PAL rear socket contact','metal',None),
      '09':('PAL power slider','buttonlight',380),
      '10':('PAL reset surround','darkgrey',None),
      '11':('PAL reset button','buttonlight',380),
      '12':('PAL power surround','darkgrey',None),
      '16':('PAL upper enclosure','snesgrey',None),
      '17':('PAL lower enclosure','sneslower',None),
      '18':('PAL controller fascia','snesgrey',480),
      '19':('PAL underside enclosure','sneslower',None),
      '20':('PAL controller contacts A','portgrey',480),
      '21':('PAL controller contacts B','portgrey',540),
      '22':('PAL controller contacts C','portgrey',480),
      '23':('PAL controller contacts D','portgrey',540),
      '24':('PAL vent and port fittings','blackbody',None),
    }
    result=[]
    for o in sorted(objects,key=lambda o:o.name):
        key=o.name.split('part_')[1].split('_')[0]
        if key in ('13','14','15'):
            # Slot flap is parked open; flat source decal surfaces are excluded.
            bpy.data.objects.remove(o,do_unlink=True);continue
        o.data.transform(transform);o.matrix_world=Matrix.Identity(4);o.data.update()
        if key in ('00','16'):carve(o,s)
        name,color,budget=mapping[key]
        result.append(finish(o,name,color,'quick_loop',
          'https://sketchfab.com/3d-models/super-nintendo-d42c35b117974ade8842f0964f5fd59e',budget))
    return result

def moulded_patches(o,angle=30):
    # Faces joined across edges flatter than the panel-normal crease angle.
    # The source is one closed skin, so parts are whole mouldings bounded by
    # creases; boxes of triangle centres left sawtooth slivers on the housing.
    bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
    limit=math.radians(angle);patch=[-1]*len(bm.faces);count=0
    for seed in bm.faces:
        if patch[seed.index]>=0:continue
        patch[seed.index]=count;stack=[seed]
        while stack:
            for e in stack.pop().edges:
                if len(e.link_faces)!=2 or e.calc_face_angle(math.pi)>limit:continue
                for f in e.link_faces:
                    if patch[f.index]<0:patch[f.index]=count;stack.append(f)
        count+=1
    bm.free();return patch

# Source-unit boxes (x, -y front, z up); every face of a moulding must fit.
US_CONTROLS=(('US power slider','uspower',(-97.7,-19.9,-104.4,-76.6,-8.4,.2)),
             ('US reset button','usreset',(19.9,97.7,-104.4,-76.6,-8.4,.2)),
             ('US eject lever','useject',(-23.8,23.8,-155.2,-76.3,-11,-7.4)),
             ('US controller sockets','portgrey',(-87,-31,-193.6,-191,-44.5,-29.5)),
             ('US controller sockets','portgrey',(31,87,-193.6,-191,-44.5,-29.5)),
             ('US rear connectors','blackbody',(-97,-15,138.5,148,-58,-45)))

def us(objects,s,transform):
    o=objects[0]
    # Replace the four small planar text regions, not the source's glyph paths:
    # the rear wordmark, both switch legends and the EJECT lever lettering.
    # Moving engraved vertices alone leaves coplanar text fragments behind.
    for rect,level in (((90,118,132,138),-1.32),
                       ((-126,-110,-101,-64),-7.96),((101,-110,126,-64),-7.96),
                       ((-9,-149,9,-143),-7.96)):
        blank_panel(o,rect,level)
    clean_mesh(o,source_weld(o));o.data.transform(transform);o.data.update();carve(o,s)
    inv=transform.inverted();patch=moulded_patches(o);groups={}
    bounds={};area={};height={}
    for p in o.data.polygons:
        k=patch[p.index];raw=[inv@o.data.vertices[i].co for i in p.vertices]
        lo,hi=bounds.setdefault(k,([math.inf]*3,[-math.inf]*3))
        for v in raw:
            for i in range(3):lo[i]=min(lo[i],v[i]);hi[i]=max(hi[i],v[i])
        area[k]=area.get(k,0)+p.area;height[k]=height.get(k,0)+p.area*(inv@p.center).z
    def group(k):
        lo,hi=bounds[k]
        for name,colour,(x0,x1,y0,y1,z0,z1) in US_CONTROLS:
            if x0<=lo[0] and hi[0]<=x1 and y0<=lo[1] and hi[1]<=y1 and z0<=lo[2] and hi[2]<=z1:
                return name,colour
        # Preserve the source's stepped two-tone enclosure as separate paint
        # parts. A moulding crossing the seam keeps one colour (area centroid).
        z=height[k]/area[k] if area[k] else (lo[2]+hi[2])/2
        return ('US lower enclosure','uslower') if z<-39.19 else ('US upper enclosure','usgrey')
    for p in o.data.polygons:groups.setdefault(group(patch[p.index]),[]).append(p)
    result=[]
    budgets={'US upper enclosure':6900,'US lower enclosure':4100,'US controller sockets':1500,
             'US rear connectors':500,'US power slider':450,'US reset button':450,'US eject lever':300}
    vertices=[tuple(v.co) for v in o.data.vertices]
    for (name,color),polys in sorted(groups.items()):
        used=sorted({i for p in polys for i in p.vertices});indices={i:j for j,i in enumerate(used)}
        data=bpy.data.meshes.new(name);data.from_pydata([vertices[i] for i in used],[],
                    [tuple(indices[i] for i in p.vertices) for p in polys]);data.update()
        part=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(part)
        result.append(finish(part,name,color,'Steven H. Tran (@ibbqcats)',
          'https://sketchfab.com/3d-models/super-nintendo-console-41c9dd1f5a53493cbe2e00a190150e93',budgets[name]))
    bpy.data.objects.remove(o,do_unlink=True)
    return result

def main():
    args=sys.argv[sys.argv.index('--')+1:];name=args[0];path=Path(args[1]).resolve();s=SPECS[name]
    out=Path(args[2]).resolve() if len(args)>2 else ROOT/'third_party/models'/s['creator']
    models.PRECISE=True;models.setup();palette(models)
    if path.suffix.lower()=='.dae':bpy.ops.wm.collada_import(filepath=str(path))
    else:bpy.ops.wm.stl_import(filepath=str(path))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    matrices={o:o.matrix_world.copy() for o in objects}
    for o in objects:o.parent=None;o.data.transform(matrices[o]);o.matrix_world=Matrix.Identity(4)
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
    lo=Vector(tuple(min(v.co[i] for o in objects for v in o.data.vertices) for i in range(3)))
    hi=Vector(tuple(max(v.co[i] for o in objects for v in o.data.vertices) for i in range(3)))
    span=hi-lo;w,h,d=s['size'];target=Vector((w,d,h))
    transform=Matrix.Diagonal(Vector((*[target[i]/span[i]*.001 for i in range(3)],1)))@Matrix.Translation(-(hi+lo)/2)
    result=pal(objects,s,transform) if name=='snes' else us(objects,s,transform)
    out.mkdir(parents=True,exist_ok=True);save(result,out/'model.glb')
    report=dict(hardware=name,author=result[0]['source_creator'],url=result[0]['source_url'],
      licence='CC-BY-4.0',licence_url='https://creativecommons.org/licenses/by/4.0/',
      source_file=path.name,source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
      archive_file=('quick-loop-original.zip' if name=='snes' else 'ibbqcats-original.zip'),
      archive_sha256=hashlib.sha256((ROOT/'research/snes'/('quick-loop-original.zip' if name=='snes' else 'ibbqcats-original.zip')).read_bytes()).hexdigest(),
      download_approved='User approved each original-format Sketchfab download on 15 October 2026',
      licence_evidence='Page and download-dialog CC BY 4.0 notice; screenshots retained in ignored research/snes',
      source_axes='X right, Z up, -Y front',prepared_axes='glTF x right/y up/z front; metres',
      source_bounds_xyz=[list(lo),list(hi)],source_uniform_width_mm=list(span*w/span.x),
      envelope_whd_mm=s['size'],axis_correction_percent=[(target[i]/(span[i]*w/span.x)-1)*100 for i in range(3)],
      slot=dict(centre_z_mm=s['slot'],entry_y_mm=s['entry'],opening_wd_mm=s['opening'],seat_depth_mm=s['seat_depth']),
      modifications=['Physical envelope corrections before one uniform native scale',
        ('Remove images, UVs and the two source decal planes' if name=='snes' else
         'Replace four STL text regions with blank planar patches; no images or source printing retained'),
        ('Remove the fixed closed slot flap; clip open skins at the real slot position without solid booleans' if name=='snes' else
         'Clip open skins at the real slot position without solid booleans'),
        'Open the physical travel under the source cartridge opening',
        ('Source-specific semantic palette, enclosure parts and panel normals' if name=='snes' else
         'Weld the STL at a source-relative tolerance; segment parts as whole mouldings bounded by 30-degree creases, with source palette and panel normals'),
        ('Suppress expanded hulls on dense housing and panel seams' if name=='snes' else
         'Suppress expanded hulls on every US part: housing seams, port interiors and recessed controls'),
        'Per-fitting runtime budgets; full-detail prepared geometry retained'],
      parts={o.name:dict(material=o['slotters_material'],triangles=len(o.data.loop_triangles),outline=o.get('outline',True),
        runtime_budget=o.get('runtime_triangle_budget')) for o in result})
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
