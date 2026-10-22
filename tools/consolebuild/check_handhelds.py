"""Independent exported-triangle feed checks. Run with Blender 4.5 (MIT)."""
import struct,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]

def read(system,stem,q):
    data=(ROOT/'theme/art-book-slot/_slot/consoles'/system/(stem+'.mesh')).read_bytes()
    _,n,count,_=struct.unpack_from('<8sIII',data)
    vertices=struct.unpack_from('<%df'%(n*9),data,20)
    points=[Vector(tuple(v/q for v in vertices[i:i+3])) for i in range(0,n*9,9)]
    indices=struct.unpack_from('<%dH'%count,data,20+n*36)
    # Include every triangle: short normals can identify either printing OR a
    # physical housing that suppresses hull expansion. Excluding them would
    # silently omit the main CGB wall and the AGS receiving floor.
    faces=[tuple(indices[i:i+3]) for i in range(0,count,3)]
    return points,faces

def bvh(points,faces):return BVHTree.FromPolygons(points,faces,all_triangles=True,epsilon=0)
def ease(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def main():
    report={}
    # GB-compatible (notched) carts in a CGB are the DMG Game Pak mesh, in mm.
    for system,q,media in (('gbc',168/78,('gbc',168/78)),('gba',224/82,('gba',224/82)),
                           ('gbc-compatible',168/78,('gb',168/90))):
        console=system.split('-')[0]
        cp,cf=read(console,'model',q);mp,mf=read(media[0],'media',media[1]);case=bvh(cp,cf)
        rows=[]
        for i in range(101):
            travel=i/100
            if console=='gbc':
                # Final rear-facing basis, after the presentation turn.
                centre=96.7142857143+(34-96.7142857143)*travel
                moved=[Vector((-p.x,p.y+centre,-p.z-2.6)) for p in mp]
            else:
                centre=62.8446428571+(24.45-62.8446428571)*travel
                # Nintendo AGS manual illustration 4: label faces down (-Y),
                # connector edge (local -Y) leads into the front slot (-Z).
                moved=[Vector((p.x,-p.z-26.03,p.y+centre)) for p in mp]
            pairs=case.overlap(bvh(moved,mf))
            row={'travel':travel,'intersecting_triangle_pairs':len(pairs)}
            if pairs:row['case_collision_centres_mm']=[list(sum((cp[k] for k in cf[a]),Vector())/3) for a,b in pairs[:12]]
            rows.append(row)
        control=[p+Vector((25,0,0)) for p in moved]
        positive=len(case.overlap(bvh(control,mf)))
        assert positive>0,'Missing collision positive control'
        report[system]={'feed_and_reverse_samples':101,'samples':rows,
                        'collision_positive_control_pairs':positive,
                        'scope':'Exported native triangles after alignment; reversing visits the same rigid poses. Coplanar contact reported, not hidden.'}
    out=ROOT/'build/exemplars/clearance.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({s:dict(max_pairs=max(x['intersecting_triangle_pairs'] for x in r['samples']),positive=r['collision_positive_control_pairs']) for s,r in report.items()}))
    assert all(max(x['intersecting_triangle_pairs'] for x in r['samples'])==0 for r in report.values()),'Feed intersects housing; inspect clearance.json'

if __name__=='__main__':main()
