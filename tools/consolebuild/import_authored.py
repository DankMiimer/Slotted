"""Prepare licensed authored geometry; run once against ignored research files.

Runtime rebuilds read the prepared GLBs, so they require no Internet/account or
third-party Blender scene. Textures, decal images, lights and cameras are omitted.
Processing code: MIT. Model geometry retains its creator's separate CC licence.
"""
import bpy
import sys
import json
import hashlib
from pathlib import Path
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import models

GB_MATERIALS={
    'Base':('DMG recreation housing','dmgbody'),
    'Pink_Buttons':('DMG action buttons','dmgbutton'),
    'D-Pad':('Continuous D-pad','blackbody'),
    'Start-Select_Button':('DMG Select and Start buttons','darkgrey'),
    'Glass':('LCD glass','lcdgreen'),
    'Front_Panel':('LCD bezel','dmgbezel'),
    'Red_Light':('Battery indicator','red'),
    'Metal':('DMG port contacts','metal'),
    'Power_Switch':('DMG power switch','darkgrey'),
    'Screen':('LCD screen','lcdgreen'),
    'Screen_Edge':('LCD border','black'),
    'Cart':('DMG Game Pak recreation shell','dmgbody'),
    'Sticker':('Blank Game Pak label','label'),
    'NormalMap':('Game Pak header moulding','dmgbody')}


def bounds(obj):
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    return Vector(tuple(min(p[i] for p in points) for i in range(3))),Vector(tuple(max(p[i] for p in points) for i in range(3)))


def split(obj,transform,mapping,author,url,licence):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    obj.modifiers.clear()
    obj.data.transform(transform@obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    before=set(bpy.context.scene.objects)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
    objects=[obj]+[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    if any(o.data.materials[o.data.polygons[0].material_index].name=='D-Pad' for o in objects):
        black=next(o for o in objects if o.data.materials[o.data.polygons[0].material_index].name=='D-Pad')
        bpy.ops.object.select_all(action='DESELECT');black.select_set(True);bpy.context.view_layer.objects.active=black
        bpy.context.tool_settings.mesh_select_mode=(True,False,False)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
        for vertex in black.data.vertices:
            x,rear,y=vertex.co*1000
            vertex.select=-40<x<-17 and -42<y<-15 and rear<-8
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
        objects += [o for o in bpy.context.scene.objects if o not in before and o not in objects and o.type=='MESH']
    for o in objects:
        if not o.data.polygons:
            bpy.data.objects.remove(o,do_unlink=True);continue
        material=o.data.materials[o.data.polygons[0].material_index].name
        name,palette=mapping[material];o.name=name
        if material=='D-Pad':
            lo,hi=bounds(o)
            o.name='Continuous D-pad' if (hi.x-lo.x)<.04 else 'DMG dark fittings'
        for key in list(o.keys()):del o[key]
        o.data.materials.clear();o.data.materials.append(models.M[palette])
        for polygon in o.data.polygons:polygon.material_index=0
        o['slotters_material']=palette;o['printed']=False;o['hinged']=False
        o['dimension_critical']=material not in ('Base','Cart')
        o['source_creator']=author;o['source_url']=url;o['source_licence']=licence
    return [o for o in objects if o.name in bpy.data.objects and o.data.polygons]


def save(objects,path):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    # The existing exporter embeds colours/extras, not materials or images.
    models.PRECISE=False;models.export_gltf(objects,path)
    bpy.ops.export_scene.gltf(filepath=str(path),use_selection=True,export_format='GLB',
        export_materials='NONE',export_texcoords=False,export_vertex_color='ACTIVE',
        export_active_vertex_color_when_no_material=True,export_extras=True)


def prepare_gb(path):
    models.PRECISE=True;models.setup()
    palettes={name:tuple(mat.diffuse_color[:3]) for name,mat in models.M.items()}
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    models.M.clear()
    for name,colour in palettes.items():models.material(name,colour)
    case=bpy.data.objects['Cube.001'];glass=bpy.data.objects['Cube.002'];cart=bpy.data.objects['Cube']
    lo,hi=bounds(case);span=hi-lo;centre=(lo+hi)*.5
    # Source: X front, Y right, Z up. Target Blender: X right, Y rear, Z up.
    # Scale each published envelope dimension explicitly; the reference card
    # records the author's initial ratios and these small dimensional corrections.
    axis=Matrix(((0,90/span.y*.001,0,0),(-32/span.x*.001,0,0,0),
                 (0,0,148/span.z*.001,0),(0,0,0,1)))
    transform=axis@Matrix.Translation(-centre)
    url='https://sketchfab.com/3d-models/gameboy-dmg-01-29849a15fe0a40a6a18e01c9d544a0ed'
    author="Let's Do 3D";licence='CC-BY-4.0'
    parts=split(case,transform,GB_MATERIALS,author,url,licence)
    glass_parts=split(glass,transform,GB_MATERIALS,author,url,licence)
    glass_parts[0].name='LCD cover glass';parts+=glass_parts
    # The recreation's internal wall only admits its original 6.9-mm cart.
    # Widen the concealed cavity by 1 mm for the measured 7.8-mm Game Pak.
    # External surfaces, screw wells and rear lip retain the author's geometry.
    housing=next(o for o in parts if o.name=='DMG recreation housing')
    for part in parts:
        if len(part.data.polygons)<4:continue
        bpy.context.view_layer.objects.active=part
        planar=part.modifiers.new('Remove coplanar tessellation','DECIMATE')
        planar.decimate_type='DISSOLVE';planar.angle_limit=.052359878
        planar.delimit={'NORMAL','MATERIAL'}
        bpy.ops.object.modifier_apply(modifier=planar.name)
    housing['dimension_critical']=True
    # Fine overlapping moulded seams already define the light-grey case.
    # Expanding every interior seam creates black aliasing at native size.
    housing['outline']=False
    cavity_vertices=0
    for vertex in housing.data.vertices:
        x,rear,y=vertex.co*1000
        if abs(x)<29.5 and y>13 and abs(rear-5.854)<.04:
            vertex.co.y-=.001;cavity_vertices+=1
        if abs(x)<30.8 and 39<y<42 and rear>13:
            vertex.co.z+=(45.5-41.3019)*.001
        if abs(x)<29.5 and y>13 and 12.8<rear<13.5:
            vertex.co.y=.01345
    # Removing the source auto-smooth node modifier must not leave the broad
    # front panel interpolating tiny bevel normals across its triangulation.
    # Rebuild sharp boundaries and weight flat panels by their face areas.
    bpy.ops.object.select_all(action='DESELECT');housing.select_set(True)
    bpy.context.view_layer.objects.active=housing
    housing.data.normals_split_custom_set([(0,0,0)]*len(housing.data.loops))
    housing.data.set_sharp_from_angle(angle=.523598776)
    for polygon in housing.data.polygons:polygon.use_smooth=True
    normals=housing.modifiers.new('Stable moulded panel normals','WEIGHTED_NORMAL')
    normals.mode='FACE_AREA';normals.keep_sharp=True;normals.weight=100
    bpy.ops.object.modifier_apply(modifier=normals.name)
    housing.data.update()
    panel_normals=[tuple(n.vector) for n in housing.data.corner_normals]
    for polygon in housing.data.polygons:
        if abs(polygon.normal.y)>.95:
            for loop in polygon.loop_indices:panel_normals[loop]=(0,1 if polygon.normal.y>0 else -1,0)
    housing.data.normals_split_custom_set(panel_normals)
    target=ROOT/'third_party/models/letsdo3d-dmg';target.mkdir(parents=True,exist_ok=True)
    save(parts,target/'model.glb')
    low,high=bounds(cart);span_cart=high-low;cart_centre=(low+high)*.5
    cart_axis=Matrix(((0,57/span_cart.y*.001,0,0),(-7.8/span_cart.x*.001,0,0,0),
                      (0,0,65.5/span_cart.z*.001,0),(0,0,0,1)))
    media=split(cart,Matrix.Rotation(3.141592653589793,4,'Z')@cart_axis@Matrix.Translation(-cart_centre),GB_MATERIALS,author,url,licence)
    save(media,target/'media.glb')
    report={'author':author,'licence':licence,'url':url,'source_dimensions':list(span),
            'uniform_height_mm_per_source_unit':148/span.z,
            'source_console_mm_at_uniform_height':[span.y*148/span.z,148,span.x*148/span.z],
            'console_mm':[90,148,32],'media_mm':[57,65.5,7.8],
            'source_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'cavity_wall_shift_mm':1,'cavity_vertices':cavity_vertices,
            'rear_lip_shift_mm':45.5-41.3019,
            'modifications':['Complete envelope normalization','Three-degree planar reduction',
                             'D-pad separated from side fittings','Cavity wall widened 1 mm',
                             'Rear inner lip set to -13.45 mm','Rear mouth raised to 45.5 mm',
                             'Rebuild 30-degree sharp boundaries and face-area weighted housing normals',
                             'Dense housing seams skip hull expansion','No source images or UVs'],
            'source_media_dimensions':list(span_cart),'source_media_seated_centre_mm':
            [(cart_centre.y-centre.y)*90/span.y,(cart_centre.z-centre.z)*148/span.z,
             (cart_centre.x-centre.x)*32/span.x]}
    (target/'source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)


PSP_MATERIALS={
    'Body 1':('PSP black moulding','pspplastic'),
    'Borders':('PSP silver fitting','chrome'),
    'screen':('PSP LCD','glass'),
    'screen Protection Plate':('PSP LCD glass','glass'),
    'Charge Port':('PSP DC socket','yellow'),
    'WIFI':('PSP WLAN LED','yellow'),
    'Memory Access':('PSP access LED','green'),
    'Power':('PSP power LED','green'),
    'Hold':('PSP hold LED','darkgrey'),
    'USB Port':('PSP USB opening','black'),
    'Shoulder Buttons':('Curved shoulder button','buttonlight'),
    'Body 1(Joy Stick)':('Textured analog nub','pspkey'),
    'Square,Circle,X, and Triangle  Shapes':('PSP key glyph','white'),
    'PSP Face Color.Other Buttons.Solid.Trans':('Separate directional key','pspkey')}


def prepare_psp(path):
    models.PRECISE=True;models.setup()
    palettes={name:tuple(mat.diffuse_color[:3]) for name,mat in models.M.items()}
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    models.M.clear()
    for name,colour in palettes.items():models.material(name,colour)
    for obj in list(bpy.context.scene.objects):
        if obj.type!='MESH':bpy.data.objects.remove(obj,do_unlink=True)
    body=bpy.data.objects['PSP Body']
    bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
    body.modifiers['Subsurf'].levels=1;body.modifiers['Subsurf'].render_levels=1
    bpy.ops.object.modifier_apply(modifier='Subsurf')
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
    # Sony excludes the largest projections: anchor the housing frame, not
    # shoulder buttons, USB fittings or the raised action keys.
    lo,hi=bounds(bpy.data.objects['PSP Body.026']);span=hi-lo;centre=(lo+hi)*.5
    scale=Vector((169.4/span.x,18.6/span.y,71.4/span.z))
    transform=Matrix.Scale(.001,4)@Matrix.Diagonal(Vector((*scale,1)))@Matrix.Translation(-centre)
    author='JSJetStream14';licence='CC-BY-3.0';url='https://blendswap.com/blend/14767'
    objects=[];counts={}
    source=list(sorted(bpy.context.scene.objects,key=lambda o:o.name))
    for obj in source:
        if obj.name=='Shoulder Buttons Labels' or obj.name in {f'PSP Body.{i:03}' for i in range(40,44)} or not obj.data.polygons:
            continue
        index=int(obj.name.rsplit('.',1)[1]) if '.' in obj.name else 0
        obj.data.calc_loop_triangles();original=len(obj.data.loop_triangles)
        # Hero housing/cover contours are kept intact. Reduce tiny fittings
        # individually before export instead of collapsing the entire console.
        limit=(original if index in (0,1,2,17,19,26) else
               320 if index in (3,27,28) else
               200 if index in (21,23,24) else
               160 if index in (44,49,50,51,52,53,54,55,56) else
               48 if index in (5,6,7,8,10,11,12,13,14,15,16,18,29,37,38,39) else 64)
        if original>limit:
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            decimate=obj.modifiers.new('Native fitting detail','DECIMATE');decimate.ratio=limit/original
            bpy.ops.object.modifier_apply(modifier=decimate.name)
        parts=split(obj,transform,PSP_MATERIALS,author,url,licence)
        for part in parts:
            if index==26:
                part.name='PSP recreation housing' if part['slotters_material']=='pspplastic' else 'PSP silver perimeter'
            elif index==19:part.name='UMD door shell'
            elif index==3:part.name='UMD door silver ring'
            elif index in (49,50,51,52):part.name='PSP '+{49:'cross',50:'circle',51:'triangle',52:'square'}[index]+' key'
            elif index in (27,28):part.name='PSP action surround' if index==27 else 'PSP direction surround'
            elif index in (30,31,32,33,34,35,36):part.name='PSP system button'
            elif index in (53,54,55,56):part.name='PSP action key cover'
            elif index in (66,67,68,69):part.name='PSP direction key cover'
            elif index in (62,63,64,65):part.name='Separate directional key'
            if index in (45,46,47,48,58,59,60,61):
                # Native materials are opaque: the source put these glyphs
                # underneath transparent caps. Project the existing flat ink
                # onto their outer surface instead of hiding it under plastic.
                for vertex in part.data.vertices:vertex.co.y-=.00063 if index<50 else .00085
            if index in (0,17,26):
                # Correct the recreation's 93.57x51.85 LCD and its matching
                # aperture to the 4.3-inch 480:272 reference card. Move only
                # the inner front opening; the exterior outline is untouched.
                for vertex in part.data.vertices:
                    x,rear,y=vertex.co*1000
                    if index in (0,17) or (-50<x<46 and -26<y<29 and rear<-7):
                        vertex.co.x=(x+1.943)*95/93.5697*.001
                        vertex.co.z=((y-1.466)*53.833333/51.8486+3.2)*.001
            if index==3:
                # The rear identifying ring is circular on the hardware.
                for vertex in part.data.vertices:
                    vertex.co.z=(.001231+(vertex.co.z-.001231)*48.49/46.817)
            part['printed']=index in (45,46,47,48,58,59,60,61)
            part['dimension_critical']=True
            part['hinged']=index in (3,19)
            if part['hinged']:part['hinge_mm']=models.PSP['hinge']
            part.data.calc_loop_triangles();counts[part.name]=len(part.data.loop_triangles)
        objects+=parts
    target=ROOT/'third_party/models/jsjetstream-psp';target.mkdir(parents=True,exist_ok=True)
    save(objects,target/'model.glb')
    report=dict(author=author,licence=licence,url=url,
                source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                source_housing_dimensions=list(span),housing_mm=[169.4,71.4,18.6],
                uniform_width_source_mm=[169.4,span.z*scale.x,span.y*scale.x],
                native_detail_triangles=sum(counts.values()),parts=counts,
                modifications=['One subdivision level','Housing envelope normalization',
                               'Per-component fitting reduction','No images or UVs',
                               'LCD and aperture corrected to 95x53.833333 mm at (0,3.2)',
                               'Rear ring corrected to a 48.49-mm circle',
                               'Opaque native key covers; flat glyphs projected onto their surfaces',
                               'Source Sony/shoulder marks excluded; project vectors replace them',
                               'Rear cover and ring tagged with shared animation hinge'])
    (target/'source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='parts'}),flush=True)


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=2 or args[0] not in ('gb','psp'):raise SystemExit('usage: blender --python import_authored.py -- gb|psp SOURCE.blend')
    (prepare_gb if args[0]=='gb' else prepare_psp)(Path(args[1]))
