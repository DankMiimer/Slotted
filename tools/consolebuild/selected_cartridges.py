"""Pack and select named cartridge alternatives. MIT processing, CC BY assets.

Preparation writes named alternatives first. --activate preserves the current
runtime package with verified hashes before copying only the owned media files.
Never accepts N64, never writes authored layouts or console geometry.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .cartridges import save_mesh
from .textured import ROOT, SLOT

KEYS = ('nds','gba','nes','gb','gbc','md')
PACKAGES = SLOT/'cartridges/models'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve_current(key):
    target = SLOT/'consoles'/key
    files = sorted(p for p in target.glob('media*') if p.is_file()
                   and not p.name.startswith('media-ea'))
    hashes = {p.name:digest(p) for p in files}
    identity = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
    previous = PACKAGES/key/('previous-'+identity)
    previous.mkdir(parents=True,exist_ok=True)
    for p in files:
        dest = previous/p.name
        if not dest.exists(): shutil.copy2(p,dest)
        if digest(dest)!=hashes[p.name]: raise ValueError('Previous copy mismatch: '+str(p))
    (previous/'package.json').write_text(json.dumps(dict(system=key,
        description='Preserved current cartridge before selected-source activation',files=hashes),indent=2)+'\n')
    return previous.name


def pack(key):
    if key not in KEYS: raise ValueError('Unsupported cartridge: '+key)
    work=ROOT/'build/selected-cartridges'/key
    reg=json.loads((work/'registration.json').read_text())
    parts=json.loads((work/'parts.json').read_text())
    data=np.load(work/'corners.npz')
    excluded=set(reg['excluded_materials'])
    tiles={};material_tiles={};blanks={}
    for name,entry in parts['images'].items():
        src=entry['image']
        if src and name not in excluded:
            identity=src['sha256']
            im=Image.open(work/'images'/src['file']).convert('RGB')
            # Runtime albedo profile; full-resolution sources/maps are retained.
            im.thumbnail((1008,1008),Image.Resampling.LANCZOS)
            if reg['blank_uv']:
                u0,v0,u1,v1=reg['blank_uv']
                rect=(int(u0*im.width)-2,int((1-v1)*im.height)-2,
                      int(u1*im.width)+2,int((1-v0)*im.height)+2)
                ImageDraw.Draw(im).rectangle(rect,fill=(58,58,58) if key in ('nds','gba') else (155,155,151))
                blanks[name]=rect
        else:
            c=np.array(entry['factor'])
            c=np.where(c<=.0031308,c*12.92,1.055*c**(1/2.4)-.055)
            colour=(155,155,151) if name in excluded else tuple(np.clip(c*255,0,255).astype(int))
            im=Image.new('RGB',(4,4),colour)
            identity='swatch-'+str(colour)
        tiles[identity]=im
        material_tiles[name]=identity
    size=128;pad=2
    while True:
        x=y=row=0;boxes={}
        for identity,im in tiles.items():
            w,h=im.width+2*pad,im.height+2*pad
            if w>size or h>size:break
            if x+w>size:x=0;y+=row;row=0
            if y+h>size:break
            boxes[identity]=(x+pad,y+pad,im.width,im.height)
            x+=w;row=max(row,h)
        if len(boxes)==len(tiles):break
        size*=2
    if size>4096:raise ValueError('Native texture budget exceeded')
    rgba=np.zeros((size,size,4),np.uint8);rgba[:,:,:3]=65
    uv=data['uv'].copy();uv[:,1]=1-uv[:,1]
    material=np.repeat(data['triangle'][:,1],3)
    for identity,im in tiles.items():
        x,y,w,h=boxes[identity]
        rgba[y-pad:y+h+pad,x-pad:x+w+pad,:3]=np.pad(np.array(im),((pad,pad),(pad,pad),(0,0)),mode='edge')
    for index,name in enumerate(parts['materials']):
        identity=material_tiles[name];x,y,w,h=boxes[identity]
        selected=material==index
        if tiles[identity].size==(4,4):uv[selected]=.5
        # Some importers leave whole-tile UV offsets. Fold only integer offsets;
        # reject crossing/out-of-range triangles instead of silently clamping.
        raw=uv[selected]
        if raw.min() < -1e-4 or raw.max()>1.0001:
            raw-=np.floor(raw.min(0)+1e-4)
        uv[selected]=(np.array((x,y))+raw*np.array((w-1,h-1))+.5)/size
    target=PACKAGES/key/reg['uid'];target.mkdir(parents=True,exist_ok=True)
    info=save_mesh(target,'media',data['position'],data['normal'],uv,rgba,.5,False)
    label=np.load(work/'label.npz');t=label['uv'].copy();t[:,1]=1-t[:,1]
    li=save_mesh(target,'media-label',label['position'],label['normal'],t,np.full((8,8,4),255,np.uint8),.5,False)
    for suffix in ('-master','-physical',''):
        shutil.copy2(work/('media'+suffix+'.glb'),target/('media'+suffix+'.glb'))
    reg.update(prepared=info,label_prepared=li,atlas=dict(size=size,source_tile_limit=1008,
        material_tiles=material_tiles,blank_pixel_rectangles=blanks),
        runtime_material_limit='Opaque albedo + source normals; normal/metallic/roughness/transmission maps retained only in full source',
        selected_package=str(target.relative_to(SLOT)).replace('\\','/'))
    (target/'media-registration.json').write_text(json.dumps(reg,indent=2)+'\n')
    (target/'media-info.json').write_text(json.dumps(dict(info,licence=reg['licence'],
        source=reg['url'],creator=reg['creator'],decimation=False),indent=2)+'\n')
    (target/'CREDITS.txt').write_text(reg['creator']+' — '+reg['url']+'\nCC BY 4.0 — https://creativecommons.org/licenses/by/4.0/\n'+
        '\n'.join(reg['modifications'])+'\n'+reg['source_quality_limitation']+'\n',encoding='utf-8')
    hashes={p.name:digest(p) for p in target.iterdir() if p.is_file() and p.name!='package.json'}
    (target/'package.json').write_text(json.dumps(dict(system=key,uid=reg['uid'],files=hashes),indent=2)+'\n')
    family=ROOT/'third_party/models'/('cartridge-'+key+'-'+reg['uid'][:8]);family.mkdir(parents=True,exist_ok=True)
    (family/'source.json').write_text(json.dumps(reg,indent=2)+'\n')
    print('PACKED',key,info,'label',li,'atlas',size,flush=True)
    return target


def activate(key, package):
    if key not in KEYS:raise ValueError('Protected/unsupported cartridge: '+key)
    source=PACKAGES/key/package
    if Path(package).name!=package or not source.resolve().is_relative_to((PACKAGES/key).resolve()):
        raise ValueError('Invalid package identity')
    manifest=json.loads((source/'package.json').read_text())
    if manifest['system']!=key:raise ValueError('Wrong package system')
    for name,h in manifest['files'].items():
        if Path(name).name!=name or digest(source/name)!=h:raise ValueError('Invalid package: '+name)
    previous=preserve_current(key)
    target=SLOT/'consoles'/key
    for name in manifest['files']:
        if name.startswith('media'):
            shutil.copy2(source/name,target/name)
    # Stale sidecars must never bind to the new vertex buffer. Preserve them in
    # the prior named package, then remove only these exact owned file names.
    for name in ('media.paint.mask','media.texture','media.albedo.png','media-label.mesh','media-label.texture','media-label.albedo.png','media-registration.json'):
        if name not in manifest['files'] and (target/name).exists():(target/name).unlink()
    selection=PACKAGES/key/'selection.json'
    selection.write_text(json.dumps(dict(system=key,selected=package,previous=previous),indent=2)+'\n')
    print('ACTIVATED',key,package,'previous',previous,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('systems',nargs='+',choices=KEYS)
    ap.add_argument('--activate',action='store_true')
    ap.add_argument('--select',metavar='PACKAGE',help='Select an already preserved package, including a previous alternative')
    args=ap.parse_args()
    if args.select:
        if len(args.systems)!=1 or args.activate:ap.error('--select requires exactly one system and no --activate')
        activate(args.systems[0],args.select)
        raise SystemExit(0)
    for key in args.systems:
        target=pack(key)
        if args.activate:activate(key,target.name)
