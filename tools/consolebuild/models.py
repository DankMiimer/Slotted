"""Cartridge console models and cel-shaded renders; processing code MIT.

Blender 4.5+: --background --python tools/consolebuild/models.py -- [system ...]
DMG/PSP use credited CC BY recreations; other geometry is original.
No reference images or game textures. Camera matches native SDL exactly.
"""
import sys
import math
import ast
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from exemplars import DMG, PSP, UMD, DMG_SCALE, PSP_SCALE, rounded_rect, umd_outline, native_header
from handhelds import CGB_SCALE, AGS_SCALE, AGS_CAVITY_T, AGS_CAVITY_Y, cgb, ags, cgb_media, ags_media, physical_cut, panel_normals
import media
import snes
import n64
import ps1
import lids
import ds_lid

MODEL_SCALES={'gb':DMG_SCALE,'psp':PSP_SCALE,'gbc':CGB_SCALE,'gba':AGS_SCALE}
MODEL_SCALES.update({name:s['scale'] for name,s in (snes.SPECS|n64.SPECS|ps1.SPECS).items()})
# Physical media share each console's presentation scale. SNES and N64 have
# authored housings; the other cartridge consoles retain their procedural ones.
MEDIA_SCALES=media.SCALES


def model_scale(name):
    return MODEL_SCALES.get(name) or MEDIA_SCALES[name]

ROOT=Path(__file__).resolve().parents[2]
source=ast.parse((ROOT/'tools/themebuild/consoles.py').read_text())
spec_node=next(n.value for n in source.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='SPECS' for t in n.targets))
SPECS=eval(compile(ast.Expression(spec_node),'<specs>','eval'),{'dict':dict})
for name,spec in SPECS.items():
    spec['yscale']={'nes':2.1,'n64':2.3,'md':1.7,'md-jp':1.7}.get(name,1)
snes.apply_specs(SPECS);n64.apply_specs(SPECS);ps1.apply_specs(SPECS)
OUT=ROOT/'build/console-renders'
FONT=ROOT/'third_party/open-sans/OpenSans-SemiBold.ttf'
SCALE=.01
PHI=math.radians(35)
M={}
PRECISE=False


def xyz(x,y,z):
    return (x*SCALE,-z*SCALE,y*SCALE)


def material(name,colour,rough=.42,metallic=0):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*colour,1);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    normal=nodes.new('ShaderNodeNewGeometry')
    dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=(-.45,-.50,.74)
    links.new(normal.outputs['Normal'],dot.inputs[0])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.interpolation='CONSTANT'
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    bands=((0,.65),(.12,.83),(.48,1.0)) if PRECISE else ((0,.50),(.12,.72),(.48,1.0))
    for index,(at,factor) in enumerate(bands):
        e=ramp.color_ramp.elements[0] if index==0 else ramp.color_ramp.elements.new(at)
        e.position=at;e.color=(*(pow(c*factor,2.2) for c in colour),1)
    links.new(dot.outputs['Value'],ramp.inputs['Fac'])
    emission=nodes.new('ShaderNodeEmission');links.new(ramp.outputs['Color'],emission.inputs['Color'])
    output=nodes.new('ShaderNodeOutputMaterial');links.new(emission.outputs[0],output.inputs['Surface'])
    M[name]=mat


def assign(obj,mat):
    obj.data.materials.append(mat)
    return obj


def bevel(obj,width,segments=5):
    if width:
        mod=obj.modifiers.new('Moulded radii','BEVEL');mod.width=width*SCALE;mod.segments=min(segments,3)
    normals=obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');normals.keep_sharp=True
    return obj


def box(name,pos,size,mat,radius=2):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(*pos))
    obj=bpy.context.object;obj.name=name
    obj.dimensions=(size[0]*SCALE,size[2]*SCALE,size[1]*SCALE)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(obj,mat);bevel(obj,radius)
    return obj


def cut(obj,pos,size,radius=2):
    tool=box('Recess cutter',pos,size,M['black'],radius)
    bpy.context.view_layer.objects.active=tool
    for mod in list(tool.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active=obj
    for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
    mod=obj.modifiers.new('Recess','BOOLEAN');mod.operation='DIFFERENCE';mod.object=tool;mod.solver='FAST'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if not obj.data.vertices:raise RuntimeError('Empty recess result: '+obj.name)
    bpy.data.objects.remove(tool,do_unlink=True)


def cylinder(name,pos,radius,height,mat,axis='top',vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=min(vertices,32),radius=radius*SCALE,
                                       depth=height*SCALE,location=xyz(*pos))
    obj=bpy.context.object;obj.name=name
    if axis=='front': obj.rotation_euler[0]=math.pi/2
    if axis=='side': obj.rotation_euler[1]=math.pi/2
    assign(obj,mat);bevel(obj,min(height/4,1.2),3)
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def text(value,pos,size,mat,front=False,width=None):
    curve=bpy.data.curves.new('Moulded / printed legend','FONT');curve.body=value
    curve.font=bpy.data.fonts.load(str(FONT));curve.size=size*SCALE
    curve.align_x='CENTER';curve.align_y='CENTER';curve.extrude=0;curve.resolution_u=2
    obj=bpy.data.objects.new(value,curve);bpy.context.collection.objects.link(obj)
    obj.location=xyz(*pos)
    if front:obj.rotation_euler[0]=math.pi/2
    assign(obj,mat)
    if width:
        bpy.context.view_layer.update()
        if obj.dimensions.x>width*SCALE:obj.scale.x=width*SCALE/obj.dimensions.x
    return obj


def screw(x,y,z):
    cylinder('Countersunk fastener',(x,y,z),2.9,.7,M['metal'])
    box('Screw slot',(x,y+.5,z),(3.9,.45,.65),M['black'],.1)


def rounded_shell(name,rx,rz,y,depth,radius,mat,crown=0):
    # Perimeter rings give the N64 its broad, curved shoulder profile.
    vertices=[];count=64
    rings=[(1,y-depth),(1,y-4),(.995,y),(.94,y+crown)] if crown else [(1,y-depth),(1,y)]
    for scale,height in rings:
        for corner in range(4):
            for i in range(16):
                a=math.radians(-90+90*corner+90*i/15)
                x=((rx-radius if corner<2 else -rx+radius)+radius*math.cos(a))*scale
                z=((-rz+radius if corner in (0,3) else rz-radius)+radius*math.sin(a))*scale
                vertices.append(xyz(x,height,z))
    faces=[tuple(range(count-1,-1,-1))]
    for ring in range(len(rings)-1):
        for i in range(count):
            j=(i+1)%count;faces.append((ring*count+i,ring*count+j,(ring+1)*count+j,(ring+1)*count+i))
    faces.append(tuple(range((len(rings)-1)*count,len(rings)*count)))
    faces=[tuple(reversed(face)) for face in faces]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);assign(obj,mat)
    bevel(obj,1.4,4)
    for p in obj.data.polygons:p.use_smooth=len(p.vertices)==4
    return obj


def controller_port(x,y,z,family):
    before=set(bpy.context.scene.objects)
    if family=='n64':
        cylinder('Grey circular controller socket',(x,y,z),17.5,2.4,M['portgrey'],'front')
        cylinder('Circular keyed socket cavity',(x,y,z+1.7),13.8,2,M['black'],'front',32)
        plug=[(-13,-5),(13,-5)]+[(13*math.cos(a),-5+15*math.sin(a)) for a in [i*math.pi/12 for i in range(13)]]
        contour_shell('Three-hole controller insert',[(x+px,y+py) for px,py in plug],z+3,1,M['portgrey'],.3)
        for dx in (-8,0,8):
            cylinder('Pin receptacle',(x+dx,y+1,z+3.5),3.1,.5,M['black'],'front',16)
        for dx in (-5,0,5):box('Controller alignment recess',(x+dx,y-10,z+3),(2,1.6,.5),M['black'],.2)
    else:
        w,h=(70,19) if family=='snes' else (58,22)
        profile=[(-w/2,-h/2),(w/2,-h/2),(w/2+4,0),(w/2,h/2),(-w/2,h/2)] if family=='snes' else [(-w/2+5,-h/2),(w/2-5,-h/2),(w/2,h/2),(-w/2,h/2)]
        contour_shell('Controller bezel',[(x+px*1.09,y+py*1.18) for px,py in profile],z+1.5,3,M['portgrey'] if family=='snes' else M['metal'],.9)
        contour_shell('Controller cavity',[(x+px,y+py) for px,py in profile],z+2.8,1.5,M['black'],.6)
        rows=((7,0),) if family=='snes' else ((5,5),(4,-5))
        for count,dy in rows:
            for i in range(count):cylinder('Controller contact',(x+(i-(count-1)/2)*8,y+dy,z+3.6),1.1,.8,M['metal'],'front',12)
    # Only the housing needs the exaggerated height for this camera. Socket
    # dimensions remain physical, even when the enclosing deck is stretched.
    scale=2.3 if family=='n64' else 1.7
    physical_front_details(before,(x,y,z),scale)


def physical_front_details(before,pos,scale):
    centre=Vector(xyz(*pos))
    compensate=Matrix.Translation(centre)@Matrix.Diagonal(Vector((1,1,1/scale,1)))@Matrix.Translation(-centre)
    for obj in set(bpy.context.scene.objects)-before:obj.matrix_world=compensate@obj.matrix_world


def rear_connectors(name,s):
    z=-s['ry']-1;y=-40 if name=='nes' else -25
    if name=='n64':
        box('N64 removable power supply',(-130,-22,z+9),(116,28,32),M['blackbody'],5)
        box('N64 power lead socket',(-130,-24,z-9),(23,10,3),M['black'],2)
        x=63
    else:x=0
    before=set(bpy.context.scene.objects)
    if name.startswith('snes') or name=='n64':
        box('Multi AV bezel',(x,y,z),(48,14,3),M['darkgrey'],3)
        box('Multi AV socket',(x,y,z-2),(40,8,2),M['black'],2)
        for dx in range(-15,16,6):box('Multi AV contact',(x+dx,y,z-3.2),(2,2,1),M['metal'],.2)
    if name.startswith('snes'):
        cylinder('Rear RF output',(-83,y,z-2),5,3,M['metal'],'front',16)
        cylinder('Rear RF opening',(-83,y,z-4),3,1,M['black'],'front',16)
        box('Rear DC socket',(85,y,z-2),(19,10,3),M['black'],2)
    elif name.startswith('md'):
        for x,label in ((-110,'DC'),(-43,'RF'),(51,'AV')):
            radius=9 if label=='AV' else 5
            cylinder('Rear '+label+' trim',(x,y,z-1),radius,2,M['metal'],'front',24)
            cylinder('Rear '+label+' socket',(x,y,z-2.5),radius-2,1,M['black'],'front',24)
        for angle in range(0,360,45):
            a=math.radians(angle);cylinder('DIN contact',(51+5*math.cos(a),y+5*math.sin(a),z-3.2),.7,.5,M['metal'],'front',8)
    elif name=='nes':
        for x,label in ((-107,'RF'),(-43,'DC')):
            cylinder('NES rear '+label+' trim',(x,y,z-1),6,2,M['metal'],'front',16)
            cylinder('NES rear '+label+' socket',(x,y,z-2.5),4,1,M['black'],'front',16)
        box('NES channel switch',(29,y,z-2),(19,8,2),M['black'],1)
    physical_front_details(before,(0,y,z),s['yscale'])
    if name=='nes':
        before=set(bpy.context.scene.objects)
        for zz,c in ((37,'yellow'),(64,'red')):
            cylinder('NES RCA collar',(s['rx']+1,-39,zz),7,3,M[c],'side',20)
            cylinder('NES RCA opening',(s['rx']+3,-39,zz),4,2,M['black'],'side',16)
        physical_front_details(before,(s['rx'],-39,0),s['yscale'])


def plate(name,pos,width,length,height,radius,mat):
    obj=rounded_shell(name,width/2,length/2,pos[1]+height/2,height,radius,mat)
    obj.location.x=pos[0]*SCALE;obj.location.y=-pos[2]*SCALE
    return obj


def oval(name,pos,width,length,height,mat):
    obj=cylinder(name,pos,width/2,height,mat)
    obj.scale.y=length/width
    return obj


def media_slot(name,s,housings,y):
    """Physical cavity for the seated media, cut through every listed housing.

    The opening fits the physical cartridge thickness with 1 mm clearance; the
    cavity reaches below the seated cartridge and is lined dark. This is a fit
    correction for the newer media, not a remodel of the console housing.
    """
    q=MEDIA_SCALES[name];depth=18 if name=='pico8' else media.opening(name)
    bottom=y-(s['sink']+2*q)/s['yscale'];top=y+30;width=s['mouth'];z=s['slot']
    for obj in housings:
        tool=box('Recess cutter',(0,(top+bottom)/2,z),(width,top-bottom,depth),M['black'],min(depth/3,6))
        bpy.context.view_layer.objects.active=tool
        for mod in list(tool.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        # FAST keeps the moulded shells' existing shading, as the earlier slot did.
        mod=obj.modifiers.new('Physical media cavity','BOOLEAN');mod.operation='DIFFERENCE'
        mod.object=tool;mod.solver='FAST'
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tool,do_unlink=True)
    wall=y-3-bottom
    box('Dark cartridge well',(0,bottom+.6,z),(width-1.2,1.2,depth-1.2),M['black'],0)
    for dz in (-1,1):box('Dark slot lining',(0,bottom+wall/2,z+dz*(depth/2-.2)),(width-.8,wall,.4),M['black'],0)
    for dx in (-1,1):box('Dark slot lining',(dx*(width/2-.2),bottom+wall/2,z),(.4,wall,depth-.8),M['black'],0)


def cartridge_slot(deck,x,z,width,depth,y=0):
    cut(deck,(x,y-4,z),(width,27,depth),depth/3)
    box('Dark cartridge well',(x,y-16,z),(width-2,2,depth-2),M['black'],2)
    for dz in (-depth*.25,depth*.25):
        box('Spring-loaded dust cover',(x,y-5,z+dz),(width-4,1.5,depth*.43),M['slotgrey'],1)


def home(name,s):
    rx,rz=s['rx'],s['ry'];front=rz
    if name=='pico8':
        # An original fantasy console, not a replica of nonexistent hardware.
        lower=rounded_shell('Fantasy 8 lower housing',rx-2,rz-2,-13,47,24,M['blackbody'])
        deck=rounded_shell('Fantasy 8 red deck',rx,rz,2,20,24,M['picored'],10)
        media_slot(name,s,[deck,lower],12)
        rim=box('Cart retaining rim',(0,12,-34),(158,2,24),M['blackbody'],4)
        cut(rim,(0,12,-34),(148,15,18),2)
        box('Eject lever well',(0,12,13),(62,2,30),M['darkink'],4)
        box('Eject lever',(0,15,10),(52,6,22),M['white'],4)
        text('EJECT',(0,18.3,11),9,M['ink'])
        text('FANTASY',(0,12.7,-100),14,M['white'],width=106)
        for x in (-148,148):
            for z in range(-81,76,12):box('Deck ventilation',(x,12.4,z),(27,1,3),M['blackbody'],.4)
        cylinder('Power button well',(0,12.5,82),15,2,M['darkink'],vertices=24)
        cylinder('Power button',(0,14,82),11,6,M['white'],vertices=24)
        text('I',(0,17.1,82),9,M['ink'])
        cylinder('Cyan power LED',(34,13,83),2.7,1,M['picocyan'],vertices=16)
        for x in (-88,88):
            box('Controller socket trim',(x,-29,front),(61,25,4),M['picored'],6)
            box('Controller socket',(x,-29,front+2),(49,15,3),M['darkink'],4)
            for dx in (-12,0,12):box('Controller socket contact',(x+dx,-29,front+4),(2,5,1),M['gold'],.2)
            text('1' if x<0 else '2',(x,-45,front+1.5),7,M['white'],True)
        box('Front emblem plaque',(0,-27,front),(41,36,3),M['darkink'],6)
        for y in (-16,-27,-38):box('Pixel eight crossbar',(0,y,front+2),(18,3,1),M['white'],0)
        for x in (-8,8):box('Pixel eight upright',(x,-27,front+2),(3,22,1),M['white'],0)
        for x in (-rx+1,rx-1):
            for z in range(-68,77,12):box('Side ventilation',(x,-22,z),(2,14,4),M['darkink'],1)
        box('Rear power socket',(-65,-30,-rz),(19,10,3),M['darkink'],3)
        box('Rear display socket',(65,-30,-rz),(36,11,3),M['metal'],2)
        for x in (-158,158):
            for z in (-87,87):box('Rubber foot',(x,-62,z),(30,5,30),M['darkink'],7)
    elif name.startswith('snes'):
        us=name.endswith('us');body=M['usgrey'] if us else M['snesgrey']
        lower=rounded_shell('Lower half',rx,rz,-20,s['depth']-20,9 if us else 26,M['darkgrey'])
        if us:
            deck=box('Upper stepped shell',(0,-7,0),(rx*2,26,rz*2),body,7)
            rails=[box('Raised shoulder rail',(x,7,-35),(88,20,390),body,5) for x in (-151,151)]
            pod=box('Raised cartridge deck',(0,15,-116),(274,30,200),body,7)
            media_slot(name,s,[pod,deck,*rails],30)
            box('Eject button',(0,7,49),(89,8,125),M['buttonlight'],4)
            text('EJECT',(0,11.5,76),10,M['ink'])
            for x,label in ((-120,'POWER'),(120,'RESET')):
                box('Switch track',(x,5,32),(85,2,108),M['darkgrey'],4)
                box('Purple slider',(x,13,10),(100,13,43),M['purple'],9)
                text(label,(x,20,11),10,M['white'])
            text('SUPER NINTENDO',(0,31,-202),16,M['ink'],width=183)
            text('ENTERTAINMENT SYSTEM',(0,31,-181),7,M['ink'],width=170)
        else:
            deck=rounded_shell('Rounded upper shell',rx,rz,-2,19,29,body,8)
            panel=box('Inset grey control panel',(0,8,-5),(381,4,288),M['snespanel'],15)
            media_slot(name,s,[panel,deck,lower],10)
            box('Eject lever',(0,12,26),(97,8,55),M['buttonlight'],10)
            text('EJECT',(0,16.5,29),10,M['ink'])
            for x,label in ((-151,'POWER'),(151,'RESET')):
                box('Switch recess',(x,8,24),(58,3,82),M['darkgrey'],13)
                box('Switch cap',(x,14,21),(44,8,35),M['buttonlight'],8)
                text(label,(x,10.6,82),9,M['ink'])
            text('SUPER NINTENDO',(0,10.6,104),13,M['ink'],width=158)
            for x,z,c in ((179,-114,'red'),(193,-100,'blue'),(165,-100,'green'),(179,-86,'yellow')):
                cylinder('Four-colour mark',(x,10.6,z),6.8,.5,M[c],vertices=32)
        for x in (-118,118):controller_port(x,-24,front+1,'snes')
        cylinder('Power LED',(-190,-22,front+1),2,1,M['red'],'front')
        for x in (-rx+3,rx-3):
            for z in range(-95,76,10):box('Side vent',(x,-13,z),(2,7,4),M['black'],.3)
    elif name=='n64':
        for x in (-190,190):box('Rounded console foot',(x,-29,105),(78,21,89),M['blackbody'],23)
        lower=rounded_shell('Lower curved shell',rx,rz,-19,17,52,M['blackbody'],2)
        deck=rounded_shell('Domed upper shell',rx,rz,-6,11,52,M['n64'],12)
        media_slot(name,s,[deck,lower],6)
        for x in range(-107,108,12):box('Cartridge cooling louver',(x,7,-30),(5,2,23),M['black'],1)
        plate('Expansion hatch seam',(0,8,57),129,91,3,18,M['black'])
        plate('Expansion hatch',(0,9,57),125,87,3,17,M['n64'])
        box('Hatch finger catch',(0,11,25),(29,2,13),M['black'],3)
        text('MEMORY EXPANSION',(0,11,77),6,M['darkink'])
        for x,label in ((-154,'POWER'),(154,'RESET')):
            oval('Recessed oval switch',(x,6,69),43,62,2,M['black'])
            oval('Raised switch',(x,10,64),33,43,8,M['n64'])
            text(label,(x,15,65),7,M['darkink'])
        for x in (-174,-72,72,174):controller_port(x,-20,front-1,'n64')
        before=set(bpy.context.scene.objects)
        box('Front logo plaque',(0,-17,front),(59,44,3),M['black'],6)
        text('NINTENDO 64',(0,-4,front+2),7,M['white'],True,width=53)
        points=[(-14,-12),(-14,12),(-6,12),(7,-3),(7,12),(14,12),(14,-12),(6,-12),(-7,3),(-7,-12)]
        logo=contour_shell('Multicolour raised N emblem',[(x,-22+y) for x,y in points],front+7,5,M['green'],.25)
        for mat in (M['blue'],M['yellow'],M['red']):logo.data.materials.append(mat)
        for face in logo.data.polygons:
            if abs(face.normal.x)>.5:face.material_index=1
            elif face.normal.z>.5:face.material_index=2
            elif face.normal.z<-.5:face.material_index=3
        physical_front_details(before,(0,-17,front),s['yscale'])
        for x in (-rx+1,rx-1):
            for z in range(-95,96,10):box('Side cooling louver',(x,-13,z),(2,11,4),M['black'],.3)
    elif name.startswith('md'):
        lower=rounded_shell('Lower shell',rx,rz,-21,17,31,M['blackbody'])
        lower.location.x=-45*SCALE
        deck=rounded_shell('Upper shell',rx,rz,-2,18,32,M['sega'],5)
        deck.location.x=-45*SCALE
        surround=cylinder('Circular cartridge surround',(0,3,-18),151,9,M['blackbody'])
        disc=cylinder('Raised round deck',(0,8,-18),146,4,M['sega'])
        media_slot(name,s,[disc,surround,deck,lower],10)
        bpy.ops.mesh.primitive_torus_add(major_radius=136*SCALE,minor_radius=.8*SCALE,
            major_segments=128,minor_segments=12,location=xyz(0,11,-18))
        assign(bpy.context.object,M['gold'] if name=='md-jp' else M['darkgrey'])
        text('16-BIT',(0,11.4,30),34 if name=='md-jp' else 14,M['gold'] if name=='md-jp' else M['white'],width=154)
        text('SEGA',(116,7,129),18,M['silver'],width=68)
        text('MEGA DRIVE' if name=='md-jp' else 'GENESIS',(0,12,-107 if name=='md-jp' else -5),16 if name=='md-jp' else 25,M['white'],width=161)
        for z in range(-125,22,8):box('Deck cooling louver',(-224,4,z),(63,2,3),M['black'],.8)
        controls_before=set(bpy.context.scene.objects)
        plate('Left control panel',(-173,5,76),104,105,2,8,M['blackbody'])
        box('Power switch recess',(-148,7,47),(42,2,29),M['black'],3)
        box('Power slider',(-148,11,47),(18,7,23),M['sega'],2)
        text('ON',(-172,7.5,44),5,M['silver'])
        text('OFF',(-123,7.5,44),5,M['silver'])
        box('Reset recess',(-148,7,94),(47,2,24),M['black'],3)
        box('Reset button',(-148,10,94),(39,5,18),M['blue'] if name=='md-jp' else M['buttonlight'],2)
        text('RESET',(-148,7.5,117),6,M['silver'])
        box('Volume track',(-204,7,71),(17,2,67),M['black'],1)
        for i in range(8):box('Volume slider tick',(-218,7.5,42+i*7),(4,1,1),M['silver'],.1)
        box('Volume slider',(-204,11,78),(18,7,12),M['sega'],1)
        text('VOLUME',(-204,7.5,119),5,M['silver'])
        for o in set(bpy.context.scene.objects)-controls_before:o.location.x-=33*SCALE
        for x in (21,146):controller_port(x,-23,front+1,'md')
        box('Power indicator window',(-102,9,76),(17,1,9),M['red'],1)
        before=set(bpy.context.scene.objects)
        cylinder('Front headphone trim',(-220,-25,front+1),6,2,M['metal'],'front',20)
        cylinder('Front headphone socket',(-220,-25,front+2.5),4,1,M['black'],'front',16)
        physical_front_details(before,(-220,-25,front),s['yscale'])
    elif name=='nes':
        chassis=box('Dark lower chassis',(0,-39,0),(rx*2,34,rz*2),M['nesdark'],5)
        deck=box('Upper ivory cover',(0,-10,0),(rx*2,26,rz*2),M['nesgrey'],4)
        cut(deck,(-45,-13,front-17),(280,35,40),2)
        # Fit correction: the physical Game Pak slides fully inside, then presses
        # down. The tunnel keeps a roof under the cover; the door opening stays.
        for obj in (deck,chassis):physical_cut(sys.modules[__name__],obj,(-45,-16.5,(front+5-85)/2),(280,35,front+5+85))
        box('Loading tunnel',(-45,-16.5,-84.6),(278,34,.8),M['black'],0)
        box('Loading tunnel floor',(-45,-33.6,(front-85)/2),(278,.8,front+85),M['black'],0)
        box('Loading tunnel roof',(-45,.6,(133-85)/2),(278,.8,133+85),M['black'],0)
        for x in (-184.6,94.6):box('Loading tunnel wall',(x,-16.5,(front-85)/2),(.8,34,front+85),M['black'],0)
        box('Loading tray',(-45,-27,front-3),(270,3,45),M['slotgrey'],2)
        box('Right black trim',(160,4,0),(75,4,rz*2-5),M['blackbody'],.7)
        for z in range(-119,85,10):box('Top cooling louver',(160,7,z),(58,2,3),M['black'],.6)
        for x,label in ((-172,'POWER'),(-105,'RESET')):
            box('Front control button',(x,-42,front+2),(46,13,5),M['buttonlight'],1)
            text(label,(x,-32,front+3),5.5,M['white'],True)
        cylinder('Power LED',(-206,-43,front+3),2,1,M['red'],'front')
        for x in (112,177):
            before=set(bpy.context.scene.objects)
            box('NES controller surround',(x,-37,front+2),(43,31,3),M['nesgrey'],2)
            box('NES seven pin socket',(x,-37,front+4),(34,23,2),M['black'],2)
            for i in range(3):cylinder('NES socket pin',(x-8+i*8,-34,front+5),1.3,1,M['metal'],'front',16)
            for i in range(4):cylinder('NES socket pin',(x-12+i*8,-41,front+5),1.3,1,M['metal'],'front',16)
            physical_front_details(before,(x,-37,front),s['yscale'])
        text('Nintendo',(160,-8,front+2),12,M['red'],True,width=85)
    if name!='pico8':rear_connectors(name,s)


def handheld(name,s):
    if name=='gb':return authored_dmg()
    rx,ry,d=s['rx'],s['ry'],s['depth'];body=M[name]
    outline=[]
    for cx,cy,radius,angle in ((rx-10,ry-10,10,0),(-rx+10,ry-10,10,90),(-rx+12,-ry+12,12,180),(rx-33,-ry+33,33,270)):
        if name=='gbc' and angle==270:cx,cy,radius=rx-23,-ry+23,23
        for i in range(13):
            a=math.radians(angle+i*90/12);outline.append((cx+radius*math.cos(a),cy+radius*math.sin(a)))
    shell=contour_shell('Moulded handheld housing',outline,d,2*d,body,1.5)
    # The rear bay is open to the top. Its actual recess becomes visible as the
    # full housing turns, with opaque side rails and a lower retaining lip.
    floor=s['slot'];cut(shell,(0,(ry+floor)/2,-d+8),(s['mouth'],ry-floor+8,27),3)
    box('Cartridge bay inner wall',(0,(ry+floor)/2,-d+21),(s['mouth']-5,ry-floor,2),M['darkgrey'],2)
    box('Cartridge connector',(0,floor+4,-d+9),(s['mouth']-10,8,12),M['black'],2)
    contour_shell('Shell parting seam',[(x*1.004,y) for x,y in outline],.6,1.2,M['darkgrey'],.3)
    # Front: asymmetric controls, inset LCD, printed bezel and speaker grille.
    bezel=box('LCD bezel',(0,ry*.48,d+1),(rx*1.73,ry*.91,4),M['screenbezel'] if name=='gb' else M['blackbody'],13)
    lcd_w=89 if name=='gb' else 100
    lcd_h=lcd_w*144/160
    box('Inset LCD border',(0,ry*.50,d+3.2),(lcd_w+8,lcd_h+7,1.8),M['black'],2)
    box('LCD glass',(0,ry*.50,d+4.3),(lcd_w,lcd_h,1.0),M['lcdgreen'] if name=='gb' else M['lcdblack'],1)
    if name=='gb':
        text('DOT MATRIX WITH STEREO SOUND',(0,ry*.91,d+3.3),4.8,M['white'],True,width=126)
    else:
        text('GAME BOY',(-23,15,d+3.3),9,M['white'],True,width=76)
        for letter,x,c in zip('COLOR',(22,31,40,49,58),('red','blue','green','yellow','magenta')):
            text(letter,(x,15,d+3.3),9,M[c],True)
    text('Nintendo GAME BOY' if name=='gb' else 'Nintendo',(0,-1,d+2),10 if name=='gb' else 9,M['blueink'],True,width=140)
    x,y=-48,-49
    for half,arm,z,depth,mat,label in ((23,9,d+2,1.2,M['darkgrey'],'D-pad socket'),(21,7,d+8,6,M['blackbody'],'Continuous D-pad')):
        if name=='gbc' and label=='D-pad socket':
            cylinder('GBC circular D-pad recess',(x,y,d+1.5),26,1.2,M['darkgrey'],'front',32)
            continue
        points=cross_profile(half,arm)
        contour_shell(label,[(x+px,y+py) for px,py in points],z,depth,mat,.8)
    cylinder('D-pad thumb centre',(x,y,d+8.5),5,.7,M['black'],'front',20)
    for x,y,label in ((39,-53,'B'),(61,-38,'A')):
        cylinder('Button socket',(x,y,d+1),13,2,M['darkgrey'],'front',32)
        cylinder('Action button '+label,(x,y,d+6),10.5,8,M['magenta'] if name=='gb' else M['blackbody'],'front',32)
        text(label,(x+3,y-20,d+2),7,M['blueink'],True)
    for x,label in ((-18,'SELECT'),(14,'START')):
        o=box(label+' button',(x,-90,d+5),(24,8,6),M['darkgrey'],3);o.rotation_euler[1]=math.radians(-22)
        text(label,(x,-104,d+2),4.8,M['blueink'],True)
    if name=='gb':
        for i in range(6):
            o=box('Speaker slot',(35+i*6,-111+(i%2)*2,d+2),(2,21,2),M['black'],.8);o.rotation_euler[1]=math.radians(-24)
    else:
        for row in range(8):
            for col in range(8):
                if (col-3.5)**2+(row-3.5)**2<18:
                    cylinder('GBC speaker perforation',(47+(col-3.5)*5,-111+(row-3.5)*5,d+2),1.25,1,M['black'],'front',8)
    cylinder('Battery indicator',(-62,ry*.51,d+4),2.0,1,M['red'],'front',20)
    # Rear cover, latch and screw wells are geometry, not a painted photograph.
    if name=='gbc':box('GBC curved battery housing',(0,-67,-d-3),(148,154,14),body,20)
    rear_before=set(bpy.context.scene.objects)
    box('Battery cover seam',(0,-65,-d-.6),(137,119,1),M['darkgrey'],10)
    box('Battery cover',(0,-65,-d-1.5),(132,114,2),body,9)
    box('Battery latch recess',(0,-8,-d-2),(27,12,2),M['darkgrey'],3)
    box('Battery latch',(0,-9,-d-3),(20,7,2),body,2)
    for y in range(-117,-101,4):box('Cover finger rib',(0,y,-d-3),(44,1.2,1.5),body,.4)
    # Rear lettering faces outward and remains readable after a half turn.
    for value,y,size in [('Nintendo',-30,11),('GAME BOY COLOR' if name=='gbc' else 'GAME BOY',-50,7),('CGB-001' if name=='gbc' else 'DMG-01',-69,5)]:
        o=text(value,(0,y,-d-3),size,M['darkink'],True,width=105);o.rotation_euler[2]=math.pi
    if name=='gbc':
        for o in set(bpy.context.scene.objects)-rear_before:o.location.y+=10*SCALE
    for x,y in ((-72,ry-25),(72,ry-25),(-72,14),(72,14),(-57,-ry+15),(57,-ry+15)):
        rear_d=d+10 if name=='gbc' and y<0 else d
        cylinder('Rear screw well',(x,y,-rear_d-1),3.2,1,M['darkgrey'],'front',20)
        cylinder('Rear screw',(x,y,-rear_d-2),1.5,1,M['metal'],'front',16)
    side=1 if name=='gb' else -1
    box('Link connector',(side*(rx+1),45,0),(3,19,11),M['black'],2)
    box('Volume wheel',(side*(rx+1),-7,0),(4,27,12),M['darkgrey'],2)
    for yy in range(-18,7,4):box('Volume grip',(side*(rx+3),yy,0),(1,1,12),M['black'],.2)
    if name=='gb':
        box('Contrast wheel',(-rx-1,66,0),(4,27,12),M['darkgrey'],2)
        box('Top power switch',(-52,ry+1,0),(25,3,12),M['darkgrey'],2)
    else:
        box('Power switch',(rx+1,ry-26,0),(4,19,10),M['darkgrey'],2)
        box('Infrared window',(49,ry+1,0),(31,3,15),M['darkink'],3)
    if name=='gb':cylinder('External power socket',(-rx-1,-81,0),4.5,2,M['black'],'side',16)
    else:cylinder('External power socket',(35,-ry-1,0),4.5,2,M['black'],vertices=16)
    cylinder('Headphone jack',(-35 if name=='gbc' else 0,-ry-1,0),5,2,M['black'],vertices=24)


def advance_sp(s):
    body=M['gba']
    base=box('SP lower housing',(0,-65,0),(224,40,224),body,12)
    cut(base,(0,-59,105),(s['mouth'],14,40),2)
    box('Cartridge connector',(0,-59,87),(s['mouth']-8,9,2),M['black'],1)
    box('SP upper control deck',(0,-42,-1),(217,5,215),body,10)
    box('SP deck seam',(0,-69,0),(225,1,217),M['darkgrey'],9)
    for x in (-65,65):cylinder('Hinge barrel',(x,-36,-103),12,94,body,'side',32)
    cylinder('Hinge central joint',(0,-36,-103),10,32,M['darkgrey'],'side',32)
    before=set(bpy.context.scene.objects)
    box('SP display lid',(0,71,-104),(217,200,16),body,12)
    box('SP screen bezel',(0,71,-94.8),(191,173,3),M['screenbezel'],5)
    box('SP LCD glass',(0,82,-92.7),(165,110,1.3),M['lcdblack'],2)
    text('GAME BOY ADVANCE SP',(0,8,-92.5),8,M['white'],True,width=180)
    for o in set(bpy.context.scene.objects)-before:
        p=o.location-Vector(xyz(0,-29,-103));q=Matrix.Rotation(math.radians(13),4,'X')
        o.location=Vector(xyz(0,-29,-103))+q@p;o.rotation_euler=(q@o.rotation_euler.to_matrix().to_4x4()).to_euler()
    x,z=-67,-5
    cylinder('SP D-pad recess',(x,-38,z),27,2,M['darkgrey'],vertices=40)
    top_profile('SP continuous D-pad',cross_profile(21,7),(x,-35,z),6,M['buttonlight'],.9)
    for x,z,label in ((56,7,'B'),(83,-12,'A')):
        cylinder('SP button socket',(x,-38,z),13,2,M['darkgrey'])
        cylinder('SP action button',(x,-34,z),10,7,M['buttonlight'])
        text(label,(x,-29.8,z),6,M['ink'])
    for x,label in ((-23,'SELECT'),(23,'START')):
        cylinder('SP '+label,(x,-35,81),7,7,M['buttonlight'])
        text(label,(x,-39,95),5,M['white'])
    for x in (-13,-6,1,8,15):
        for z in (18,25,32):cylinder('SP speaker perforation',(x,-38,z),1.7,1,M['black'],vertices=12)
    cylinder('SP brightness button',(0,-36,-70),5,5,M['buttonlight'])
    box('SP power LED',(113,-43,-45),(2,5,12),M['green'],1)
    box('SP charging LED',(113,-43,-64),(2,4,9),M['yellow'],1)
    box('SP power slider',(113,-63,21),(3,8,21),M['darkgrey'],2)
    box('SP volume track',(-113,-63,23),(3,7,36),M['darkgrey'],2)
    box('SP volume slider',(-115,-63,17),(2,8,10),M['buttonlight'],1)
    for x,label in ((-28,'EXT.1'),(28,'EXT.2')):
        box('SP '+label+' connector trim',(x,-63,-113),(30,11,3),M['metal'],2)
        box('SP '+label+' connector',(x,-63,-115),(25,7,2),M['black'],1)
        for dx in (-7,0,7):box('SP connector contact',(x+dx,-63,-116.3),(1.5,2,1),M['metal'],.2)
    box('SP battery cover seam',(0,-85,8),(137,1,122),M['darkgrey'],5)
    box('SP battery cover',(0,-86,8),(132,2,117),body,4)
    cylinder('SP battery fastener',(0,-87,-41),3,1,M['metal'],vertices=16)
    for x in (-94,94):
        box('SP shoulder button',(x,-46,-98),(28,14,18),M['buttonlight'],5)
        text('L' if x<0 else 'R',(x,-38.5,-98),6,M['ink'])


def cross_profile(half,arm):
    return [(-arm,-half),(arm,-half),(arm,-arm),(half,-arm),(half,arm),(arm,arm),(arm,half),(-arm,half),(-arm,arm),(-half,arm),(-half,-arm),(-arm,-arm)]


def top_profile(name,points,pos,depth,mat,radius=.8):
    """One continuous moulding, including concave profiles such as a D-pad."""
    n=len(points)
    vertices=[xyz(pos[0]+x,pos[1]+dy,pos[2]+z)
              for dy in (-depth/2,depth/2) for x,z in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    assign(o,mat);bevel(o,radius,3)
    return o


def ds_lite(s):
    body=M['dswhite'];dark=M['darkgrey']
    base=box('DS Lite lower housing',(0,-65,0),(404,38,226),body,12)
    seam=box('DS deck seam',(0,-68,0),(405,1,220),M['dsseam'],10)
    # Fit correction: Slot-1 now receives the physical 35-mm card completely.
    for obj in (base,seam):physical_cut(sys.modules[__name__],obj,(-28,-65,-72),(s['mouth'],12,116))
    box('Slot-1 connector',(-28,-65,-14.8),(s['mouth']-7,8,1.2),M['black'],0)
    box('Slot-1 upper lip',(-28,-58,-114),(s['mouth']+5,2,3),dark,1)
    box('Slot-1 dark lining',(-28,-70.8,-65.25),(s['mouth']-1,.4,96.5),M['black'],0)
    box('DS control deck',(0,-43,0),(396,5,218),body,10)
    # Slot-2 filler, headphone/microphone socket, volume slider and stylus.
    box('Slot-2 cover seam',(0,-63,113),(153,14,2),M['dsseam'],2)
    box('Slot-2 dust cover',(0,-63,114),(148,11,3),body,2)
    cylinder('Headphone socket',(125,-65,114),5,2,M['black'],'front',24)
    box('Microphone connector',(143,-65,114),(9,7,2),M['black'],1)
    box('Volume track',(-144,-66,113),(39,7,2),dark,2)
    box('Volume slider',(-142,-66,115),(16,6,3),body,1)
    for x in (-146,-142,-138):box('Volume grip',(x,-66,117),(1,4,.5),M['dsseam'],.1)
    text('VOL.',(-143,-56,115),4,M['ink'],True)
    box('Stylus silo',(195,-66,30),(3,13,130),dark,2)
    box('Stylus cap',(197,-65,91),(6,12,23),body,2)
    box('Power switch recess',(203,-64,60),(3,17,27),dark,2)
    box('Power switch',(204,-61,60),(4,10,21),body,2)
    box('Charger socket',(77,-65,-115),(30,10,3),M['black'],2)
    box('Charger metal surround',(77,-65,-114),(34,14,1),M['metal'],2)
    box('Charger socket interior',(77,-65,-115.7),(25,7,1),M['black'],1)
    for x in (71,83):box('Charging contact',(x,-65,-116),(2,3,1),M['gold'],.2)
    box('Wrist strap recess',(127,-66,-114),(15,10,3),M['black'],3)
    box('Wrist strap bridge',(127,-66,-115),(3,10,3),body,1)
    for x,label in ((-172,'L'),(172,'R')):
        box('DS shoulder key seam',(x,-53,-104),(55,14,22),M['dsseam'],6)
        box('DS '+label+' shoulder key',(x,-52.5,-105),(52,12,21),body,6)
        legend=text(label,(x,-53,-116),6,M['ink'],True)
        legend.rotation_euler[2]=math.pi
    # Fixed end knuckles belong to the base; the long middle knuckle belongs
    # to the lid. Narrow collar seams replace the old three oversized bars.
    for x in (-178.5,178.5):
        box('DS hinge root',(x,-42,-102),(40,17,20),body,5)
        cylinder('DS fixed hinge knuckle',(x,-34,-103),9.8,40,body,'side',32)
        cylinder('DS hinge end cap',(x+(-20 if x<0 else 20),-34,-103),8.8,.8,body,'side',24)
    for x in (-157.5,157.5):
        cylinder('DS hinge collar seam',(x,-34,-103),9.1,1.2,M['dsseam'],'side',32)
    cylinder('DS rotating lid knuckle',(0,-34,-103),9.2,313,body,'side',32)
    for x,c in ((179,'green'),(187,'yellow')):
        box('DS indicator window',(x,-26.4,-101),(4.2,1.2,7.2),M['dsseam'],.7)
        box('Status indicator',(x,-25.8,-101),(2.8,.5,5.7),M[c],.5)
    box('Touchscreen gasket',(0,-40,1),(203,2,152),M['dsseam'],2)
    box('Touchscreen frame',(0,-39,1),(199,1,149),body,2)
    box('Bottom LCD',(0,-37.7,1),(191,1.4,143),M['glass'],1)
    x=-148
    cross=[(-7,-22),(7,-22),(7,-7),(22,-7),(22,7),(7,7),
           (7,22),(-7,22),(-7,7),(-22,7),(-22,-7),(-7,-7)]
    top_profile('DS D-pad socket',[(dx*1.06,dz*1.06) for dx,dz in cross],
                (x,-40.1,-3),.7,M['dsseam'],1)
    top_profile('DS continuous D-pad',cross,(x,-38.7,-3),4,body,1)
    for dx,dz in ((0,-15),(0,15),(-15,0),(15,0)):
        box('D-pad moulded groove',(x+dx,-36.62,-3+dz),
            (7 if dz else .75,.15,.75 if dz else 7),M['dsseam'],0)
    for x,z,label in ((148,-30,'X'),(176,-3,'A'),(148,24,'B'),(121,-3,'Y')):
        cylinder('DS button recess',(x,-40.1,z),10.1,.8,M['dsseam'],vertices=32)
        cylinder('DS '+label+' button',(x,-38.2,z),9.2,4,body,vertices=32)
        text(label,(x,-36.12,z),7,M['ink'])
    for z,label in ((65,'START'),(86,'SELECT')):
        cylinder('DS '+label+' socket',(152,-40.2,z),5.4,.6,M['dsseam'],vertices=20)
        cylinder('DS '+label,(152,-39,z),4.6,2.6,body,vertices=20)
        text(label,(175,-40.1,z),4.8,M['ink'],width=29)
    cylinder('Microphone opening',(0,-24.9,-101.5),1.7,.5,M['darkink'],vertices=16)
    text('MIC.',(0,-25.5,-92),3.8,M['ink'])
    # Full open lid, including rear shell, printed marks and both speaker grilles.
    before=set(bpy.context.scene.objects)
    box('DS display lid',(0,77,-108),(399,202,19),body,10)
    box('Upper shell seam',(0,77,-112.5),(398,201,1),M['dsseam'],9)
    box('Lid inner fascia',(0,77,-98.5),(391,194,2),body,8)
    box('DS lid hinge neck',(0,-24,-105),(312,15,13),body,3)
    box('Upper LCD gasket',(0,77,-97.2),(203,153,1),M['dsseam'],2)
    box('Upper LCD frame',(0,77,-96.8),(199,150,1),body,2)
    box('Top LCD',(0,77,-96),(191,143,1.3),M['glass'],1)
    for x in (-155,155):
        for dx in (-4.5,4.5):
            for y in (74,83,92):cylinder('DS speaker perforation',(x+dx,y,-96.8),1.9,1,M['darkink'],'front',12)
    for x in (-184,184):
        for y in (-12,159):box('Lid rubber bumper',(x,y,-96.5),(7,11,2),M['dsrubber'],2)
    # The outer lid carries two embossed screen outlines, not filled bars.
    for y in (56,96):
        for x in (-27,27):box('Embossed DS emblem',(x,y,-118),(1.8,32,.6),M['dsseam'],.4)
        for dy in (-16,16):box('Embossed DS emblem',(0,y+dy,-118),(54,1.8,.6),M['dsseam'],.4)
    for o in set(bpy.context.scene.objects)-before:
        p=o.location-Vector(xyz(0,-34,-103));q=Matrix.Rotation(math.radians(-55),4,'X')
        o.location=Vector(xyz(0,-34,-103))+q@p;o.rotation_euler=(q@o.rotation_euler.to_matrix().to_4x4()).to_euler()
    box('DS battery cover seam',(72,-85,0),(148,2,169),M['dsseam'],5)
    box('DS battery cover',(72,-86,0),(144,2,165),body,4)
    cylinder('Battery cover screw',(72,-87,-72),3,1,M['metal'],vertices=16)
    text('Nintendo DS Lite',(-92,-85,0),7,M['ink'],width=144)
    for x,z in ((-176,90),(176,90),(-175,-80),(175,-80)):
        cylinder('Bottom screw well',(x,-86,z),3,.8,M['darkgrey'],vertices=16)


def contour_shell(name,points,z,depth,mat,radius=2.2,segments=3):
    """Moulded vertical shell with the PSP's asymmetric shoulder/heel outline."""
    n=len(points);vertices=[xyz(x,y,zz) for zz in (z-depth,z) for x,y in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);assign(o,mat);bevel(o,radius,segments)
    return o


def cut_profile(obj,name,profile,top,depth):
    """Subtract an original planar profile without scaling its opening."""
    cutter=contour_shell('Aperture cutter',profile,top,depth,M['black'],0)
    bpy.context.view_layer.objects.active=obj
    for modifier in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    modifier=obj.modifiers.new(name,'BOOLEAN');modifier.operation='DIFFERENCE'
    modifier.object=cutter;modifier.solver='EXACT'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


def stroke(name,points,z,mat,width=1.5):
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        o=box(name,((a[0]+b[0])/2,(a[1]+b[1])/2,z),(math.hypot(dx,dy)+width,width,.6),mat,0)
        o.rotation_euler[1]=-math.atan2(dy,dx)
        o['printed']=True


def psp_mark(y,z,mat,scale=1,rear=False):
    for offset,points in ((-26,[(0,-7),(0,7),(19,7),(19,0),(0,0)]),
                          (-4,[(19,7),(0,7),(0,0),(19,0),(19,-7),(0,-7)]),
                          (20,[(0,-7),(0,7),(19,7),(19,0),(0,0)])):
        stroke('PSP wordmark',[((x+offset-6)*scale*(-1 if rear else 1),y+dy*scale) for x,dy in points],z,mat,1.6*scale)


def ink_path(name,points,z,mat,width=.3):
    """Original flat vector ribbons; no bevel or inverted outline on ink."""
    verts=[];faces=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<1e-6:continue
        nx,ny=-dy*width/(2*length),dx*width/(2*length);k=len(verts)
        verts.extend(xyz(x,y,z) for x,y in ((a[0]+nx,a[1]+ny),(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny)))
        faces.append((k,k+1,k+2,k+3) if z>=0 else (k+3,k+2,k+1,k))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);assign(o,mat);o['printed']=True
    return o


def arc_points(cx,cy,rx,ry,start=0,end=360,steps=48):
    return [(cx+rx*math.cos(math.radians(start+(end-start)*i/steps)),
             cy+ry*math.sin(math.radians(start+(end-start)*i/steps))) for i in range(steps+1)]


def vector_word(value,pos,height,mat,italic=0):
    """Our own small path alphabet for the identifying hardware marks."""
    oval=arc_points(.43,.5,.41,.5,0,360,20)
    glyphs={'G':[arc_points(.43,.5,.41,.5,45,315,18),[(.45,.45),(.85,.45),(.85,.1)]],
            'A':[[(0,0),(.43,1),(.86,0)],[(.2,.4),(.66,.4)]],
            'M':[[(0,0),(0,1),(.43,.35),(.86,1),(.86,0)]],
            'E':[[(.86,1),(0,1),(0,0),(.86,0)],[(0,.5),(.72,.5)]],
            'B':[[(0,0),(0,1)],[(0,1),(.55,1),(.82,.88),(.82,.67),(.55,.5),(0,.5)],[(.55,.5),(.85,.35),(.85,.14),(.55,0),(0,0)]],
            'O':[oval], 'Y':[[(0,1),(.43,.52),(.86,1)],[(.43,.52),(.43,0)]],
            'S':[[(.86,.85),(.66,1),(.2,1),(0,.82),(.08,.62),(.75,.38),(.86,.18),(.66,0),(.2,0),(0,.15)]],
            'N':[[(0,0),(0,1),(.86,0),(.86,1)]],
            'U':[[(0,1),(0,.22),(.12,.06),(.3,0),(.56,0),(.74,.06),(.86,.22),(.86,1)]],
            'D':[[(0,0),(0,1),(.46,1),(.7,.88),(.86,.65),(.86,.35),(.7,.12),(.46,0),(0,0)]]}
    total=sum(.52 if c==' ' else 1.02 for c in value)-.16
    x=pos[0]-total*height/2
    for c in value:
        if c==' ':x+=.52*height;continue
        for path in glyphs[c]:ink_path(value,[(x+(px+italic*py)*height,pos[1]+(py-.5)*height) for px,py in path],pos[2],mat,height*.115)
        x+=1.02*height


def nintendo_word(pos,width,mat,rear=False):
    """Hand-authored lowercase identity curves, rather than a squeezed font."""
    paths=[[(0,0),(0,1),(.72,0),(.72,1)], # N
           [(1,0),(1,.67)],[(1,.9),(1,.93)],
           [(1.3,0),(1.3,.65),(1.6,.68),(1.86,.5),(1.86,0)],
           [(2.25,1),(2.25,.12),(2.42,0),(2.62,.05)],[(2.0,.68),(2.58,.68)],
           arc_points(3.01,.34,.29,.34,0,325,16),[(2.73,.36),(3.3,.36)],
           [(3.58,0),(3.58,.65),(3.88,.68),(4.14,.5),(4.14,0)],
           arc_points(4.72,.34,.29,.34,0,360,18),[(5.01,0),(5.01,1)],
           arc_points(5.6,.34,.3,.34,0,360,18)]
    unit=width/5.92
    for path in paths:ink_path('Nintendo identifying wordmark',[(pos[0]+(x-2.96)*unit*(-1 if rear else 1),pos[1]+(y-.5)*unit) for x,y in path],pos[2],mat,.22*unit)


def uniform_group(before,scale):
    # matrix_world is lazy after assigning rotation/location. Read the
    # evaluated matrices, including the final object added without an operator.
    bpy.context.view_layer.update()
    transform=Matrix.Diagonal(Vector((scale,scale,scale,1)))
    for o in set(bpy.context.scene.objects)-before:o.matrix_world=transform@o.matrix_world


def authored_geometry(system,stem='model'):
    """Import our image-free, physical-scale adaptation of licensed geometry."""
    folder=({'gb':'letsdo3d-dmg','psp':'jsjetstream-psp','gbc':'wikiti-cgb','gba':'thegraphicsgeek-ags'} |
            {name:s['creator'] for name,s in (snes.SPECS|n64.SPECS|ps1.SPECS).items()})[system]
    path=ROOT/'third_party/models'/folder/(stem+'.glb')
    if system=='gba' and stem=='media':path=ROOT/'third_party/models/dave-gba/model.glb'
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    q=MODEL_SCALES[system]
    transform=Matrix.Scale(10*q,4)
    objects=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    for o in objects:
        o.data.transform(o.matrix_world);o.matrix_world=transform
        palette=o['slotters_material'];o.data.materials.clear();o.data.materials.append(M[palette])
        for polygon in o.data.polygons:polygon.material_index=0
    return objects


def authored_dmg():
    authored_geometry('gb')
    before=set(bpy.context.scene.objects)
    # Minimal identifying marks remain our own vectors. Source decal images
    # and its game screenshot are excluded from the prepared geometry.
    nintendo_word((-27,-3,13.55),19.5,M['blueink'])
    vector_word('GAME BOY',(1.5,-3.15,13.55),4.35,M['blueink'],.14)
    text('DOT MATRIX WITH STEREO SOUND',(4.8,58.8,13.73),1.55,M['white'],True)
    text('BATTERY',(-33.4,34.7,13.73),1.35,M['white'],True)
    for y,colour in ((59.0,'magenta'),(57.9,'blueink')):
        for left,right in ((-35.8,-16.2),(28.2,35.8)):
            ink_path('Bezel colour rule',[(left,y),(right,y)],13.73,M[colour],.22)
    for (x,y),label in zip(DMG['buttons'],'BA'):text(label,(x+1,y-9.4,13.55),2.6,M['blueink'],True)
    for x,y,label in ((-13.401,-49.671,'SELECT'),(1.245,-49.690,'START')):
        o=text(label,(x+1.5,y-4.8,13.55),1.9,M['blueink'],True);o.rotation_euler[1]=math.radians(-25)
    uniform_group(before,DMG_SCALE)


def authored_game_pak():
    authored_geometry('gb','media')
    before=set(bpy.context.scene.objects)
    nintendo_word((-10.5,22.9,2.91),10.5,M['darkgrey'])
    vector_word('GAME BOY',(6.6,22.9,2.91),2.35,M['darkgrey'],.085)
    uniform_group(before,DMG_SCALE)


def authored_psp():
    authored_geometry('psp')
    before=set(bpy.context.scene.objects)
    # Our minimal identity paths replace the source's modeled Sony letters
    # and image decals. Source dimensions are recorded in source.json.
    vector_word('SONY',(-64,21.3,9.62),2.35,M['white'])
    for x,y,label in ((34.3,-30.472,'SELECT'),(45.529,-30.473,'START'),
                      (-36.333,-30.717,'-'),(-24.392,-30.714,'+')):
        text(label,(x,y,10.25),1.0 if len(label)>2 else 1.7,M['white'],True)
    for x,glyph in ((16.257,'display'),(23.981,'sound')):
        y=-30.5
        points=(rounded_rect(2.6,1.6,(.2,)*4,(x,y),3)+[(x+1.3,y-.6)] if glyph=='display'
                else [(x-1,y-.8),(x-1,y+1),(x+.8,y+.7),(x+.8,y-.5)])
        ink_path('PSP '+glyph+' key glyph',points,10.25,M['white'],.16)
    x,y=-48.14,-30.489
    ink_path('PS key identifying mark',[(x-.5,y-1),(x-.5,y+1.1),(x+.8,y+.8),(x+.8,y),(x-.4,y)],10.25,M['white'],.22)
    ink_path('PS key identifying mark',[(x-1.7,y-.7),(x-.7,y-.4),(x+1.6,y-.7),(x+.8,y-1.1)],10.25,M['white'],.2)
    for rear in (False,True):
        for offset,path in ((-9,[(-3,-1.8),(-3,1.8),(3,1.8),(3,-.1),(-2.7,-.1)]),
                            (0,[(3,1.8),(-3,1.8),(-3,0),(3,0),(3,-1.8),(-3,-1.8)]),
                            (9,[(-3,-1.8),(-3,1.8),(3,1.8),(3,-.1),(-2.7,-.1)])):
            points=[((-offset-px if rear else offset+px),(-.3 if rear else -30.5)+py) for px,py in path]
            mark=ink_path(('Rear ' if rear else '')+'PSP identifying wordmark',points,-10.08 if rear else 9.64,M['chrome'] if rear else M['white'],.28)
            if rear:
                mark['hinged']=True;mark['hinge_mm']=PSP['hinge']
    # A shallow drive base and the holder move independently, as on hardware.
    box('UMD drive chamber',(0,-.5,-2.0),(70,65,1),M['black'],0)
    cylinder('UMD drive spindle',(0,-2.1,-2.6),2.8,.3,M['metal'],'front',16)
    for x in (-33.5,33.5):
        rail=box('UMD holder rail',(x,-2.8,-7.3),(1.2,46.6,.8),M['chrome'],0)
        rail['hinged']=True;rail['hinge_mm']=PSP['hinge']
    stop=box('UMD holder stop',(0,-33.6,-7.3),(58.6,1.2,.8),M['chrome'],0)
    stop['hinged']=True;stop['hinge_mm']=PSP['hinge']
    uniform_group(before,PSP_SCALE)


def umd_media():
    """Original ECMA-365 rear apertures, contained within the case envelope."""
    case=contour_shell('UMD original ECMA case',umd_outline(),2.1,4.2,
                       M['white'],UMD['edge_radius'])

    def recess(name,profile,depth):
        # Cut from the rear plane (-2.1) into the case. Keep the front closed.
        top=-2.1+depth+.02
        cut_profile(case,name,profile,top,depth+1)
        # A dark floor is inside the bore; it never protrudes out of the back.
        floor=contour_shell(name+' floor',profile,top-.01,.01,M['darkgrey'],0)
        floor['dimension_critical']=True

    location=arc_points(*UMD['location'],1.8,1.8,steps=48)[:-1]
    alignment=rounded_rect(*UMD['alignment_size'],(1.8,)*4,UMD['alignment'])
    recess('UMD location bore',location,UMD['hole_depth'])
    recess('UMD alignment bore',alignment,UMD['hole_depth'])
    recess('UMD spindle aperture',arc_points(0,0,9,9,steps=64)[:-1],2.2)
    # The head window opens to the rear-view left edge. Its 21.3 mm width
    # follows L6-L17, and y follows L16/L18 relative to plane X at -26.3.
    head=rounded_rect(34-UMD['head_inner_x'],UMD['head_top']-UMD['head_bottom'],
                      (.5,)*4,((34+UMD['head_inner_x'])/2,
                               (UMD['head_top']+UMD['head_bottom'])/2))
    recess('UMD head aperture',head,UMD['head_recess'])
    # L25-L28: a rear-side notch prevents upside-down insertion.
    w,h,depth=UMD['misinsert_size']
    detent=rounded_rect(w+1,h,(.2,)*4,(-32+(w-1)/2,UMD['misinsert_bottom']+h/2))
    recess('UMD misinsert detent',detent,depth)
    # Floors beyond the perimeter are unnecessary for open edge recesses.
    for name in ('UMD head aperture floor','UMD misinsert detent floor'):
        bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
    # Optical surface and spindle hub are behind the case's rear surface.
    cylinder('UMD optical disc',(0,0,.03),29.85,.08,M['metal'],'front',32)
    cylinder('UMD clamping plate',(0,0,-.3),6.5,.18,M['metal'],'front',32)
    # A flat label and flat vector ink add only 0.006 mm in the central zone.
    label=contour_shell('UMD blank disc print',arc_points(0,0,30,30,steps=64)[:-1],
                        2.106,.005,M['label'],0)
    label['dimension_critical']=True
    vector_word('UMD',(0,-24,2.11),2.8,M['darkgrey'],.12)


def setup():
    # A subset build must have the same datablock names as a full build.
    bpy.ops.wm.read_factory_settings(use_empty=True);M.clear()
    colours={'black':(.009,.01,.013),'blackbody':(.10,.12,.16),'darkgrey':(.28,.29,.30),
        'n64':(.24,.27,.32),'sega':(.22,.25,.30),'snesgrey':(.76,.77,.74),
        'snespanel':(.60,.63,.65),
        'usgrey':(.78,.76,.83),'nesgrey':(.85,.84,.79),'nesdark':(.27,.29,.34),
        'slotgrey':(.24,.25,.26),'portgrey':(.68,.69,.69),'buttonlight':(.68,.70,.74),
        'purple':(.59,.43,.84),'ink':(.20,.20,.23),'darkink':(.07,.08,.09),
        'white':(.82,.83,.82),'silver':(.60,.63,.65),'metal':(.51,.53,.54),
        'gold':(.73,.57,.26),'label':(.77,.75,.68),'red':(.65,.045,.035),
        'blue':(.06,.19,.65),'green':(.06,.56,.15),'yellow':(.83,.64,.07),
        'gb':(.79,.79,.71),'gbc':(.12,.63,.67),'gba':(.18,.34,.73),
        'screenbezel':(.20,.23,.29),'lcdgreen':(.45,.53,.24),'lcdblack':(.055,.105,.105),
        'magenta':(.65,.13,.35),'blueink':(.15,.20,.36),'dswhite':(.91,.91,.89),
        'dsseam':(.66,.67,.65),'dsrubber':(.77,.77,.74),
        'glass':(.105,.14,.155),'pspblack':(.19,.205,.235),'pspbutton':(.25,.27,.30),
        'picored':(.79,.10,.225),'picocyan':(.16,.68,.99),
        'dmgbody':(.76,.77,.75),'dmgshadow':(.68,.69,.67),'dmghighlight':(.79,.80,.78),
        'dmgbezel':(.46,.45,.49),'dmgbutton':(.55,.045,.25),'cgbclear':(.48,.47,.54),
        'pspplastic':(.09,.10,.115),'pspkey':(.15,.165,.18),'chrome':(.63,.65,.67),
        'glinthint':(.29,.32,.34),'mediashell':media.SHELL,'mediashade':media.SHADE,'pcb':(.10,.33,.18)}
    for name,c in colours.items():material(name,c,.34 if name in ('sega','purple','gba') else .48,
                                         .65 if name in ('gold','metal','silver') else 0)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
    scene.cycles.use_denoising=True;scene.cycles.device='CPU'
    scene.render.resolution_x=720;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
    scene.world=bpy.data.worlds.new('World');scene.world.color=(.25,.25,.25)
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
    scene.render.use_freestyle=True
    linesets=scene.view_layers[0].freestyle_settings.linesets
    if not linesets:linesets.new('Contour')
    if linesets[0].linestyle is None:linesets[0].linestyle=bpy.data.linestyles.new('Contour ink')
    linesets[0].linestyle.thickness=.7 if PRECISE else 1.4
    bpy.ops.object.camera_add(location=(0,-12*math.cos(PHI),12*math.sin(PHI)))
    cam=bpy.context.object;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=60;cam.data.sensor_width=36;cam.data.sensor_fit='HORIZONTAL';scene.camera=cam
    for name,loc,energy,size in [('Soft key',(-3.8,-4.5,7),1450,5),('Fill',(4,-2,4),650,4),('Back edge',(1,4,5),1200,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object;light.name=name;light.data.energy=energy;light.data.shape='DISK';light.data.size=size
        light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()


def render(path):
    bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    # Blender embeds wall-clock dates and timing statistics in otherwise
    # identical PNGs. Keep pixels/colour information, omit volatile metadata.
    import struct
    raw=path.read_bytes();out=raw[:8];offset=8
    while offset<len(raw):
        size=struct.unpack_from('>I',raw,offset)[0];kind=raw[offset+4:offset+8]
        if kind not in (b'tEXt',b'iTXt',b'zTXt',b'eXIf',b'tIME'):
            out+=raw[offset:offset+12+size]
        offset+=12+size
    path.write_bytes(out)


def export_gltf(objects,path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
        colors=o.data.color_attributes.get('Colour') or o.data.color_attributes.new(name='Colour',type='BYTE_COLOR',domain='CORNER')
        for poly in o.data.polygons:
            c=o.data.materials[poly.material_index].diffuse_color
            for li in poly.loop_indices:colors.data[li].color_srgb=c
    registered_ds=path.parent.name=='nds' and path.stem.startswith('model')
    if PRECISE or registered_ds:
        scene=bpy.context.scene;q=ds_lid.HOUSING_UNITS_PER_MM if registered_ds else model_scale(path.parent.name)
        scene['slotters_axes']='x right, y up, z front; hinge_mm uses these axes'
        scene['slotters_native_units_per_mm']=q
        scene['slotters_glb_to_metres']=1 if path.stem.endswith('-physical') else 1/(10*q)
    bpy.ops.export_scene.gltf(filepath=str(path),use_selection=True,export_format='GLB',export_materials='NONE',export_texcoords=False,export_vertex_color='ACTIVE',export_active_vertex_color_when_no_material=True,export_extras=PRECISE or registered_ds)
    if path.parent.name in ('gbc','gba') or (path.stem.startswith('media') and path.parent.name in MEDIA_SCALES):
        # Exact cavity booleans can enumerate equal triangles in a different
        # order. Canonical cyclic rotation/sorting preserves winding and all
        # geometry while removing that serialization-only nondeterminism.
        import struct,json
        raw=bytearray(path.read_bytes());length=struct.unpack_from('<I',raw,12)[0]
        g=json.loads(raw[20:20+length]);binary=28+length
        for mesh in g['meshes']:
            for primitive in mesh['primitives']:
                a=g['accessors'][primitive['indices']];v=g['bufferViews'][a['bufferView']]
                code={5123:'H',5125:'I'}[a['componentType']]
                offset=binary+v.get('byteOffset',0)+a.get('byteOffset',0)
                values=struct.unpack_from('<%d%s'%(a['count'],code),raw,offset)
                faces=[]
                for i in range(0,len(values),3):
                    t=values[i:i+3];faces.append(min(t,t[1:]+t[:1],t[2:]+t[:2]))
                struct.pack_into('<%d%s'%(a['count'],code),raw,offset,*(k for t in sorted(faces) for k in t))
        path.write_bytes(raw)


def export_mesh(target,stem='model'):
    import struct,json
    snes_model=target.name in snes.SPECS and stem=='model'
    full_snes=snes_model and (snes.DETAIL=='full' or snes.DETAIL=='detailed' and target.name=='snes')
    meshes=[];doors=[]
    for o in list(bpy.context.scene.objects):
        if o.type not in ('MESH','FONT'):continue
        door=o.get('hinged',False) or o.name in ('Loading door','Nintendo ENTERTAINMENT SYSTEM');printed=o.type=='FONT' or o.get('printed',False)
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.convert(target='MESH');o=bpy.context.object
        o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
        o['printed']=printed
        if PRECISE or target.name=='nds':o['hinged']=bool(door)
        (doors if door else meshes).append(o)
    all_objects=meshes+doors
    for o in all_objects:o.data.calc_loop_triangles()
    ink=sum(len(o.data.loop_triangles) for o in all_objects if o['printed'])
    solid=sum(len(o.data.loop_triangles) for o in all_objects if not o['printed'])
    protected_names={'Moulded handheld housing','Shell parting seam','LCD bezel','LCD glass',
                     'Continuous D-pad','Action button A','Action button B',
                     'SELECT button','START button','SELECT socket','START socket','Speaker slot','Speaker opening',
                     'PSP silver perimeter','PSP front housing','PSP rear housing','PSP LCD glass',
                     'Separate directional key','PSP triangle key','PSP circle key','PSP cross key','PSP square key',
                     'Textured analog nub','UMD door shell','UMD holder rail','UMD holder stop',
                     'PSP system button',
                     'Cartridge guide rail','DMG Game Pak original shell','UMD original ECMA case'}
    if PRECISE or target.name=='nds' and stem=='model':
        export_gltf(all_objects,target/(stem+'-master.glb'))
        q=ds_lid.HOUSING_UNITS_PER_MM if target.name=='nds' and stem=='model' else model_scale(target.name)
        physical=Matrix.Scale(1/(10*q),4)
        for o in all_objects:o.matrix_world=physical
        export_gltf(all_objects,target/(stem+'-physical.glb'))
        for o in all_objects:o.matrix_world=Matrix.Identity(4)
    # Source-specific per-part limits preserve the editable masters above.
    for o in all_objects:
        limit=o.get('runtime_triangle_budget')
        if snes_model and snes.DETAIL=='detailed':limit=snes.DETAILED_BUDGETS.get(o.name,limit)
        if not limit or full_snes:continue
        o.data.calc_loop_triangles();count=len(o.data.loop_triangles)
        if count<=limit:continue
        bpy.context.view_layer.objects.active=o
        if (target.name=='gba' and o.name=='SP recreation housing') or target.name in snes.SPECS|n64.SPECS|ps1.SPECS:
            # glTF splits vertices at hard-normal boundaries. Weld those
            # coincident corners before reducing the connected moulding.
            bm=bmesh.new();bm.from_mesh(o.data)
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001)
            bm.to_mesh(o.data);bm.free();o.data.calc_loop_triangles();count=len(o.data.loop_triangles)
        d=o.modifiers.new('Authored fitting budget','DECIMATE');d.ratio=limit/count
        bpy.ops.object.modifier_apply(modifier=d.name)
        if target.name in snes.SPECS|n64.SPECS|ps1.SPECS:panel_normals(sys.modules[__name__],o)
        if target.name=='gba' and o.name=='SP recreation housing':
            # Restore the dimension-critical slot planes after simplifying the
            # outer housing. Quadric collapse must not drag a flange rim inward.
            physical_cut(sys.modules[__name__],o,tuple(v*AGS_SCALE for v in (0,AGS_CAVITY_Y,24.5)),tuple(v*AGS_SCALE for v in (58.2,AGS_CAVITY_T,37)))
            physical_cut(sys.modules[__name__],o,tuple(v*AGS_SCALE for v in (0,AGS_CAVITY_Y,38.5)),tuple(v*AGS_SCALE for v in (60.7,AGS_CAVITY_T,11)))
            panel_normals(sys.modules[__name__],o)
    protected=lambda o:(PRECISE and (o.get('dimension_critical',False) or o.name.split('.')[0] in protected_names)
                        or target.name=='nds' and o.name in ('DS control deck','DS rotating lid knuckle'))
    fixed=ink+sum(len(o.data.loop_triangles) for o in all_objects if not o['printed'] and protected(o))
    reducible=sum(len(o.data.loop_triangles) for o in all_objects if not o['printed'] and not protected(o))
    ratio=min(1,max(.10,((12800-fixed)/max(1,reducible)) if PRECISE else (14000-ink)/max(1,solid)))
    if full_snes:ratio=1
    for o in all_objects:
        if o['printed'] or protected(o) or len(o.data.loop_triangles)<64 or ratio==1:continue
        bpy.context.view_layer.objects.active=o
        original=o.data.copy()
        low=Vector(tuple(min(v.co[i] for v in original.vertices) for i in range(3)))
        high=Vector(tuple(max(v.co[i] for v in original.vertices) for i in range(3)))
        d=o.modifiers.new('Native triangle budget','DECIMATE');d.ratio=ratio
        bpy.ops.object.modifier_apply(modifier=d.name)
        # Quadric collapse can extrapolate thin, bevelled door/lip vertices far
        # outside the housing. Keep the complete moulding if that happens.
        if any(not math.isfinite(v.co[i]) or v.co[i]<low[i]-.005 or v.co[i]>high[i]+.005
               for v in o.data.vertices for i in range(3)):
            damaged=o.data;o.data=original;bpy.data.meshes.remove(damaged)
        else:bpy.data.meshes.remove(original)
    if target.name=='nds' and stem=='model':
        # Collapse interpolates custom normals along the newly thinned lid.
        # Rebuild unit moulding normals on the final triangles rather than
        # exporting short solid normals or relying on shader normalization.
        for o in all_objects:panel_normals(sys.modules[__name__],o)
    data=[];door_first=0;moving_parts={}
    for index,group in enumerate((meshes,doors)):
        if index:door_first=len(data)//9
        for o in group:
            first=len(data)//9
            mesh=o.data;mesh.calc_loop_triangles()
            for tri in mesh.loop_triangles:
                if tri.normal.length_squared<.5:continue
                c=mesh.materials[tri.material_index].diffuse_color[:3]
                for li in tri.loops:
                    p=mesh.vertices[mesh.loops[li].vertex_index].co;n=mesh.corner_normals[li].vector
                    if n.length_squared<.5:n=tri.normal
                    if target.name=='nds' and stem=='model':n=n.normalized()
                    # A short normal marks printed ink for the shader: keep its
                    # orientation for lighting, without a thick black hull.
                    k=.25 if o['printed'] or o.get('outline') is False else 1
                    data.extend((p.x*100,p.z*100,-p.y*100,n.x*k,n.z*k,-n.y*k,*c))
            if index:moving_parts[o.name]=dict(first=first,count=len(data)//9-first)
    if target.name in ('gbc','gba') or (stem.startswith('media') and target.name in MEDIA_SCALES):
        groups=[]
        for first,last in ((0,door_first*9),(door_first*9,len(data))):
            faces=[]
            for i in range(first,last,27):
                vertices=[tuple(data[j:j+9]) for j in range(i,i+27,9)]
                faces.append(min(vertices[k:]+vertices[:k] for k in range(3)))
            groups.extend(value for face in sorted(faces) for vertex in face for value in vertex)
        data=groups
    unique=[];indices=[];lookup={}
    for offset in range(0,len(data),9):
        vertex=tuple(data[offset:offset+9]);packed=struct.pack('<9f',*vertex)
        if packed not in lookup:lookup[packed]=len(unique);unique.append(packed)
        indices.append(lookup[packed])
    assert len(unique)<=65535
    triangle_limit=200000 if snes_model and snes.DETAIL!='balanced' else 15000
    if snes_model and snes.DETAIL!='balanced':assert len(indices)<=600000, 'Native index-count limit exceeded'
    elif PRECISE:assert len(indices)//3<triangle_limit, f'Exemplar exceeds selected triangle budget: {len(indices)//3}'
    payload=struct.pack('<8sIII',b'SCTOON2\0',len(unique),len(indices),door_first)
    payload+=b''.join(unique)+struct.pack('<%dH'%len(indices),*indices)
    path=target/(stem+'.mesh');temporary=path.with_suffix('.mesh.tmp')
    temporary.write_bytes(payload);temporary.replace(path)
    export_gltf(all_objects,target/(stem+'.glb'))
    origins=sorted({(o['source_creator'],o['source_licence'],o['source_url'])
                    for o in all_objects if o.get('source_creator')})
    info=dict(vertices=len(unique),indices=len(indices),triangles=len(data)//27,door_first=door_first,
              licence=' + '.join(sorted({'MIT'}|{licence for _,licence,_ in origins})),
              source='Authored recreation adapted by tools/consolebuild/models.py' if origins else
                     'Original procedural geometry, tools/consolebuild/models.py')
    if origins:info['creators']=[dict(author=a,licence=l,url=u) for a,l,u in origins]
    if target.name=='n64':info['moving_parts']=moving_parts
    if target.name in snes.SPECS and stem=='model':info.update(detail=snes.DETAIL,triangle_limit=triangle_limit)
    (target/('mesh-info.json' if stem=='model' else stem+'-info.json')).write_text(json.dumps(info,indent=2)+'\n')
    return meshes+doors


def main():
    global PRECISE
    selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(SPECS)
    if set(selected)&{'gb','psp'}:native_header()
    if 'psx' in selected:ps1.native_header()
    if set(selected)&{'gba','nds'}:lids.native_header()
    if set(selected)&set(media.CONSOLE_VARIANTS):
        # Multithreaded EXACT booleans return slightly different cavity
        # geometry between runs. One thread makes every output repeatable.
        argv=sys.argv[:sys.argv.index('--')] if '--' in sys.argv else sys.argv
        if not any(a in ('-t','--threads') and argv[i+1]=='1' for i,a in enumerate(argv[:-1])):
            raise SystemExit('Physical media consoles need deterministic booleans: run blender -t 1')
        media.native_header()
    for name in selected:
        if (ROOT/'theme/art-book-slot/_slot/consoles'/name/'model.texture').exists():
            print('CONSOLE PRESERVED',name,'textured source: rebuild with tools/consolebuild/textured.sh',flush=True)
            continue
        PRECISE=name in MODEL_SCALES
        setup();s=SPECS[name]
        if name=='gb':authored_dmg()
        elif name=='gbc':cgb(sys.modules[__name__])
        elif name=='gba':ags(sys.modules[__name__])
        elif name in snes.SPECS:snes.console(sys.modules[__name__],name)
        elif name in n64.SPECS:n64.console(sys.modules[__name__],name)
        elif name=='psx':ps1.console(sys.modules[__name__])
        elif s['kind']==1:handheld(name,s)
        elif s['kind']==3:advance_sp(s)
        elif s['kind']==4:
            ds_lite(s);ds_lid.prepare(sys.modules[__name__])
        elif s['kind']==5:authored_psp()
        else:home(name,s)
        if name=='nes':
            box('Loading door',(-45,1,s['ry']-20),(278,3,37),M['nesgrey'],2)
            text('Nintendo ENTERTAINMENT SYSTEM',(-45,2.8,s['ry']-19),10,M['red'],width=235)
        target=ROOT/'theme/art-book-slot/_slot/consoles'/name;target.mkdir(parents=True,exist_ok=True)
        if s['yscale']!=1:
            stretch=Matrix.Diagonal(Vector((1,1,s['yscale'],1)))
            for o in bpy.context.scene.objects:
                if o.type in ('MESH','FONT'):o.matrix_world=stretch@o.matrix_world
        objects=export_mesh(target)
        if name=='n64':n64.native_header()
        ink=bpy.data.collections.new('Printed details');bpy.context.scene.collection.children.link(ink)
        for o in objects:
            if o.get('printed'):ink.objects.link(o)
        lines=bpy.context.view_layer.freestyle_settings.linesets[0]
        lines.select_by_collection=True;lines.collection=ink;lines.collection_negation='EXCLUSIVE'
        if name in ('gbc','gba'):lines.select_crease=False
        pose=Matrix.Rotation(-PHI,4,'X') if s['kind'] in (1,5) else Matrix.Identity(4)
        pose=pose@Matrix.Rotation(math.radians(-12 if s['kind']==1 else -14 if s['kind']==5 else -8),4,'Z')
        for o in objects:
            o.matrix_world=pose@lids.closed_transform(name,model_scale(name),SCALE) if name in ('gba','nds') and o.get('hinged') else pose
        render(target/'body.png')
        if name in ('gb','gbc','gba','psp') and not (target/'media.texture').exists():
            setup()
            if name=='gb':authored_game_pak()
            elif name=='gbc':cgb_media(sys.modules[__name__])
            elif name=='gba':ags_media(sys.modules[__name__])
            else:
                before=set(bpy.context.scene.objects);umd_media();uniform_group(before,PSP_SCALE)
            export_mesh(target,'media')
        for variant in media.CONSOLE_VARIANTS.get(name,()):
            if (target/(media.MEDIA[variant]['part']+'.texture')).exists():continue
            # Physical media masters/derivatives share the console's scale.
            PRECISE=True;setup();media.build(sys.modules[__name__],variant)
            export_mesh(target,media.MEDIA[variant]['part'])
        print('CONSOLE COMPLETE',name,flush=True)


if __name__=='__main__':main()
