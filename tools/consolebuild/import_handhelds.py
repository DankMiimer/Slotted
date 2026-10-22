"""Source-specific CGB/AGS adapters. Blender 4.5, --disable-autoexec (MIT).

Downloads remain in research/. Prepared image-free CC BY geometry builds offline.
Axes below describe the actual sources, not a generic glTF import convention.
"""
import bpy, bmesh, sys, json, hashlib, math
from pathlib import Path
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models
from import_authored import bounds, save
from handhelds import physical_cut,panel_normals,AGS_CAVITY_T,AGS_CAVITY_Y
from lids import ags_registration
ROOT=Path(__file__).resolve().parents[2]


def start(path):
    models.PRECISE=True;models.setup()
    colours={n:tuple(m.diffuse_color[:3]) for n,m in models.M.items()}
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    if path.suffix=='.dae':bpy.ops.wm.collada_import(filepath=str(path))
    else:bpy.ops.import_scene.gltf(filepath=str(path))
    models.M.clear()
    for n,c in colours.items():models.material(n,c)
    bpy.context.view_layer.update()
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    matrices={o:o.matrix_world.copy() for o in meshes}
    for o in meshes:
        o.parent=None;o.data.transform(matrices[o]);o.matrix_world=Matrix.Identity(4)
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
    bpy.context.view_layer.update()


def finish(o,name,palette,transform,author,url,critical=True):
    o.name=name;o.data.transform(transform);o.matrix_world=Matrix.Identity(4)
    o.data.update();bpy.context.view_layer.update()
    for key in list(o.keys()):del o[key]
    o.data.materials.clear();o.data.materials.append(models.M[palette])
    for p in o.data.polygons:p.material_index=0
    o['slotters_material']=palette;o['source_creator']=author
    o['source_licence']='CC-BY-4.0';o['source_url']=url
    o['printed']=False;o['hinged']=False;o['dimension_critical']=critical
    for uv in list(o.data.uv_layers):o.data.uv_layers.remove(uv)
    return o


def planar(o,angle=3):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    d=o.modifiers.new('Dissolve coplanar source tessellation','DECIMATE')
    d.decimate_type='DISSOLVE';d.angle_limit=math.radians(angle);d.delimit={'NORMAL','MATERIAL'}
    bpy.ops.object.modifier_apply(modifier=d.name)


def record(folder,path,report,objects):
    folder=ROOT/'third_party/models'/folder;folder.mkdir(parents=True,exist_ok=True)
    save(objects,folder/'model.glb')
    report['source_file']=path.name;report['source_file_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    report['prepared_axes']='glTF x right, y up, z front; metres'
    report['licence']='CC-BY-4.0';report['licence_url']='https://creativecommons.org/licenses/by/4.0/'
    report['parts']={o.name:dict(material=o['slotters_material'],triangles=len(o.data.loop_triangles)) for o in objects}
    (folder/'source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)


def gbc(path):
    start(path)
    # Collada: X right, Z up, -Y front. Weld coincident triangle corners before
    # separating physical islands; otherwise every hard-normal corner separates.
    for o in list(bpy.context.scene.objects):
        bm=bmesh.new();bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
        bm.to_mesh(o.data);bm.free()
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
    case=bpy.data.objects['Case lp'];lo,hi=bounds(case);span=hi-lo;centre=(lo+hi)*.5
    axis=Matrix.Diagonal(Vector((78/span.x*.001,27.4/span.y*.001,133.5/span.z*.001,1)))
    transform=axis@Matrix.Translation(-centre)
    author='Wikiti';url='https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19'
    names={'Case lp':('CGB recreation housing','gbc'), 'Case lp.017':('CGB battery cover','gbc'),
           'Plastic lp.001':('CGB power slider','darkgrey'), 'Plastic lp.002':('CGB volume wheel','darkgrey'),
           'Plastic lp.003':('Continuous D-pad','blackbody'),
           'Plastic lp.004':('Action button B','blackbody'),'Plastic lp.005':('Action button A','blackbody'),
           'Plastic lp.006':('SELECT button','blackbody'),'Plastic lp.007':('START button','blackbody'),
           'Screen lp':('CGB infrared window','blackbody'),
           'Screen lp.001':('CGB lens surround','screenbezel'),
           'Screen lp.002':('CGB LCD glass','lcdblack'),'Screen lp.003':('CGB battery LED','red')}
    objects=[]
    for o in sorted(list(bpy.context.scene.objects),key=lambda x:x.name):
        if o.name=='Plastic lp':
            # Only an exposed half cartridge was supplied, not a complete shell.
            bpy.data.objects.remove(o,do_unlink=True);continue
        name,palette=names.get(o.name,('CGB side grip moulding','gbc') if o.name.startswith('Case') else ('CGB port fitting','metal'))
        old=o.name;finish(o,name,palette,transform,author,url)
        if old=='Screen lp.002':
            # Replace the source active-area extent, retaining the outer lens.
            low,high=bounds(o);c=(low+high)*.5
            for v in o.data.vertices:
                v.co.x=c.x+(v.co.x-c.x)*.044/(high.x-low.x)
                v.co.z=c.z+(v.co.z-c.z)*.0396/(high.z-low.z)
                # The source's opaque outer lens covers its recessed LCD.
                v.co.y=-.01345
        if old=='Screen lp.001':
            # Cut an actual aperture through the previously texture-only lens.
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            models.cut(o,(-.0001/.01,.0348/.01,.0113/.01),(.044/.01,.0396/.01,.006/.01),0)
        if old=='Case lp':o['outline']=False
        if old=='Case lp':
            # Source was built around an exposed half cartridge. Open the
            # concealed full travel and establish independent rear-lip/seat
            # surfaces for a complete 7.8-mm shell, preserving outer rails.
            physical_cut(models,o,(0,3.45,-.26),(5.84,6.65,.86))
            physical_cut(models,o,(0,5.07,-1.33),(5.84,3.46,1.36))
        planar(o);o.data.calc_loop_triangles();objects.append(o)
        if old in ('Case lp','Case lp.017'):panel_normals(models,o)
        if old=='Case lp':
            o.data.update();normals=[tuple(n.vector) for n in o.data.corner_normals]
            for p in o.data.polygons:
                if abs(p.normal.y)>.93:
                    for li in p.loop_indices:normals[li]=(0,1 if p.normal.y>0 else -1,0)
            o.data.normals_split_custom_set(normals)
    record('wikiti-cgb',path,dict(author=author,url=url,housing_mm=[78,133.5,27.4],
        source_housing_units=list(span),uniform_height_housing_mm=list(span*133.5/span.z),
        source_axes='X right, Z up, -Y front',
        modifications=['Remove incomplete seated cartridge','Weld coincident triangle corners',
                      'Normalize physical housing envelope','Opaque native palette; exclude UVs/images',
                      'Active LCD corrected to 44 x 39.6 mm; cut lens aperture',
                      'Dissolve coplanar tessellation; preserve silhouette and receiving rails']),objects)


def gba(path):
    start(path)
    author='thegraphicsgeek';url='https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f'
    # glTF import yields X right, +Y rear, Z up. Source is already in metres.
    # Physical base is 84 x 82; Nintendo specifies 82 wide x 84.6 long.
    transform=Matrix.Translation((0,0,-.0311))@Matrix.Diagonal(Vector((82/84,84.6/82,1,1)))
    skip=('LogoSticker','Btm_Label','OffText','OnText','OnDot','OffDot','VolText','VolDot','VolBar','ScreenGlass','ScreenCover','CartridgeSlot_Teeth')
    objects=[]
    for o in sorted(list(bpy.context.scene.objects),key=lambda x:x.name):
        key=o.name.split('_geo_')[0]
        if key.startswith(skip):bpy.data.objects.remove(o,do_unlink=True);continue
        palette=('gba' if key in ('Base','TopScreen_Frame','Top_LargeHinge','Top_SmallHinge','Battery_Lid','HingeCorner_RMid','HingeCorner_LMid')
                 else 'lcdblack' if key=='Sceren' else 'screenbezel' if key=='ScreenGuard'
                 else 'green' if key=='Power_LED01' else 'yellow' if key=='Power_LED02'
                 else 'black' if key.endswith('Base') or 'Inside' in key or key=='CartridgeSlot_Teeth'
                 else 'buttonlight' if 'Btn' in key or key=='DPad' else 'metal')
        finish(o,{'Base':'SP recreation housing','TopScreen_Frame':'SP display lid','DPad':'SP continuous D-pad','Sceren':'SP LCD glass'}.get(key,'SP '+key),palette,transform,author,url)
        o['hinged']=key in ('TopScreen_Frame','Top_LargeHinge','Top_SmallHinge','Sceren','ScreenGuard')
        if key=='Base':
            bm=bmesh.new();bm.from_mesh(o.data)
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
            # Complete-shell cavity and the wider/thicker upper pull flange.
            # These are concealed fit corrections, not a housing scale change.
            physical_cut(models,o,(0,AGS_CAVITY_Y/10,2.45),(5.82,AGS_CAVITY_T/10,3.70))
            physical_cut(models,o,(0,AGS_CAVITY_Y/10,3.85),(6.07,AGS_CAVITY_T/10,1.10))
        if key=='Sceren':
            c=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
            up=Vector((0,.26646,.96385));half=max(abs((v.co-c).dot(up)) for v in o.data.vertices)
            for v in o.data.vertices:
                delta=v.co-c
                v.co=c+Vector((delta.x*61.2/61.268,0,0))+up*(delta.dot(up)*.0204/half)
        planar(o)
        # Protect the silhouette by dissolving redundant tessellation first.
        # Dense fittings are reduced individually, never the assembled console.
        o.data.calc_loop_triangles();original=len(o.data.loop_triangles)
        limit=5800 if key=='Base' else 2200 if key=='TopScreen_Frame' else 500 if key=='DPad' else 240 if 'Hinge' in key else 160
        o['runtime_triangle_budget']=limit
        if key=='Base':o['outline']=False
        if key=='Base':panel_normals(models,o)
        o.data.calc_loop_triangles();objects.append(o)
    def native_points(name):
        o=next(o for o in objects if o.name==name)
        return [(v.co.x*1000,v.co.z*1000,-v.co.y*1000) for v in o.data.vertices]
    lid=ags_registration(native_points('SP Top_LargeHinge'),native_points('SP LCD glass'))
    record('thegraphicsgeek-ags',path,dict(author=author,url=url,source_base_mm=[84,82],base_mm=[82,84.6],lid=lid,
        source_axes='X right, Y rear, Z up',source_open_angle_degrees=105,
        modifications=['Physical width/length correction','Individual component reduction after planar dissolve',
                       'Remove all source decals and raised text','Remove opaque lens over LCD',
                       'Native vertex colours; no source images or UVs']),objects)


def gba_media(path):
    start(path);o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    lo,hi=bounds(o);span=hi-lo;c=(lo+hi)*.5
    transform=Matrix.Diagonal(Vector((60/span.x*.001,9.4/span.y*.001,34.5/span.z*.001,1)))@Matrix.Translation(-c)
    author='thegraphicsgeek';url='https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f'
    finish(o,'GBA recreated Game Pak','darkgrey',transform,author,url);planar(o)
    folder=ROOT/'third_party/models/thegraphicsgeek-ags';save([o],folder/'media.glb')
    (folder/'media-source.json').write_text(json.dumps(dict(author=author,url=url,licence='CC-BY-4.0',
        source_file=path.name,source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_dimensions_mm=list(span*1000),media_mm=[60,34.5,9.4],
        source_axes='X right, Z up, -Y label face',
        modifications=['Physical envelope correction','Remove images, UVs and game label','Opaque native shell palette']),indent=2)+'\n')


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=2 or args[0] not in ('gbc','gba','gba-media'):raise SystemExit('usage: -- gbc|gba|gba-media SOURCE')
    {'gbc':gbc,'gba':gba,'gba-media':gba_media}[args[0]](Path(args[1]))
