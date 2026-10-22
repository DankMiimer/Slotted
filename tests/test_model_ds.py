"""Cianon's textured DS Lite: moving lid group, lid axis, folded clearance and screen anchors."""
import json,math,re,struct,unittest,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/consolebuild'))
from ds_lid import HOUSING_UNITS_PER_MM
from test_model_exemplars import gltf,bounds

NDS=ROOT/'theme/art-book-slot/_slot/consoles/nds'
REGISTRATION=json.loads((NDS/'registration.json').read_text())
HINGE=np.array(REGISTRATION['hinge_native'])
OPEN_DEGREES=REGISTRATION['open_degrees']


def native():
    raw=(NDS/'model.mesh').read_bytes()
    _,n,count,door=struct.unpack_from('<8sIII',raw)
    points=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)[:,:3].astype(float).copy()
    indices=np.frombuffer(raw,'<u2',count,20+n*36)
    return points,indices,door


def folded():
    p,i,d=native();j=np.unique(i[d:]);v=p[j]-HINGE;t=np.radians(OPEN_DEGREES)
    rot=np.array(((1,0,0),(0,np.cos(t),-np.sin(t)),(0,np.sin(t),np.cos(t))))
    p[j]=v@rot.T+HINGE
    return p,j


class DSLiteModel(unittest.TestCase):
    def test_moving_group_is_the_lid_and_its_screen_only(self):
        nodes=[n for n in gltf('nds')['nodes'] if 'mesh' in n]
        moving={n['name'] for n in nodes if n['extras']['hinged']}
        self.assertEqual(moving,{'DS Lite upper housing','Top LCD'})
        for name in ('DS Lite lower housing','Bottom LCD','DS Slot-1 mouth'):
            self.assertIn(name,{n['name'] for n in nodes})
            self.assertNotIn(name,moving)
        p,i,d=native()
        self.assertEqual(len(i)-d,232*3)            # the source lid, screen included
        self.assertEqual(REGISTRATION['source_triangles'],1186)
        self.assertEqual(len(i)//3,1158+12)         # all but the invisible glass, plus the mouth box

    def test_runtime_hinge_matches_the_registered_lid_knuckle_axis(self):
        text=(ROOT/'tools/slotlaunch/lid-data.h').read_text()
        hinge=[float(v) for v in re.search(r'ds_lid_hinge\[\]=\{([^}]*)\}',text).group(1).split(',')]
        np.testing.assert_allclose(hinge,HINGE,atol=1e-6)
        opened=float(re.search(r'ds_lid_open_radians=([0-9.]+);',text).group(1))
        self.assertAlmostEqual(math.degrees(opened),OPEN_DEGREES,places=6)
        # Source pose is 125 degrees; the accepted 145-degree presentation is a rotation about the same axis.
        self.assertAlmostEqual(REGISTRATION['source_open_degrees'],125.0,delta=.05)
        self.assertIn('knuckle',REGISTRATION['hinge_basis'])
        self.assertEqual(HINGE[0],0)

    def test_scale_screens_and_folded_height_follow_the_published_anchors(self):
        q=HOUSING_UNITS_PER_MM
        self.assertAlmostEqual(REGISTRATION['native_units_per_mm'],q)
        p,i,d=native();body=p[np.unique(i[:d])]
        self.assertAlmostEqual(np.ptp(body[:,0])/q,133.0,delta=.4)       # published closed width
        self.assertAlmostEqual(REGISTRATION['source_size_mm'][0],133.0,delta=.01)
        lo,hi=bounds(gltf('nds'),'Bottom LCD')
        width,height=((hi-lo)[[0,2]]*100/q)
        self.assertAlmostEqual(width/height,4/3,delta=.01)
        self.assertAlmostEqual(width,61.4,delta=1.5);self.assertAlmostEqual(height,46.1,delta=1.5)
        lo,hi=bounds(gltf('nds'),'Top LCD');top=(hi-lo)*100/q
        self.assertAlmostEqual(top[0],61.4,delta=1.5)             # the source's two panels differ by 2 %
        # The source is about 12 % thicker folded than Nintendo's 21.5 mm anchor: recorded, not corrected.
        folded_points,_=folded()
        height_mm=np.ptp(folded_points[:,1])/q
        self.assertTrue(21.5<height_mm<25.0,height_mm)
        for stem in ('model','model-master','model-physical'):
            g=gltf('nds',stem);extras=g['scenes'][g['scene']]['extras']
            self.assertAlmostEqual(extras['slotters_native_units_per_mm'],q)
            self.assertFalse(g.get('images'));self.assertFalse(g.get('textures'))

    def test_lid_clears_the_deck_when_folded(self):
        q=HOUSING_UNITS_PER_MM
        p,i,d=native();fixed=p[np.unique(i[:d])];f,j=folded();lid=f[j]
        # Source hinge end tabs overlap the body's end barrels by design; the
        # central screen area, away from the barrels and keys, must clear.
        fx=(np.abs(fixed[:,0])<35*q)&(fixed[:,2]>-20*q);lx=(np.abs(lid[:,0])<35*q)&(lid[:,2]>-20*q)
        self.assertTrue(fx.any() and lx.any())
        self.assertGreater((lid[lx,1].min()-fixed[fx,1].max())/q,1.0)

    def test_slot_mouth_sits_on_the_registered_card_path(self):
        q=HOUSING_UNITS_PER_MM
        lo,hi=bounds(gltf('nds'),'DS Slot-1 mouth');lo,hi=lo*100,hi*100
        x,y=REGISTRATION['card_slot_native']
        self.assertAlmostEqual((lo[0]+hi[0])/2,x,delta=.05);self.assertAlmostEqual((lo[1]+hi[1])/2,y,delta=.05)
        self.assertAlmostEqual((hi[0]-lo[0])/q,35.0,delta=.05)       # opening wider than the 33 mm card
        ry=REGISTRATION['spec']['ry']
        self.assertTrue(-(ry+6)<lo[2]<-(ry-4),lo[2])                 # proud of the rear face by ~1 mm


if __name__=='__main__':unittest.main()
