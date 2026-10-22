"""Bram Verheyen's Gameboy Classic, source UVs and full detail. CC BY-NC 4.0.

Blender 4.5 --factory-startup --disable-autoexec. Processing code MIT.
"""
import json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb
URL='https://sketchfab.com/3d-models/gameboy-classic-854c46e14ce24779ad64ae74cb9b9089'
Q=168/90


def main():
    source=Path(sys.argv[sys.argv.index('--')+1]);objects=tb.import_source(source);bpy=tb.bpy
    screen=objects['GB_02_low_Screen'];front=objects['GB_01_low_Front'];back=objects['GB_02_low_Back']
    points=np.unique(np.round([tuple(v.co) for v in screen.data.vertices],5),axis=0)
    values,basis=np.linalg.eigh(np.cov(points.T));normal=basis[:,0];u=basis[:,2]
    def centre(o):return np.mean([tuple(v.co) for v in o.data.vertices],axis=0)
    if np.dot(normal,centre(front)-centre(back))<0:normal=-normal
    if u[0]<0:u=-u
    up=np.cross(normal,u)
    rotation=Matrix([tuple(u)+(0,),tuple(-normal)+(0,),tuple(up)+(0,),(0,0,0,1)])
    for o in objects.values():o.data.transform(rotation)
    lo,hi=tb.bounds(objects.values());centre_mm=(lo+hi)/2;mm=90/(hi.x-lo.x)
    for o in objects.values():o.data.transform(Matrix.Scale(mm,4)@Matrix.Translation(-centre_mm));o.data.update()
    # The active LCD is the eight large planar faces, excluding its narrow bevel.
    active=lambda tri:tri.area>100 and tri.normal.y<-.999
    lcd=tb.copy_triangles(screen,'LCD screen',active)
    bevel=tb.copy_triangles(screen,'DMG LCD bevel',lambda tri:not active(tri))
    bpy.data.objects.remove(screen,do_unlink=True);objects.pop('GB_02_low_Screen')
    floor=tb.ray(back,(0,40,60),(0,-1,0)).y
    label_y=floor+7.8+.2
    lip=None
    for z in np.arange(20,74,.01):
        hit=tb.ray(back,(0,40,float(z)),(0,-1,0))
        if hit and hit.y<label_y:lip=float(z);break
    assert lip is not None,'No rear Game Pak lip found'
    lo,hi=tb.bounds([back]);top=hi.z
    kept=[lcd,bevel];flags={lcd.name:dict(role='lcd')}
    paint={'GB_01_low_Front','GB_02_low_Back','GB_03_low_BatteryClip'}
    for name,o in objects.items():
        o['source_part']=name;o.name={'GB_01_low_Front':'DMG front housing','GB_02_low_Back':'DMG rear housing'}.get(name,'DMG '+name.replace('GB_03_low_','').replace('GB_02_low_','').replace('GB_01_low_',''))
        kept.append(o)
        if name in paint:flags[o.name]=dict(role='paint')
    all_lo,all_hi=tb.bounds(kept);lcd_lo,lcd_hi=tb.bounds([lcd])
    reg=dict(model='gb',adapter='verheyen_gb.py',author='Bram Verheyen',title='Gameboy Classic',url=URL,
        licence='CC-BY-NC-4.0',licence_url='https://creativecommons.org/licenses/by-nc/4.0/',
        source_file=source.name,source_sha256=tb.sha256(source),source_triangles=9856,decimation=False,
        rotation_rows=[list(row) for row in rotation],mm_per_source_unit=mm,native_units_per_mm=Q,
        scale_basis='Uniform, 90 mm complete source width; artist proportions retained',
        source_size_mm=list(all_hi-all_lo),lcd_size_mm=[lcd_hi.x-lcd_lo.x,lcd_hi.z-lcd_lo.z],
        bay_floor_mm=floor,game_pak_mm=[57,65.5,7.8],cart_label_native=-label_y*Q,rear_lip_mm=lip,
        spec=dict(ry=top*Q,depth=(all_hi.y-all_lo.y)*Q/2,slot=lip*Q),
        modifications=['Undo presentation tilt using source LCD plane and horizontal axis',
            'Retain all 9856 triangles, UVs and source cosmetic wear/sticker',
            'Separate actual planar LCD from bevel for live game information',
            'Register full Game Pak to measured bay floor and rear housing lip',
            'Repeat source U range continuously; 4K source maps preserved, 2048px runtime atlas',
            'Source albedo and simple lighting; no normal/roughness/metallic maps'])
    tb.to_native(kept,(0,0,0),1,Q)
    work=tb.ROOT/'build/textured/gb';tb.write_corners(kept,work,flags)
    (work/'registration.json').write_text(json.dumps(reg,indent=2)+'\n')
    tb.export_master_glb(kept,work/'model-master.glb')
    target=tb.ROOT/'theme/art-book-slot/_slot/consoles/gb'
    provenance=dict(source_creator='Bram Verheyen',source_licence='CC-BY-NC-4.0',source_url=URL)
    for name,physical in [('model.glb',False),('model-master.glb',False),('model-physical.glb',True)]:
        tb.export_geometry_glb(kept,target/name,Q,physical=physical,provenance=provenance)
    print('GB PREPARED',json.dumps(reg),flush=True)


if __name__=='__main__':main()
