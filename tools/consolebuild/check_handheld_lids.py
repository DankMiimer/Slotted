"""Independent native-triangle lid sweeps. Blender 4.5, MIT."""
import json,math,struct
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]


def ease(t):
    t=max(0,min(1,t));return t*t*(3-2*t)


def check(system,q,hinge,angle):
    raw=(ROOT/'theme/art-book-slot/_slot/consoles'/system/'model.mesh').read_bytes()
    _,n,count,door=struct.unpack_from('<8sIII',raw)
    data=struct.unpack_from('<%df'%(n*9),raw,20)
    points=[Vector(tuple(v/q for v in data[i:i+3])) for i in range(0,n*9,9)]
    indices=struct.unpack_from('<%dH'%count,raw,20+n*36)
    fixed=[tuple(indices[i:i+3]) for i in range(0,door,3)]
    moving=[tuple(indices[i:i+3]) for i in range(door,count,3)]
    assert fixed and moving
    case=BVHTree.FromPolygons(points,fixed,all_triangles=True,epsilon=0)
    h=Vector(hinge);rows=[]
    for i in range(101):
        opened=i/100;rot=Matrix.Rotation(angle*(1-opened),3,'X')
        moved=[h+rot@(p-h) for p in points]
        if i==0:closed=moved
        pairs=case.overlap(BVHTree.FromPolygons(moved,moving,all_triangles=True,epsilon=0))
        centres=[list(sum((moved[k] for k in moving[b]),Vector())/3) for a,b in pairs]
        rows.append(dict(opened=opened,pairs=len(pairs),centres_mm=centres[:20]))
    down=[p+Vector((0,-5,0)) for p in closed]
    positive=len(case.overlap(BVHTree.FromPolygons(down,moving,all_triangles=True,epsilon=0)))
    raw=(ROOT/'theme/art-book-slot/_slot/consoles'/system/'media.mesh').read_bytes()
    _,nv,ni,_=struct.unpack_from('<8sIII',raw);v=struct.unpack_from('<%df'%(nv*9),raw,20)
    mp=[Vector(tuple(a/q for a in v[i:i+3])) for i in range(0,nv*9,9)]
    ix=struct.unpack_from('<%dH'%ni,raw,20+nv*36);mf=[tuple(ix[i:i+3]) for i in range(0,ni,3)]
    feed=[]
    # Fully aligned native feed while the independent lid starts to close.
    # Withdrawal traverses the same rigid card poses; the hinge sweep above
    # also checks the entire open/closed interval, without bearing exclusions.
    for i in range(101):
        start=.38 if system=='gba' else .73
        time=start+(1-start)*i/100
        opened=ease((time-.10)/.20)*(1-ease((time-.82)/.10))
        rot=Matrix.Rotation(angle*(1-opened),3,'X');posed=[h+rot@(p-h) for p in points]
        if system=='gba':
            move=ease((time-.34)/.44)
            centre=62.8446428571+(24.45-62.8446428571)*move
            cart=[Vector((p.x,-p.z-26.03,p.y+centre)) for p in mp]
        else:
            move=ease((time-.74)/.13);half=35*2.75/2
            centre=-114-half-18+(((-114+half-3)-(-114-half-18))*move)
            centre+=3*ease((time-.86)/.025)*(1-ease((time-.895)/.025))
            cart=[Vector((-28/q-p.x,(-70.4+3.8*2.75/2)/q-p.z,centre/q-p.y)) for p in mp]
        leaf=BVHTree.FromPolygons(posed,moving,all_triangles=True,epsilon=0)
        card=BVHTree.FromPolygons(cart,mf,all_triangles=True,epsilon=0)
        feed.append(dict(time=time,body_pairs=len(case.overlap(card)),lid_pairs=len(leaf.overlap(card))))
    return dict(samples=rows,maximum_pairs=max(r['pairs'] for r in rows),positive_control=positive,
                closing_feed_samples=feed,maximum_feed_pairs=max(r['body_pairs']+r['lid_pairs'] for r in feed))


def main():
    a=json.loads((ROOT/'third_party/models/thegraphicsgeek-ags/source.json').read_text())['lid']
    import sys
    sys.path.insert(0,str(ROOT/'tools/consolebuild'))
    from ds_lid import HINGE,OPEN_DEGREES,HOUSING_UNITS_PER_MM
    q=HOUSING_UNITS_PER_MM
    result={'gba':check('gba',224/82,a['hinge_xyz_mm'],math.radians(a['open_degrees'])),
            'nds':check('nds',q,[v/q for v in HINGE],math.radians(OPEN_DEGREES))}
    out=ROOT/'build/handheld-lids/lid-clearance.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({s:{k:v for k,v in r.items() if k not in ('samples','closing_feed_samples')} for s,r in result.items()}),flush=True)
    assert all(r['maximum_pairs']==0 and r['maximum_feed_pairs']==0 and r['positive_control']>0 for r in result.values())


if __name__=='__main__':main()
