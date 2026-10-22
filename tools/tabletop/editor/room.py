"""Durable room/home authoring, separate from existing console profiles."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import secrets
import time

TABLES=('table','wooden-table','tv-stand')
TVS=('panasonic','pvm','oldtv')
MODELS=('snes','snes-us','n64','nes','md','md-jp','psx','gb','gbc','gba','nds','psp','pico8')
# Optional room surfaces: a plain colour, or a texture (surfaces/NAME.png) every `tile` mm
# multiplied by `color`. A room with any surface is written as SLOTWORLD2 (frontend 22 Oct+).
SURFACES=('floor','wall','ceiling')
TEXTURE_NAME=re.compile(r'[a-z0-9][a-z0-9-]{0,47}')

def surface(value):
    if not isinstance(value,dict) or set(value)-{'color','tile','texture'} or not {'color','tile'}<=set(value):raise ValueError('Invalid room surface fields')
    texture=value.get('texture')
    if texture is not None and (not isinstance(texture,str) or not TEXTURE_NAME.fullmatch(texture)):raise ValueError('Invalid surface texture name')
    out=dict(color=vector(value['color'],0,1),tile=number(value['tile'],100,20000))
    if texture:out['texture']=texture
    return out

def textures(profile):
    """Texture names a validated room profile uses."""
    return sorted({s['texture'] for s in profile.get('surfaces',{}).values() if s.get('texture')})

def texture_path(root,name):
    """A surface texture: the user's own (scene-layouts/surfaces) before the built-in library
    (build/tabletop/assets/surfaces, from tools/tabletop/make_surfaces.py)."""
    if not TEXTURE_NAME.fullmatch(name):raise ValueError('Invalid surface texture name')
    for folder in (Path(root)/'scene-layouts/surfaces',Path(root)/'build/tabletop/assets/surfaces'):
        if (folder/(name+'.png')).is_file():return folder/(name+'.png')
    raise ValueError('Missing surface texture: '+name)

def number(value,low=-10000,high=10000):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid finite room number')
    return float(value)

def vector(value,low=-10000,high=10000):
    if not isinstance(value,list) or len(value)!=3:raise ValueError('Expected three coordinates')
    return [number(x,low,high) for x in value]

def placement(value):
    if set(value)!={'position','rotation'}:raise ValueError('Invalid placement fields')
    return dict(position=vector(value['position']),rotation=vector(value['rotation']))

def camera(value):
    if set(value)!={'position','target','fov'}:raise ValueError('Invalid camera fields')
    p,t=vector(value['position']),vector(value['target'])
    if sum((a-b)**2 for a,b in zip(p,t))<100:raise ValueError('Camera must be at least 10 mm from its target')
    return dict(position=p,target=t,fov=number(value['fov'],5,110))

def validate(value):
    if type(value.get('version')) is not int or value['version']!=1 or value.get('kind') not in ('room','home'):raise ValueError('Unsupported room/home profile')
    if value['kind']=='room':
        if set(value)-{'surfaces'}!={'version','kind','floor','bounds','tables','paths'}:raise ValueError('Invalid room fields')
        surfaces=value.get('surfaces') or {}
        if not isinstance(surfaces,dict) or not set(surfaces)<=set(SURFACES):raise ValueError('Invalid room surfaces')
        b=value['bounds']
        if set(b)!={'left','right','back','front','height'}:raise ValueError('Invalid room bounds')
        b={k:number(v,-30000,30000) for k,v in b.items()}
        if b['right']-b['left']<2000 or b['front']-b['back']<2000 or not 1500<=b['height']<=10000:raise ValueError('Room is too small')
        if not isinstance(value['tables'],dict) or not value['tables'] or not set(value['tables'])<=set(TABLES):raise ValueError('Invalid room tables')
        tables={key:placement(at) for key,at in value['tables'].items()}
        for at in tables.values():
            x,_,z=at['position'];rx,_,rz=at['rotation']
            if not b['left']<x<b['right'] or not b['back']<z<b['front'] or rx!=0 or rz!=0:raise ValueError('Tables must be inside the room and upright')
        paths=[];pairs=set()
        if not isinstance(value['paths'],list) or len(value['paths'])>6:raise ValueError('Too many travel paths')
        for v in value['paths']:
            if set(v)!={'from','to','seconds','first','second'}:raise ValueError('Invalid path fields')
            pair=(v['from'],v['to'])
            if pair[0] not in tables or pair[1] not in tables or pair[0]==pair[1] or pair in pairs:raise ValueError('Invalid or duplicate path')
            pairs.add(pair);paths.append(dict(zip(('from','to'),pair),seconds=number(v['seconds'],.2,8),first=vector(v['first']),second=vector(v['second'])))
        out=dict(version=1,kind='room',floor=number(value['floor'],-30000,30000),bounds=b,tables=tables,paths=paths)
        if surfaces:out['surfaces']={key:surface(surfaces[key]) for key in SURFACES if key in surfaces}
        return out
    if set(value)-{'version','kind','tv','viewport','camera','screen','table','objects','consoles','transitionSeconds','follow'}:raise ValueError('Invalid home fields')
    if value['tv'] not in TVS or value['viewport'] not in ({'width':720,'height':480},{'width':720,'height':540}):raise ValueError('Invalid home TV or viewport')
    table=value['table']
    if set(table)!={'model','scale'} or table['model'] not in TABLES:raise ValueError('Invalid home table')
    if set(value['objects'])!={'table','tv','status'}:raise ValueError('Invalid home objects')
    consoles=value['consoles']
    if not isinstance(consoles,dict) or not 1<=len(consoles)<=16 or not set(consoles)<=set(MODELS):raise ValueError('Invalid home consoles')
    identities=[{'snes-us':'snes','md-jp':'md'}.get(key,key) for key in consoles]
    if len(set(identities))!=len(identities):raise ValueError('Choose one regional model per console')
    out=dict(version=1,kind='home',tv=value['tv'],viewport=copy.deepcopy(value['viewport']),camera=camera(value['camera']),
        table=dict(model=table['model'],scale=vector(table['scale'],.1,5)),objects={k:placement(v) for k,v in value['objects'].items()},
        consoles={k:placement(v) for k,v in consoles.items()},transitionSeconds=number(value.get('transitionSeconds',.8),.1,5),follow=number(value.get('follow',.2),0,1))
    if value.get('screen') is not None:out['screen']=camera(value['screen'])
    return out

def native_text(value):
    p=validate(value)
    def nums(v):return ' '.join(format(x,'.9g') for x in v)
    if p['kind']=='room':
        b=p['bounds'];surfaces=p.get('surfaces',{})
        lines=['SLOTWORLD2' if surfaces else 'SLOTWORLD1','room '+nums([p['floor'],*[b[k] for k in ('left','right','back','front','height')]])]
        lines+=['surface '+key+' '+nums(s['color']+[s['tile']])+' '+(s.get('texture') or '-') for key,s in surfaces.items()]
        lines+=['table '+key+' '+nums(at['position']+at['rotation']) for key,at in p['tables'].items()]
        lines+=['path '+v['from']+' '+v['to']+' '+nums([v['seconds']]+v['first']+v['second']) for v in p['paths']]
    else:
        lines=['SLOTHOME1','viewport '+str(p['viewport']['width'])+' '+str(p['viewport']['height'])]
        for key,label in [('camera','camera'),('screen','view_screen')]:
            if key in p:c=p[key];lines.append(label+' '+nums(c['position']+c['target']+[c['fov']]))
        lines += [key+' '+nums(at['position']+at['rotation']) for key,at in p['objects'].items()]
        lines+=['table_asset '+p['table']['model'],'table_scale '+nums(p['table']['scale']),'transition '+nums([p['transitionSeconds']]),'follow '+nums([p['follow']])]
        lines+=['console '+key+' '+nums(at['position']+at['rotation']) for key,at in p['consoles'].items()]
    return '\n'.join(lines)+'\n'

def profile_key(value):
    p=validate(value);return 'room' if p['kind']=='room' else 'home-'+p['tv']

def parse_home(text,tv):
    lines=text.splitlines()
    if not lines or lines[0]!='SLOTHOME1':raise ValueError('Expected a native home profile')
    out=dict(version=1,kind='home',tv=tv,objects={},consoles={},table=dict(model='table',scale=[1,1,1]));seen=set()
    for line in lines[1:]:
        fields=line.split()
        if not fields:continue
        key=fields.pop(0)
        if key=='console':
            model=fields.pop(0)
            if model in out['consoles']:raise ValueError('Duplicate home console')
            v=list(map(float,fields));out['consoles'][model]=dict(position=v[:3],rotation=v[3:]);continue
        if key in seen:raise ValueError('Duplicate home record')
        seen.add(key)
        if key=='viewport':out['viewport']=dict(zip(('width','height'),map(int,fields)))
        elif key in ('camera','view_screen'):
            if len(fields)!=7:raise ValueError('Invalid home camera')
            v=list(map(float,fields));out['camera' if key=='camera' else 'screen']=dict(position=v[:3],target=v[3:6],fov=v[6])
        elif key in ('table','tv','status'):
            v=list(map(float,fields));out['objects'][key]=dict(position=v[:3],rotation=v[3:])
        elif key=='table_asset':out['table']['model']=fields[0]
        elif key=='table_scale':out['table']['scale']=list(map(float,fields))
        elif key in ('transition','follow'):out['transitionSeconds' if key=='transition' else key]=float(fields[0])
        else:raise ValueError('Unknown home record')
    return validate(out)

def parse_world(text):
    lines=text.splitlines()
    if not lines or lines[0] not in ('SLOTWORLD1','SLOTWORLD2'):raise ValueError('Expected a native room profile')
    out=dict(version=1,kind='room',tables={},paths=[])
    for line in lines[1:]:
        fields=line.split()
        if not fields:continue
        key=fields.pop(0)
        if key=='surface' and lines[0]=='SLOTWORLD2' and len(fields)==6 and fields[0] in SURFACES and fields[0] not in out.get('surfaces',{}):
            values=list(map(float,fields[1:5]))
            out.setdefault('surfaces',{})[fields[0]]=dict(color=values[:3],tile=values[3],**({} if fields[5]=='-' else dict(texture=fields[5])))
        elif key=='room' and len(fields)==6 and 'floor' not in out:
            values=list(map(float,fields));out['floor']=values[0]
            out['bounds']=dict(zip(('left','right','back','front','height'),values[1:]))
        elif key=='table' and len(fields)==7:
            model=fields.pop(0)
            if model in out['tables']:raise ValueError('Duplicate room table')
            values=list(map(float,fields));out['tables'][model]=dict(position=values[:3],rotation=values[3:])
        elif key=='path' and len(fields)==9:
            start,end=fields[:2];values=list(map(float,fields[2:]))
            out['paths'].append(dict(zip(('from','to'),(start,end)),seconds=values[0],first=values[1:4],second=values[4:]))
        else:raise ValueError('Invalid or unknown room record')
    return validate(out)

def default_room():
    def at(x,y,z,yaw=0):return dict(position=[x,y,z],rotation=[0,yaw,0])
    return dict(version=1,kind='room',floor=0,bounds=dict(left=-8000,right=8000,back=-6000,front=6000,height=3600),
        tables={'table':at(0,805.077,0),'wooden-table':at(4200,416.822,0,90),'tv-stand':at(-4200,660.95,0)},
        paths=[dict(zip(('from','to'),pair),seconds=1.4,first=[0,180,0],second=[0,180,0]) for pair in [('table','wooden-table'),('table','tv-stand')]])

def save(root,value,expected=None):
    p=validate(value);key=profile_key(p);folder=Path(root)/'scene-layouts';folder.mkdir(parents=True,exist_ok=True)
    saved=folder/(key+'.json');derivative=Path(root)/'build/tabletop/assets/layouts'/(key+('.world' if key=='room' else '.scene'))
    old=saved.read_bytes() if saved.exists() else None
    old_hash=hashlib.sha256(old).hexdigest() if old else None
    if expected!=old_hash:raise ValueError('Saved scene changed in another editor; reload before saving')
    data=(json.dumps(p,indent=2)+'\n').encode()
    if old and native_text(json.loads(old))==native_text(p):data=old
    if old and data!=old:
        history=folder/'history';history.mkdir(exist_ok=True);backup=history/(key+'-'+str(time.time_ns())+'.json');backup.write_bytes(old)
        if hashlib.sha256(backup.read_bytes()).digest()!=hashlib.sha256(old).digest():raise OSError('Room history verification failed')
    derivative.parent.mkdir(parents=True,exist_ok=True)
    for target,contents in [(saved,data),(derivative,native_text(p).encode())]:
        temp=target.with_suffix(target.suffix+'.'+secrets.token_hex(6)+'.tmp');temp.write_bytes(contents);temp.replace(target)
    return dict(key=key,json=str(saved),native=str(derivative),sha256=hashlib.sha256(data).hexdigest())
