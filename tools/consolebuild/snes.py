"""Physical SNSP/SHVC-001 and SNS-001 anchors and integration (MIT)."""
import math,os

# Profiles are measured on the handheld, not selected by a fixed triangle cap.
# The user's SNES target was relaxed from 60 to about 50 fps during this slice.
DETAIL=os.environ.get('SLOT_SNES_DETAIL','detailed')
if DETAIL not in ('balanced','detailed','full'):raise ValueError('SLOT_SNES_DETAIL must be balanced, detailed or full')
DETAILED_BUDGETS={'US lower enclosure':6500,'US controller sockets':2500,
                  'US rear connectors':800,'US power slider':600,'US reset button':600}

# W/H/D mm. Housing envelopes are corrected before one uniform scene scale.
SPECS = {
    'snes': dict(size=(200,72,242), scale=1.6, origin=280, slot=-22.7315683,
                 entry=33.67, opening=(138.4,22), seat_depth=30,
                 creator='quick-loop-snes',media=(130,86,20)),
    'snes-us': dict(size=(203.2,68,254), scale=1.55, origin=272, slot=-18.132,
                    entry=34, opening=(139,22.5), seat_depth=32,
                    creator='ibbqcats-snes',media=(136,88,20)),
}
# SNS-001 POWER and RESET share one purple with lavender legends; the EJECT
# lever and the moulded bay lettering are darker grey than the housing
# (Evan-Amos console photographs).
COLORS = {'sneslower':(.61,.62,.60), 'uslower':(.65,.64,.69),
          'uspower':(.45,.34,.65), 'usreset':(.45,.34,.65),
          'useject':(.55,.54,.59), 'uslegend':(.76,.70,.90),
          'snesgrey':(.76,.77,.74),'snespanel':(.60,.63,.65),'usgrey':(.78,.76,.83)}
ENCLOSURE_PALETTES={'snes':('snesgrey','snespanel','sneslower'),'snes-us':('usgrey','uslower')}

def palette(m):
    for name,rgb in COLORS.items():m.material(name,rgb)

def apply_specs(table):
    for name,s in SPECS.items():
        w,h,d=s['size'];q=s['scale']
        table[name].update(rx=w*q/2,ry=d*q/2,depth=h*q/2,slot=s['slot']*q,
            mouth=s['opening'][0]*q,cart=s['media'][0]*q,sink=s['seat_depth']*q,
            yscale=1,entry=s['entry']*q,origin=s['origin'])

def console(m,name):
    from mathutils import Matrix,Vector
    palette(m);m.authored_geometry(name)
    s=SPECS[name];q=s['scale'];before=set(m.bpy.context.scene.objects)
    w,d=s['opening'];floor=s['entry']-s['seat_depth']-1.5
    o=m.box('SNES connector floor',(0,floor,s['slot']),(w-.6,.5,d-.6),m.M['black'],0)
    o['dimension_critical']=True;o['outline']=False
    top=s['entry']-.4;bottom=floor-.25
    for sign in (-1,1):
        for pos,size in (((sign*(w/2+.125),(top+bottom)/2,s['slot']),(.25,top-bottom,d)),
                         ((0,(top+bottom)/2,s['slot']+sign*(d/2+.125)),(w,top-bottom,.25))):
            o=m.box('SNES inner slot lining',pos,size,m.M['black'],0)
            o['dimension_critical']=True;o['outline']=False
    def hit(x,z):
        m.bpy.context.view_layer.update()
        found,p,n,*_=m.bpy.context.scene.ray_cast(m.bpy.context.evaluated_depsgraph_get(),
                    Vector((x*q*.01,-z*q*.01,20)),Vector((0,0,-1)))
        return (p,n) if found else (None,None)
    def surface(x,z):
        p,_=hit(x,z)
        return p.z*100/q+.12 if p else s['entry']
    # Untextured original identifiers; source decals/engraved lettering removed.
    us=name=='snes-us'
    if us:
        # Legends sit on the parts they label, as printed on SNS-001: centred
        # on each switch, at the front of the lever, and on the left of the
        # sloped cartridge-bay front, following that slope.
        for x,word in ((-43.7,'POWER'),(43.7,'RESET')):
            m.text(word,(x,surface(x,50.4),50.4),2.8,m.M['uslegend'])
        m.text('EJECT',(0,surface(0,91.7),91.7),2.7,m.M['white'])
        p,n=hit(-40,16)
        t=m.text('SUPER NINTENDO',(-40,0,16),4.2,m.M['useject'],width=48)
        t.location=Vector((-.40,-.16,p.z/q))+n*.0012
        t.rotation_euler=n.to_track_quat('Z','Y').to_euler()
    else:
        for x,word in ((-55,'POWER'),(55,'RESET')):
            m.text(word,(x,surface(x,38),38),2.8,m.M['ink'])
        m.text('EJECT',(0,surface(0,46),46),2.7,m.M['ink'])
        m.text('SUPER NINTENDO',(0,surface(0,94),94),3.4,m.M['ink'],width=57)
    if not us:
        for x,z,c in ((75,-47,'red'),(80,-42,'blue'),(70,-42,'green'),(75,-37,'yellow')):
            m.cylinder('Four-colour identifying mark',(x,surface(x,z),z),2.1,.08,m.M[c],vertices=16)
    m.uniform_group(before,q)
