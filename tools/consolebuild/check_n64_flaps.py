"""Independent native-triangle checks for N64 cartridge and both spring doors."""
import json,math,struct,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from n64 import SPECS,FLAPS,flap_angle

def read(stem,q):
    raw=(ROOT/'theme/art-book-slot/_slot/consoles/n64'/(stem+'.mesh')).read_bytes()
    _,n,count,door=struct.unpack_from('<8sIII',raw)
    values=struct.unpack_from('<%df'%(n*9),raw,20)
    points=[Vector(tuple(x/q for x in values[i:i+3])) for i in range(0,len(values),9)]
    indices=struct.unpack_from('<%dH'%count,raw,20+n*36)
    return points,[tuple(indices[i:i+3]) for i in range(0,count,3)],door//3

def tree(p,f):return BVHTree.FromPolygons(p,f,all_triangles=True,epsilon=0)

def main():
    spec=SPECS['n64'];q=spec['scale'];cp,cf,door=read('model',q);mp,mf,_=read('media',q)
    source=json.loads((ROOT/'third_party/models/josephrohm-n64/source.json').read_text())
    info=json.loads((ROOT/'theme/art-book-slot/_slot/consoles/n64/mesh-info.json').read_text())
    housing=tree(cp,cf[:door]);rows=[];controls=[]
    for step in range(101):
        move=step/100;bottom=spec['entry']+55/q-(spec['seat_depth']+55/q)*move
        cart=[p+Vector((0,bottom+spec['media'][1]/2,spec['slot'])) for p in mp]
        pak=tree(cart,mf);row=dict(move=move,cart_body_pairs=len(housing.overlap(pak)),leaves={})
        for name in FLAPS:
            f=source['flaps'][name];r=info['moving_parts'][name]
            faces=cf[r['first']//3:(r['first']+r['count'])//3]
            angle=flap_angle(f['profile_yz_mm'],f['hinge_yz_mm'],f['side'],bottom,spec['media'][2]/2)
            hy,hz=f['hinge_yz_mm'];c,s=math.cos(angle),math.sin(angle)
            posed=[Vector((p.x,hy+(p.y-hy)*c-(p.z-hz)*s,hz+(p.y-hy)*s+(p.z-hz)*c)) for p in cp]
            leaf=tree(posed,faces);body_pairs=housing.overlap(leaf);cart_pairs=pak.overlap(leaf)
            report=dict(degrees=math.degrees(angle),cart_pairs=len(cart_pairs),body_pairs=len(body_pairs))
            if body_pairs:report['body_centres']=[list(sum((cp[k] for k in cf[a]),Vector())/3) for a,b in body_pairs[:8]]
            row['leaves'][name]=report
            if step==100:
                # A deliberately closed leaf intersects a fully seated cart.
                controls.append(len(pak.overlap(tree(cp,faces))))
        rows.append(row)
    out=ROOT/'build/n64-flaps';out.mkdir(parents=True,exist_ok=True)
    result=dict(samples=rows,closed_leaf_positive_control_pairs=controls)
    (out/'clearance.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    summary=dict(max_cart_body=max(r['cart_body_pairs'] for r in rows),
        max_cart_leaf=max(f['cart_pairs'] for r in rows for f in r['leaves'].values()),
        max_body_leaf=max(f['body_pairs'] for r in rows for f in r['leaves'].values()),positive=controls)
    print(json.dumps(summary),flush=True)
    assert all(controls),'Missing closed-leaf positive controls'
    assert not any(summary[k] for k in ('max_cart_body','max_cart_leaf','max_body_leaf')),'Inspect build/n64-flaps/clearance.json'

if __name__=='__main__':main()
