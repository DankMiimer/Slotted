"""CGB-001 / AGS-001 physical integration and original missing details (MIT)."""
import math
from mathutils import Matrix,Vector

CGB_SCALE=168/78
AGS_SCALE=224/82
AGS_CAVITY_T=8.4
AGS_CAVITY_Y=-25.975
SCALES={'gbc':CGB_SCALE,'gba':AGS_SCALE}


def physical_cut(m,obj,pos,size):
    tool=m.box('Physical cavity cutter',pos,size,m.M['black'],0)
    m.bpy.context.view_layer.objects.active=tool
    for mod in list(tool.modifiers):m.bpy.ops.object.modifier_apply(modifier=mod.name)
    m.bpy.context.view_layer.objects.active=obj
    for mod in list(obj.modifiers):m.bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('Physical cavity','BOOLEAN');mod.operation='DIFFERENCE'
    mod.object=tool;mod.solver='EXACT';mod.use_self=True;mod.use_hole_tolerant=True
    m.bpy.ops.object.modifier_apply(modifier=mod.name)
    m.bpy.data.objects.remove(tool,do_unlink=True)


def panel_normals(m,obj):
    m.bpy.context.view_layer.objects.active=obj
    obj.data.normals_split_custom_set([(0,0,0)]*len(obj.data.loops))
    obj.data.set_sharp_from_angle(angle=math.radians(30))
    for p in obj.data.polygons:p.use_smooth=True
    n=obj.modifiers.new('Stable moulded panel normals','WEIGHTED_NORMAL')
    n.mode='FACE_AREA';n.keep_sharp=True;n.weight=100
    m.bpy.ops.object.modifier_apply(modifier=n.name)
    if obj.name=='SP recreation housing':
        obj.data.update();normals=[tuple(n.vector) for n in obj.data.corner_normals]
        for p in obj.data.polygons:
            if abs(p.normal.z)>.93:
                for li in p.loop_indices:normals[li]=(0,0,1 if p.normal.z>0 else -1)
        obj.data.normals_split_custom_set(normals)


def cgb(m):
    m.authored_geometry('gbc');before=set(m.bpy.context.scene.objects)
    m.vector_word('GAME BOY',(-9.5,7.4,13.35),3.1,m.M['white'],.1)
    for i,(letter,colour) in enumerate(zip('COLOR',('red','magenta','green','yellow','blue'))):
        m.text(letter,(7.5+i*2.4,7.4,13.35),3,m.M[colour],True)
    m.nintendo_word((0,-4,13.2),18,m.M['blueink'])
    m.cylinder('CGB power LED',(-31.3,43,13.6),.8,.1,m.M['red'],'front',20)
    for x,y,letter in ((14,-30,'B'),(28,-25,'A')):m.text(letter,(x,y,12.6),2.5,m.M['blueink'],True)
    for x,word in ((-5.5,'SELECT'),(5.5,'START')):m.text(word,(x,-49.8,13.2),1.6,m.M['blueink'],True)
    # Original blank identifying plate: no downloaded serial or decal paths.
    t=m.text('CGB-001',(0,-11,-8.8),2.3,m.M['darkgrey'],True);t.rotation_euler[2]=math.pi
    m.uniform_group(before,CGB_SCALE)


def ags(m):
    m.authored_geometry('gba');before=set(m.bpy.context.scene.objects)
    # Source's perforations were normal-map details. These original dark wells
    # are actual geometry, on the upper control deck, below the active controls.
    for x in (-4.2,-2.1,0,2.1,4.2):
        for z in (7,9.1,11.2):m.cylinder('SP speaker perforation',(x,-17.75,z),.48,.08,m.M['black'],vertices=12)
    for x,word in ((-7.1,'SELECT'),(7.1,'START')):m.text(word,(x,-17.75,36.1),1.3,m.M['white'])
    for x,z,letter in ((13.56,-4.47,'B'),(25.94,-9.02,'A')):m.text(letter,(x,-18.05,z),2.3,m.M['ink'])
    m.box('SP connector floor',(0,-26.4,6.55),(54,5.2,.45),m.M['black'],0)
    floor=m.box('SP bay floor',(0,AGS_CAVITY_Y-AGS_CAVITY_T/2-.15,24.15),(58.2,.3,36.3),m.M['gba'],0)
    floor['dimension_critical']=True;floor['outline']=False
    # Ring in the source's sloping lid plane. Four quads leave a real aperture.
    centre=Vector((0,30.494,-47.507));up=Vector((0,.96385,-.26646));normal=Vector((0,.26646,.96385))
    vertices=[]
    for w,h in ((71,57),(61.2,40.8)):
        for x,y in ((-1,-1),(1,-1),(1,1),(-1,1)):
            p=centre+Vector((x*w/2,0,0))+up*(y*h/2)+normal*.18
            vertices.append(m.xyz(*p))
    mesh=m.bpy.data.meshes.new('SP lens ring');mesh.from_pydata(vertices,[],[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)]);mesh.update()
    ring=m.bpy.data.objects.new('SP dark lens surround',mesh);m.bpy.context.collection.objects.link(ring);m.assign(ring,m.M['screenbezel']);ring['printed']=True
    pos=centre-up*25+normal*.24
    word=m.text('GAME BOY ADVANCE SP',tuple(pos),1.9,m.M['white'],True,width=44)
    word.rotation_euler[0]=math.pi/2-math.asin(.26646)
    ring['hinged']=True;word['hinged']=True
    # Opaque black lens surround with a physical 61.2 x 40.8 mm aperture.
    # The source active area is retained; a small highlight has no image input.
    for name in ('SP ChargingPort','SP LinkPort'):
        o=m.bpy.data.objects.get(name)
        if o:o.name='SP EXT.2 connector' if 'Charging' in name else 'SP EXT.1 connector'
    m.uniform_group(before,AGS_SCALE)


def cgb_media(m):
    # Dedicated CGB shell: rounded crown, continuous full-width top (no DMG
    # switch notch), recessed label and rear connector opening. Derived from
    # the blanked Evan-Amos reference; mechanical interior remains an estimate.
    before=set(m.bpy.context.scene.objects)
    p=m.rounded_rect(57,65.5,(4,4,.65,.65),steps=12)
    shell=m.contour_shell('Dedicated CGB Game Pak',p,3.9,7.8,m.M['cgbclear'],.20,3)
    m.cut_profile(shell,'CGB label recess',m.rounded_rect(42.2,37.6,(1.3,)*4,(0,-5),8),4.1,.45)
    m.cut_profile(shell,'CGB rear connector opening',[(-25.5,-33),(25.5,-33),(25.5,-27),(-25.5,-27)],-1.2,3)
    m.box('CGB connector board',(0,-29.3,-1),(50.7,6.5,1.1),m.M['green'],0)
    for i in range(32):m.box('CGB connector finger',(-24+i*48/31,-30.8,-1.61),(.85,3.1,.05),m.M['gold'],0)
    # The raised oval crown is the conspicuous dedicated-case distinction.
    m.contour_shell('CGB raised crown',m.rounded_rect(43.5,11,(5.5,)*4,(0,24),12),4.01,.3,m.M['cgbclear'],.08,2)
    m.vector_word('GAME BOY',(0,24,4.02),3.2,m.M['darkgrey'],.08)
    m.box('Blank CGB recessed label',(0,-5,3.68),(41.8,37.2,.05),m.M['label'],.5)
    m.uniform_group(before,CGB_SCALE)


def ags_media(m):
    m.authored_geometry('gba','media');q=AGS_SCALE
    before=set(m.bpy.context.scene.objects)
    m.box('Blank GBA recessed label',(0,-2,3.49),(44.1,22.8,.03),m.M['label'],.3)
    m.box('GBA connector board',(0,-13,-.85),(50.8,8,1),m.M['pcb'],0)
    for i in range(32):
        for z in (-.33,-1.37):m.box('GBA connector finger',(-24+i*48/31,-14.3,z),(.85,4.7,.035),m.M['gold'],0)
    m.nintendo_word((0,8.6,-3.68),16,m.M['darkgrey'],rear=True)
    for value,y,size in (('MODEL NO. AGB-002',4.8,1.05),('PAT. PEND. MADE IN JAPAN',2.8,.9)):
        o=m.text(value,(0,y,-3.69),size,m.M['darkgrey'],True,width=24)
        o.rotation_euler[2]=math.pi
    m.uniform_group(before,q)
