"""Physical NUS-001 anchors, source bay correction and integration (MIT)."""
import math

# W/H/D mm. The housing envelope is corrected before one uniform scene scale.
SPECS = {
    'n64': dict(size=(260,73,190), scale=1.5, origin=282, slot=-61.7,
                entry=10.87158, opening=(118.5,27.9), seat_depth=27,
                creator='josephrohm-n64',media=(116,76.6,18.5)),
}
# Joseph Rohm's slot is 97.8 mm wide at true scale (his own cart is 87 mm), but
# a NUS-006 Game Pak is 116 mm. Widen only the cartridge bay, in source units
# about the source's centre line: |x| <= inner scales by `factor`, the flat
# shoulders out to `outer` take up the difference, and the weight ramps to zero
# in front of the bay (z) and below the rear connectors (y). Factor makes the
# 2.605-unit flap opening 120.5 mm at the 260/13.846 mm-per-unit envelope, so
# the 118.5-mm slot keeps a 1-mm floor margin inside the bay walls.
BAY = dict(inner=3.3, outer=5.6, factor=120.5/2/(2.605*260/13.846),
           z_full=-1.3, z_none=-0.6, y_none=2.45, y_full=2.7)
COLORS = {'n64upper':(.25,.255,.27), 'n64lower':(.225,.23,.245), 'n64grille':(.12,.125,.135),
          'n64button':(.27,.275,.29), 'n64port':(.60,.61,.62), 'n64socket':(.10,.10,.11),
          'n64foot':(.07,.07,.08)}
ENCLOSURE_PALETTES={'n64':('n64upper','n64lower')}
FLAPS=('N64 rear dust flap','N64 front dust flap')
FLAP_CLEARANCE=.25  # concealed running clearance, fit assumption in mm

def smooth(t):
    t=min(1,max(0,t));return t*t*(3-2*t)

def bay_warp(x,y,z):
    """Source-unit x after the bay widening; continuous, monotonic in x."""
    b=BAY;w=smooth((b['z_none']-z)/(b['z_none']-b['z_full']))*smooth((y-b['y_none'])/(b['y_full']-b['y_none']))
    a=abs(x);k=b['factor']
    if a<=b['inner']:g=a*k
    elif a<b['outer']:g=b['inner']*k+(a-b['inner'])*(b['outer']-b['inner']*k)/(b['outer']-b['inner'])
    else:g=a
    return x+w*(math.copysign(g,x)-x)

def palette(m):
    for name,rgb in COLORS.items():m.material(name,rgb)

def flap_angle(profile,hinge,side,bottom,half_thickness):
    """Minimum spring-door angle keeping the cartridge's lower edge clear.

    Profile and hinge are y/z in mm. Clip the rotated section to the cartridge
    side plane and check its highest remaining point, including edge crossings.
    This follows contact during feed/reverse, without a timestamp-driven flap.
    """
    def clear(angle):
        c,s=math.cos(angle),math.sin(angle);p=[]
        for y,z in profile:
            dy,dz=y-hinge[0],z-hinge[1]
            p.append((hinge[0]+dy*c-dz*s,side*(hinge[1]+dy*s+dz*c-SPECS['n64']['slot'])))
        boundary=half_thickness+FLAP_CLEARANCE
        inside=[y for y,z in p if z<=boundary]
        for a in p:
            for b in p:
                if (a[1]<boundary<b[1]) or (b[1]<boundary<a[1]):
                    inside.append(a[0]+(b[0]-a[0])*(boundary-a[1])/(b[1]-a[1]))
        return not inside or max(inside)<=bottom-FLAP_CLEARANCE
    sign=-side
    if clear(0):return 0
    lo,hi=0,math.radians(89)
    for _ in range(18):
        mid=(lo+hi)/2
        if clear(sign*mid):hi=mid
        else:lo=mid
    return sign*hi

def native_header():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    source=json.loads((root/'third_party/models/josephrohm-n64/source.json').read_text())
    mesh=json.loads((root/'theme/art-book-slot/_slot/consoles/n64/mesh-info.json').read_text())
    q=SPECS['n64']['scale'];lines=['/* Generated N64 door sections/ranges; MIT processing, CC BY geometry. */']
    for index,name in enumerate(FLAPS):
        f=source['flaps'][name];part=mesh['moving_parts'][name]
        lines.append('static const double n64_flap_profile_%d[][2]={'%index+
            ','.join('{'+','.join(f'{v*q:.9f}' for v in p)+'}' for p in f['profile_yz_mm'])+'};')
        lines.append('static const double n64_flap_hinge_%d[2]={'%index+
            ','.join(f'{v*q:.9f}' for v in f['hinge_yz_mm'])+'};')
        lines.append('static const unsigned n64_flap_range_%d[2]={%d,%d};'%(index,part['first'],part['count']))
    lines.append(f'static const double n64_flap_clearance={FLAP_CLEARANCE*q:.9f};')
    lines.append(f'static const double n64_cart_half_thickness={SPECS["n64"]["media"][2]*q/2:.9f};')
    lines.append(f'static const double n64_cart_slot={SPECS["n64"]["slot"]*q:.9f};')
    (root/'tools/slotlaunch/n64-data.h').write_text('\n'.join(lines)+'\n',newline='\n')

def apply_specs(table):
    for name,s in SPECS.items():
        w,h,d=s['size'];q=s['scale']
        table[name].update(rx=w*q/2,ry=d*q/2,depth=h*q/2,slot=s['slot']*q,
            mouth=s['opening'][0]*q,cart=s['media'][0]*q,sink=s['seat_depth']*q,
            yscale=1,entry=s['entry']*q,origin=s['origin'])

def console(m,name):
    from mathutils import Vector
    palette(m);m.authored_geometry(name)
    s=SPECS[name];q=s['scale'];before=set(m.bpy.context.scene.objects)
    w,d=s['opening'];floor=s['entry']-s['seat_depth']-1.5
    o=m.box('N64 connector floor',(0,floor,s['slot']),(w-.6,.5,d-.6),m.M['black'],0)
    o['dimension_critical']=True;o['outline']=False
    top=s['entry']-.4;bottom=floor-.25
    for sign in (-1,1):
        for pos,size in (((sign*(w/2+.125),(top+bottom)/2,s['slot']),(.25,top-bottom,d)),
                         ((0,(top+bottom-1.8)/2,s['slot']+sign*(d/2+1.2)),(w,top-bottom-1.8,.25))):
            o=m.box('N64 inner slot lining',pos,size,m.M['black'],0)
            o['dimension_critical']=True;o['outline']=False
    # Untextured original identifier: a black badge with white lettering in
    # the source's 0.7-mm front recess between ports 2 and 3 (about 0-28 mm up).
    m.bpy.context.view_layer.update()
    found,p,n,*_=m.bpy.context.scene.ray_cast(m.bpy.context.evaluated_depsgraph_get(),
        Vector((0,-3*q,14*q*.01)),Vector((0,1,0)))
    if not found or n.y>-.98:raise RuntimeError('N64 front badge recess not found')
    plate=m.box('N64 front badge',(0,0,0),(44,22,.8),m.M['black'],1.5)
    plate.location=Vector((0,p.y/q,p.z/q))+n*.004
    plate.rotation_euler=(-n).to_track_quat('Y','Z').to_euler();plate['outline']=False
    t=m.text('NINTENDO 64',(0,0,0),4.2,m.M['white'],width=38)
    t.location=Vector((0,p.y/q,p.z/q))+n*.0085;t.rotation_euler=n.to_track_quat('Z','Y').to_euler()
    m.uniform_group(before,q)
