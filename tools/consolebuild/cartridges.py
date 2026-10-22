"""Pack registered cartridge albedo, UVs and source-surface game labels. MIT.

Run the safe Blender adapter first, then python -m tools.consolebuild.cartridges.
Image tiles are reduced or copied at their original size, never enlarged.
"""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from .textured import ROOT,SLOT,fnv,coverage

KEYS=('snes','pico8','gba','n64','tzakol')

def save_mesh(target,part,p,n,t,rgba,luma,paint):
    if not np.isfinite(t).all() or t.min()<0 or t.max()>1:raise ValueError(f'{target}/{part}: UV leaves its atlas')
    size=rgba.shape[0];sample=np.clip((t*size).astype(int),0,size-1)
    colour=rgba[sample[:,1],sample[:,0],:3]/255
    weight=np.where(rgba[sample[:,1],sample[:,0],3]>127,
        np.clip((colour@np.array([.299,.587,.114]))/luma*192,1,255),0).astype(np.uint8)
    raw,uvs,weights,indices,lookup=[],[],[],[],{}
    for i in range(len(p)):
        vertex=struct.pack('<9f',*p[i],*n[i],*colour[i]);uv=struct.pack('<2f',*t[i]);key=vertex+uv
        if key not in lookup:
            lookup[key]=len(raw);raw.append(vertex);uvs.append(uv);weights.append(int(weight[i]))
        indices.append(lookup[key])
    if len(raw)>65535:raise ValueError('Native vertex limit exceeded')
    v=b''.join(raw);ix=struct.pack('<%dH'%len(indices),*indices)
    (target/(part+'.mesh')).write_bytes(struct.pack('<8sIII',b'SCTOON2\0',len(raw),len(indices),len(indices))+v+ix)
    albedo=target/(part+'.albedo.png');Image.fromarray(rgba).save(albedo,optimize=True)
    (target/(part+'.texture')).write_bytes(struct.pack('<8sIIIfQQQ',b'SCTEX003',len(raw),size,size,luma,fnv(v),fnv(ix),fnv(albedo.read_bytes()))+b''.join(uvs))
    if paint:(target/(part+'.paint.mask')).write_bytes(struct.pack('<8sIQ',b'SCPAINT1',len(raw),fnv(v))+bytes(weights))
    return dict(vertices=len(raw),triangles=len(indices)//3,mesh_sha256=hashlib.sha256((target/(part+'.mesh')).read_bytes()).hexdigest())

def pack(key):
    work=ROOT/'build/textured'/('cartridge-'+key)
    reg=json.loads((work/'registration.json').read_text());parts=json.loads((work/'parts.json').read_text());data=np.load(work/'corners.npz')
    mats=parts['materials'];mat=np.repeat(data['triangle'][:,1],3);roles=np.repeat(data['triangle'][:,0],3)
    # Images whose only role is fixed game art are deliberately never copied.
    excluded={'gba':{'gblabel'},'n64':{'LogoMaterial'}}.get(key,set())
    images={}
    for name in mats:
        entry=parts['images'][name]
        if entry['image'] and name not in excluded:
            im=Image.open(work/'images'/entry['image']['file']).convert('RGB')
            limit=2048 if key=='snes' else 992 if key=='gba' else 1024
            im.thumbnail((limit,limit),Image.Resampling.LANCZOS);images[name]=im
        else:
            linear=np.array(entry['factor']);srgb=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
            colour=(198,195,184) if name in excluded else tuple(np.clip(srgb*255,0,255).astype(int))
            images[name]=Image.new('RGB',(8,8),colour)
    # Clear all fixed artwork in kept source images before packing.
    blank={'snes':[(0,.758,.495,.928)],'tzakol':[(.44,.059,.75,.297)],'pico8':[(.101,.118,.9,.947)]}.get(key,[])
    for im in images.values():
        draw=ImageDraw.Draw(im)
        for u0,v0,u1,v1 in blank:
            draw.rectangle((int(u0*im.width),int((1-v1)*im.height),int(u1*im.width),int((1-v0)*im.height)),fill=(198,195,184))
    # Deterministic shelf packing; constant swatches use their own small tiles.
    size=128;padding=16 if key=='gba' else 0
    while True:
        x=y=row=0;boxes={};ok=True
        for name,im in images.items():
            tw,th=im.width+2*padding,im.height+2*padding
            if tw>size or th>size:ok=False;break
            if x+tw>size:x=0;y+=row;row=0
            if y+th>size:ok=False;break
            boxes[name]=(x+padding,y+padding,im.width,im.height);x+=tw;row=max(row,th)
        if ok:break
        size*=2
    rgba=np.zeros((size,size,4),np.uint8);rgba[:,:,:3]=180
    uv=data['uv'].copy();uv[:,1]=1-uv[:,1]
    painted_roles=np.array([p.get('role')=='paint' for p in parts['parts']])[roles]
    for name,im in images.items():
        x,y,w,h=boxes[name];pixels=np.array(im)
        hsv=np.array(im.convert('HSV'));plastic=(hsv[:,:,1]<52)&(hsv[:,:,2]>25)
        if name in excluded:plastic[:]=False
        for u0,v0,u1,v1 in blank:
            plastic[int((1-v1)*h):int((1-v0)*h)+1,int(u0*w):int(u1*w)+1]=False
        tile=np.dstack((pixels,plastic.astype(np.uint8)*255))
        tile=np.pad(tile,((padding,padding),(padding,padding),(0,0)),mode='wrap')
        rgba[y-padding:y+h+padding,x-padding:x+w+padding]=tile
        selected=mat==mats.index(name)
        if im.size==(8,8):uv[selected]=(.5,.5)
        uv[selected]=(np.array((x,y))+uv[selected]*np.array((max(1,w-1),max(1,h-1)))+.5)/size
    # Role coverage prevents PCB/metal sharing a map from being repainted.
    used=coverage(np.stack((uv[:,0],1-uv[:,1]),axis=1),np.arange(len(uv)).reshape(-1,3)[painted_roles.reshape(-1,3).all(1)],size)
    rgba[:,:,3]=np.minimum(rgba[:,:,3],np.array(used.filter(ImageFilter.MaxFilter(3))))
    lum=rgba[:,:,:3]@np.array([.299,.587,.114])/255
    luma=float(np.median(lum[rgba[:,:,3]>127]))
    target=SLOT/'consoles'/('snes' if key=='tzakol' else key);part='media-tzakol' if key=='tzakol' else 'media'
    info=save_mesh(target,part,data['position'],data['normal'],uv,rgba,luma,True)
    label=np.load(work/'label.npz');t=label['uv'].copy();t[:,1]=1-t[:,1]
    dummy=np.full((8,8,4),255,np.uint8)
    label_info=save_mesh(target,part+'-label',label['position'],label['normal'],t,dummy,.5,False)
    reg.update(atlas=dict(size=size,tiles=boxes,repeat_border_px=padding,source_uv_range=[data['uv'].min(0).tolist(),data['uv'].max(0).tolist()],
        blank_uv=blank,excluded_images=sorted(excluded),paint_luma=luma),prepared=info,label_prepared=label_info)
    (target/(part+'-registration.json')).write_text(json.dumps(reg,indent=2)+'\n',newline='\n')
    (target/(part+'-info.json')).write_text(json.dumps(dict(info,licence=reg['licence'],source=reg['url'],creator=reg['creator'],decimation=False),indent=2)+'\n',newline='\n')
    family=ROOT/'third_party/models'/('cartridge-'+key);family.mkdir(parents=True,exist_ok=True)
    (family/'source.json').write_text(json.dumps(reg,indent=2)+'\n',newline='\n')
    if key=='tzakol':
        other=SLOT/'consoles/snes-us';factor=1.55/reg['q']
        us=save_mesh(other,part,data['position']*factor,data['normal'],uv,rgba,luma,True)
        us_label=save_mesh(other,part+'-label',label['position']*factor,label['normal'],t,dummy,.5,False)
        registered=dict(reg,q=1.55,prepared=us,label_prepared=us_label)
        (other/(part+'-registration.json')).write_text(json.dumps(registered,indent=2)+'\n',newline='\n')
        (other/(part+'-info.json')).write_text(json.dumps(dict(us,licence=reg['licence'],source=reg['url'],creator=reg['creator'],decimation=False),indent=2)+'\n',newline='\n')
    print(key,info,'label',label_info,'atlas',size,flush=True)

if __name__=='__main__':
    for key in sys.argv[1:] or KEYS:pack(key)
