"""Independent triangle/triangle clearance of selected handheld cards (Blender).

Uses recorded native seat registers and actual console meshes. Does not change
models, layouts or the device. Full rigid alignment/feed and reverse sampled.
"""
import json
import math
import struct
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import textured_blender as tb


def load(path,q):
    raw=path.read_bytes();magic,n,count,_=struct.unpack_from('<8sIII',raw)
    assert magic==b'SCTOON2\0'
    points=[Vector([v/q for v in struct.unpack_from('<3f',raw,20+i*36)]) for i in range(n)]
    ix=struct.unpack_from('<%dH'%count,raw,20+n*36)
    return points,[tuple(ix[i:i+3]) for i in range(0,count,3)]


def crossing(a,b):
    """Narrow phase: non-coplanar edge/triangle intersections, not BVH boxes."""
    edge0=a[:,1]-a[:,0];edge1=a[:,2]-a[:,0]
    norm=np.cross(edge0,edge1)
    d00=np.sum(edge0*edge0,axis=1);d01=np.sum(edge0*edge1,axis=1);d11=np.sum(edge1*edge1,axis=1)
    det=d00*d11-d01*d01
    result=np.zeros(len(a),bool)
    for i in range(3):
        start=b[:,i];end=b[:,(i+1)%3];line=end-start
        denom=np.sum(norm*line,axis=1)
        ok=(abs(denom)>1e-8)&(abs(det)>1e-12)
        t=np.divide(np.sum(norm*(a[:,0]-start),axis=1),denom,out=np.full(len(a),-1.),where=ok)
        hit=start+t[:,None]*line-a[:,0]
        d20=np.sum(hit*edge0,axis=1);d21=np.sum(hit*edge1,axis=1)
        u=np.divide(d11*d20-d01*d21,det,out=np.zeros(len(a)),where=ok)
        v=np.divide(d00*d21-d01*d20,det,out=np.zeros(len(a)),where=ok)
        result |= ok&(t>1e-5)&(t<1-1e-5)&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
    return result


def run(key):
    root=tb.ROOT;slot=root/'theme/art-book-slot/_slot'
    reg=json.loads((root/'build/selected-cartridges'/key/'registration.json').read_text())
    package=slot/'cartridges/models'/key/reg['uid']
    q=reg['q'];cq=3.037594 if key=='nds' else q
    console=slot/'consoles'/key/'model.mesh'
    if key=='gba' and (slot/'local-models/consoles/gba/model.mesh').exists():
        console=slot/'local-models/consoles/gba/model.mesh'
    cp,cf=load(console,cq);p,f=load(package/'media.mesh',q)
    case=BVHTree.FromPolygons(cp,cf,all_triangles=True,epsilon=0)
    if key=='gb':
        rotation=Matrix.Rotation(math.pi,3,'Y');seat=Vector((0,77.124143/q,-26.624431/q+3.9));out=Vector((0,1,0));travel=(193.39081-77.124143)/q
    elif key=='gbc':
        rotation=Matrix.Rotation(math.pi,3,'Y');seat=Vector((0,70.888721/q,-16.127651/q+3.9));out=Vector((0,1,0));travel=(205.96564-70.888721)/q
    elif key=='gba':
        rotation=Matrix.Rotation(math.pi/2,3,'X');seat=Vector((0,-26.03,24.45));out=Vector((0,0,1));travel=165.62309/2.7317073-24.45
    else:
        rotation=Matrix.Rotation(math.pi,3,'Y')@Matrix.Rotation(math.pi/2,3,'X')
        seat=Vector((-28/cq,-65.175/cq,-113.29114/cq+17.5-1));out=Vector((0,0,-1));travel=38
    def sample(points,faces):
        rows=[]
        for i in range(101):
            t=i/100;offset=seat+out*travel*(1-t)
            moved=[rotation@v+offset for v in points]
            pairs=case.overlap(BVHTree.FromPolygons(moved,faces,all_triangles=True,epsilon=0))
            broad=len(pairs)
            if pairs:
                aa=np.array([[cp[k] for k in cf[a]] for a,b in pairs]);bb=np.array([[moved[k] for k in faces[b]] for a,b in pairs])
                exact=crossing(aa,bb)|crossing(bb,aa)
                pairs=[pair for pair,keep in zip(pairs,exact) if keep]
            rows.append(dict(progress=t,pairs=len(pairs),broad_phase_pairs=broad,examples=[dict(console_triangle=a,card_triangle=b,
                centre=list(sum((cp[k] for k in cf[a]),Vector())/3)) for a,b in pairs[:5]]))
        return rows
    rows=sample(p,f)
    before=root/'build/cartridge-implementation-20261019/before/theme/art-book-slot/_slot/consoles'/key/'media.mesh'
    baseline=sample(*load(before,q))
    result=dict(system=key,console=str(console.relative_to(root)),console_sha256=tb.sha256(console),
        cartridge_sha256=tb.sha256(package/'media.mesh'),q=q,console_q=cq,
        max_pairs=max(r['pairs'] for r in rows),samples=rows,
        baseline_max_pairs=max(r['pairs'] for r in baseline),baseline=baseline,
        limitation='Raw geometry only; shared-depth concealment is not counted as physical clearance')
    dest=root/'build/cartridge-implementation-20261019/clearance';dest.mkdir(exist_ok=True)
    (dest/(key+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print('CLEARANCE',key,result['max_pairs'],'baseline',result['baseline_max_pairs'],flush=True)


if __name__=='__main__':
    for key in sys.argv[sys.argv.index('--')+1:]:run(key)
