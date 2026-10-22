"""Register the user-selected cartridge originals, preserving geometry and UVs.

Run with Blender --factory-startup --disable-autoexec -t 1. MIT processing code;
each model and its derivatives retain the source licence in registration.json.
"""
import json, math, sys
from pathlib import Path
from mathutils import Matrix
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb

SOURCES = {
    'snes': ('snescart/super_nintendo_cartridge.glb', 130, math.pi, 0, 1.6,
             'SomeKevin; UVs cpt.brotzeit', 'CC-BY-4.0', 'b2076d8a65d648ff99bf51ca9d5fca2a'),
    'pico8': ('pico8/song_of_morus_pico-8_cartridge.glb', 60, 0, 6, 2.2,
              'sunnychow', 'CC-BY-4.0', 'fc89d8b44a934400bdf282600f61d369'),
    'gba': ('gbacart/gameboy_advance_cartridge.glb', 60, -math.pi/2, 0, 224/82,
            'Vxcl', 'CC-BY-4.0', '38c1e6702e5d4f21af1d0930689b1d10'),
    'n64': ('n64cart/nintendo_64_cart.glb', 116, 0, 0, 1.5,
            'Chris Sweetwood', 'CC-BY-NC-SA-4.0', '7b93f9cb196743009c2211a5e47643d8'),
    'tzakol': ('tzakol/game_cartridge_tzakol_in_exile.glb', 130, math.pi/2, 20, 1.6,
               'kutejnikov', 'CC-BY-4.0', '49251a57f2c9418faec314a5a5ab7ee9'),
}

def run(key):
    filename,width,angle,thickness,q,author,licence,uid=SOURCES[key]
    source=tb.ROOT/'research/model-options-20261016'/filename
    objects=list(tb.import_source(source).values())
    if key=='n64':
        # The source's other two cartridges are posed copies of this upright one.
        for o in list(objects):
            if o.name not in ('BezierCurve','BezierCurve_Material_0'):
                tb.bpy.data.objects.remove(o,do_unlink=True);objects.remove(o)
    for o in objects:o.data.transform(Matrix.Rotation(angle,4,'Z'));o.data.update()
    lo,hi=tb.bounds(objects);mm=width/(hi.x-lo.x)
    original_size=[float(v*mm) for v in hi-lo]
    depth_scale=thickness/original_size[1] if thickness else 1
    for o in objects:o.data.transform(Matrix.Diagonal((1,depth_scale,1,1)))
    lo,hi=tb.bounds(objects);centre=(lo+hi)/2
    tb.to_native(objects,centre,mm,q)
    out=tb.ROOT/'build/textured'/('cartridge-'+key);out.mkdir(parents=True,exist_ok=True)
    flags={o.name:dict(role='paint') for o in objects}
    for o in objects:
        if key=='gba' and o.name not in ('Object_4','Object_5'):flags[o.name]['role']='fixed'
        if key=='pico8' and o.name!='Cart_3':flags[o.name]['role']='fixed'
        if key=='tzakol' and o.name=='plata_low':flags[o.name]['role']='fixed'
        if key=='n64' and o.name=='BezierCurve':flags[o.name]['role']='fixed'
    tb.write_corners(objects,out,flags)
    data=np.load(out/'corners.npz');tris=data['triangle'];parts=json.loads((out/'parts.json').read_text())
    names=[p['name'] for p in parts['parts']]
    uv=data['uv'].reshape(-1,3,2);normal=data['normal'].reshape(-1,3,3)
    if key=='snes':
        selected=((uv[:,:,0]>=0)&(uv[:,:,0]<.494)&(uv[:,:,1]>.759)&(uv[:,:,1]<.927)).all(1)
        pos=data['position'].reshape(-1,3,3)
        selected &= (pos[:,:,2].mean(1)>7*q)&(pos[:,:,1].mean(1)>0)
    elif key=='tzakol':
        selected=((uv[:,:,0].max(1)>.445)&(uv[:,:,0].min(1)<.748)&
                  (uv[:,:,1].max(1)>.06)&(uv[:,:,1].min(1)<.296))
    else:
        label_name={'pico8':'Sticker_6','gba':'Cube_0','n64':'BezierCurve'}[key]
        selected=tris[:,0]==names.index(label_name)
    selected &= normal[:,:,2].mean(1)>.55
    if selected.sum()<2:raise RuntimeError(f'{key}: label selection is empty')
    p=data['position'].reshape(-1,3,3)[selected].copy()
    n=normal[selected].copy();p+=n*(.035*q)
    if key=='tzakol':
        # The artist painted the sticker inside a larger shell UV triangle.
        # Clip its real surface at the sticker boundary, preserving interpolation.
        clipped=[]
        for pos,nrm,tex in zip(p,n,uv[selected]):
            poly=[np.concatenate((pos[i],nrm[i],tex[i])) for i in range(3)]
            for axis,edge,sign in [(6,.445,1),(6,.748,-1),(7,.06,1),(7,.296,-1)]:
                result=[]
                for i,a0 in enumerate(poly):
                    b0=poly[(i+1)%len(poly)];da=(a0[axis]-edge)*sign;db=(b0[axis]-edge)*sign
                    if da>=0:result.append(a0)
                    if (da>=0)!=(db>=0):result.append(a0+(b0-a0)*da/(da-db))
                poly=result
                if not poly:break
            for i in range(1,len(poly)-1):clipped.append([poly[0],poly[i],poly[i+1]])
        clipped=np.array(clipped);p=clipped[:,:,:3];n=clipped[:,:,3:6]
    a,b=p.reshape(-1,3).min(0)/q,p.reshape(-1,3).max(0)/q
    label_uv=np.stack(((p[:,:,0]/q-a[0])/(b[0]-a[0]),(p[:,:,1]/q-a[1])/(b[1]-a[1])),axis=-1)
    np.savez_compressed(out/'label.npz',position=p.reshape(-1,3),normal=n.reshape(-1,3),uv=label_uv.reshape(-1,2))
    bounds=tb.bounds(objects);size=[(bounds[1][i]-bounds[0][i])*100/q for i in [0,2,1]]
    registration=dict(adapter='cartridges_blender.py',key=key,creator=author,licence=licence,
        url='https://sketchfab.com/3d-models/'+uid,source_file=filename,source_sha256=tb.sha256(source),
        q=q,size_mm=size,source_size_mm=[original_size[0],original_size[2],original_size[1]],depth_scale=depth_scale,
        label_mm=[float((a[0]+b[0])/2),float((a[1]+b[1])/2),float((b[0]-a[0])/2),float((b[1]-a[1])/2),float(b[2])],
        label_triangles=len(p),decimation=False,
        modifications=['Registered and centred source; independent shell only','Fixed front game art blanked; per-game label follows source surface',
            'Simple albedo lighting; no source normal, metallic or roughness maps']+
            ([f'Depth scaled by {depth_scale:.9g} to the existing slot; width/height unchanged'] if depth_scale!=1 else []))
    (out/'registration.json').write_text(json.dumps(registration,indent=2)+'\n')
    target=tb.ROOT/'theme/art-book-slot/_slot/consoles'/('snes' if key=='tzakol' else key)
    target.mkdir(parents=True,exist_ok=True);part='media-tzakol' if key=='tzakol' else 'media'
    tb.export_master_glb(objects,out/'registered-master.glb')
    tb.export_geometry_glb(objects,target/(part+'-master.glb'),q,provenance={'creator':author,'licence':licence,'source':registration['url']})
    tb.export_geometry_glb(objects,target/(part+'-physical.glb'),q,physical=True,provenance={'creator':author,'licence':licence,'source':registration['url']})
    tb.export_geometry_glb(objects,target/(part+'.glb'),q,provenance={'creator':author,'licence':licence,'source':registration['url']})
    if key=='tzakol':
        other=target.parent/'snes-us';other.mkdir(exist_ok=True)
        for o in objects:o.data.transform(Matrix.Scale(1.55/q,4))
        for suffix,physical in [('-master',False),('-physical',True),('',False)]:
            tb.export_geometry_glb(objects,other/(part+suffix+'.glb'),1.55,physical=physical,provenance={'creator':author,'licence':licence,'source':registration['url']})
    print('REGISTERED',key,json.dumps(registration),flush=True)

if __name__=='__main__':
    for key in sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else SOURCES:run(key)
