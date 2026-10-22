"""Registered handheld lid axes and native/Blender closed poses (MIT)."""
import math,json
from pathlib import Path
import numpy as np
import ds_lid
ROOT=Path(__file__).resolve().parents[2]

def ags_registration(hinge_points,screen_points):
    # Undo only the known physical depth correction for the circle fit. The
    # barrel was circular before that correction and is now slightly elliptical.
    points=np.unique(np.round(np.asarray(hinge_points)[:,1:3],4),axis=0)
    points[:,1]/=84.6/82;rng=np.random.default_rng(4);best=None
    for _ in range(2500):
        sample=points[rng.choice(len(points),3,replace=False)]
        try:a,b,k=np.linalg.solve(np.c_[sample,np.ones(3)],(sample*sample).sum(axis=1))
        except np.linalg.LinAlgError:continue
        centre=np.array((a,b))/2;r2=k+(centre*centre).sum()
        if not 1<r2<100:continue
        error=abs(np.linalg.norm(points-centre,axis=1)-math.sqrt(r2));mask=error<.015
        if best is None or mask.sum()>best.sum():best=mask
    assert best is not None and best.sum()>50
    fit=points[best];a,b,k=np.linalg.lstsq(np.c_[fit,np.ones(len(fit))],(fit*fit).sum(axis=1),rcond=None)[0]
    centre=np.array((a,b))/2
    screen=np.asarray(screen_points)[:,1:3];_,basis=np.linalg.eigh(np.cov(screen.T));up=basis[:,-1]
    if up[0]<0:up=-up
    return dict(hinge_xyz_mm=[0,float(centre[0]),float(centre[1]*84.6/82)],
        open_degrees=math.degrees(math.atan2(up[0],up[1])),
        method='Dominant circular section of moving hinge, before depth correction; LCD long-axis PCA',
        fit_points=int(best.sum()),section_points=len(points),fit_tolerance_mm=.015,
        uncertainty='Axis registered to authored geometry, not an OEM hinge drawing')

def ags_spec():
    return json.loads((ROOT/'third_party/models/thegraphicsgeek-ags/source.json').read_text())['lid']

def native_header():
    a=ags_spec();q=224/82
    ds_hinge,ds_open=ds_lid.HINGE,ds_lid.OPEN_DEGREES
    registered=ROOT/'theme/art-book-slot/_slot/consoles/nds/registration.json'
    if registered.exists() and registered.with_name('model.texture').exists():
        # The textured Cianon DS Lite registers its own lid axis and pose.
        data=json.loads(registered.read_text());ds_hinge,ds_open=data['hinge_native'],data['open_degrees']
    lines=['/* Generated handheld lid registration; MIT processing. */',
        'static const double ags_lid_hinge[]={'+','.join(f'{v*q:.9f}' for v in a['hinge_xyz_mm'])+'};',
        f'static const double ags_lid_open_radians={math.radians(a["open_degrees"]):.12f};',
        'static const double ds_lid_hinge[]={'+','.join(f'{v:.9f}' for v in ds_hinge)+'};',
        f'static const double ds_lid_open_radians={math.radians(ds_open):.12f};']
    (ROOT/'tools/slotlaunch/lid-data.h').write_text('\n'.join(lines)+'\n',newline='\n')

def closed_transform(name,q,scale):
    from mathutils import Vector,Matrix
    if name=='nds':
        a=dict(hinge_xyz_mm=[v/q for v in ds_lid.HINGE],open_degrees=ds_lid.OPEN_DEGREES)
    else:a=ags_spec()
    x,y,z=a['hinge_xyz_mm']
    h=Vector((x*q*scale,-z*q*scale,y*q*scale))
    return Matrix.Translation(h)@Matrix.Rotation(math.radians(a['open_degrees']),4,'X')@Matrix.Translation(-h)
