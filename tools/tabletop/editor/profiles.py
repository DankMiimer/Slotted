"""Pure console-profile validation/serialization, safe for packaging without a server."""
import math
from tools.tabletop.editor.settings import TVS,validate_extras,native_extras

SYSTEMS=('snes','n64','nes','md','psx','gb','gbc','gba','nds','psp','pico8')
NAMES=['table','tv','console','status']+['cart'+str(i) for i in range(12)]

def vector(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 for v in value):
        raise ValueError('Use three finite values within +/-10000')
    return list(map(float,value))

def validate(value,systems=SYSTEMS):
    if value.get('version')!=1 or value.get('system') not in systems or value.get('tv') not in TVS:
        raise ValueError('Unsupported scene profile')
    viewport=value['viewport']
    if (viewport.get('width'),viewport.get('height')) not in ((720,480),(720,540)):raise ValueError('Choose 3:2 or 4:3')
    camera=value['camera'];eye,target=vector(camera['position']),vector(camera['target']);fov=camera['fov']
    if type(fov) not in (int,float) or not math.isfinite(fov) or not 5<=fov<=110 or sum((a-b)**2 for a,b in zip(eye,target))<100:
        raise ValueError('Invalid camera FOV or target distance')
    names=NAMES if len(value['objects'])==len(NAMES) else NAMES[:12]
    if set(value['objects'])!=set(names):raise ValueError('Scene must contain table, TV, console, status and eight or twelve cartridges')
    nodes={name:dict(position=vector(value['objects'][name]['position']),rotation=vector(value['objects'][name]['rotation'])) for name in names}
    return dict(version=1,system=value['system'],tv=value['tv'],viewport=dict(viewport),
                camera=dict(position=eye,target=target,fov=float(fov)),objects=nodes,**validate_extras(value,vector))

def native_text(profile,systems=SYSTEMS):
    p=validate(profile,systems)
    def nums(values):return ' '.join(format(v,'.9g') for v in values)
    lines=['SLOTLAYOUT1','viewport '+nums([p['viewport']['width'],p['viewport']['height']]),
           'camera '+nums(p['camera']['position']+p['camera']['target']+[p['camera']['fov']])]
    lines.extend(name+' '+nums(node['position']+node['rotation']) for name,node in p['objects'].items())
    lines.extend(native_extras(p))
    return '\n'.join(lines)+'\n'
