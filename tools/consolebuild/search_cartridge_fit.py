"""Measure candidate seat offsets; outputs diagnostics only (safe Blender, MIT)."""
import json
import math
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_selected_cartridges import load,crossing
import textured_blender as tb


def run(key):
    root=tb.ROOT;slot=root/'theme/art-book-slot/_slot'
    reg=json.loads((slot/'consoles'/key/'media-registration.json').read_text());q=reg['q'];cq=3.037594 if key=='nds' else q
    console=slot/'consoles'/key/'model.mesh'
    if key=='gba':console=slot/'local-models/consoles/gba/model.mesh'
    cp,cf=load(console,cq);mp,mf=load(slot/'consoles'/key/'media.mesh',q)
    case=BVHTree.FromPolygons(cp,cf,all_triangles=True,epsilon=0)
    if key=='gb':rotation=Matrix.Rotation(math.pi,3,'Y');seat=Vector((0,77.124143/q,-26.624431/q+3.9));out=Vector((0,1,0));travel=(193.39081-77.124143)/q;axis=2
    elif key=='gbc':rotation=Matrix.Rotation(math.pi,3,'Y');seat=Vector((0,70.888721/q,-16.127651/q+3.9));out=Vector((0,1,0));travel=(205.96564-70.888721)/q;axis=2
    elif key=='gba':rotation=Matrix.Rotation(math.pi/2,3,'X');seat=Vector((0,-26.03,24.45));out=Vector((0,0,1));travel=165.62309/2.7317073-24.45;axis=1
    else:
        rotation=Matrix.Rotation(math.pi,3,'Y')@Matrix.Rotation(math.pi/2,3,'X');seat=Vector((-28/cq,-65.175/cq,-113.29114/cq+17.5-1));out=Vector((0,0,-1));travel=38;axis=1
    base=[rotation@v for v in mp]
    def overlaps(offset,progress):
        shift=seat+out*travel*(1-progress);shift[axis]+=offset
        moved=[v+shift for v in base]
        pairs=case.overlap(BVHTree.FromPolygons(moved,mf,all_triangles=True,epsilon=0))
        if not pairs:return []
        aa=np.array([[cp[i] for i in cf[a]] for a,b in pairs]);bb=np.array([[moved[i] for i in mf[b]] for a,b in pairs])
        exact=crossing(aa,bb)|crossing(bb,aa)
        return [pair for pair,keep in zip(pairs,exact) if keep]
    rows=[]
    for offset in np.arange(-5,5.001,.125):
        pairs=overlaps(float(offset),1)
        rows.append(dict(offset=float(offset),seated_pairs=len(pairs)))
    candidates=sorted(rows,key=lambda r:(r['seated_pairs'],abs(r['offset'])))[:8]
    for row in candidates:
        counts=[len(overlaps(row['offset'],i/100)) for i in range(101)]
        row.update(max_feed_pairs=max(counts),feed_pairs=counts)
    result=dict(system=key,axis=axis,current_seat=list(seat),candidates=candidates,grid=rows,
        scope='Diagnostic only; zero collisions at an arbitrary offset does not establish a physically valid slot placement')
    dest=root/'build/cartridge-validation-20261019/fit-search';dest.mkdir(exist_ok=True)
    (dest/(key+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print('FIT',key,[(r['offset'],r['seated_pairs'],r['max_feed_pairs']) for r in candidates],flush=True)


if __name__=='__main__':
    for key in sys.argv[sys.argv.index('--')+1:]:run(key)
