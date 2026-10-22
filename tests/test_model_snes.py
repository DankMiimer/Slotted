"""Exported SNES envelopes, open slots, landmark preservation and paint isolation."""
import json,struct,unittest
from pathlib import Path
import numpy as np
from tools.consolebuild.snes import SPECS,COLORS,ENCLOSURE_PALETTES

ROOT=Path(__file__).resolve().parents[1]
SLOT=ROOT/'theme/art-book-slot/_slot'

def native(name):
    raw=(SLOT/'consoles'/name/'model.mesh').read_bytes()
    magic,n,count,door=struct.unpack_from('<8sIII',raw)
    v=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)
    indices=np.frombuffer(raw,'<u2',count,20+n*36)
    return magic,v,indices,door

def glb(path):
    raw=path.read_bytes();n=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+n])

def part_bounds(g):
    result={}
    for node in g['nodes']:
        if 'mesh' not in node:continue
        pairs=[]
        for primitive in g['meshes'][node['mesh']]['primitives']:
            a=g['accessors'][primitive['attributes']['POSITION']]
            pairs.append((a['min'],a['max']))
        result[node['name']]=np.array((np.min([p[0] for p in pairs],axis=0),np.max([p[1] for p in pairs],axis=0)))
    return result

def top_hits(triangles,x,z):
    # Vertical rays through the actual native triangles, independent of booleans.
    a=triangles[:,0,[0,2]];b=triangles[:,1,[0,2]]-a;c=triangles[:,2,[0,2]]-a
    p=np.array((x,z))-a;area=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid=np.abs(area)>1e-8;b,c,p,area=b[valid],c[valid],p[valid],area[valid]
    u=(p[:,0]*c[:,1]-p[:,1]*c[:,0])/area;v=(b[:,0]*p[:,1]-b[:,1]*p[:,0])/area
    inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
    h=triangles[valid,:,1]
    return (h[:,0]+u*(h[:,1]-h[:,0])+v*(h[:,2]-h[:,0]))[inside]

def project(points,yaw):
    a=np.radians(yaw);p=points.copy();x=p[:,0].copy();z=p[:,2].copy()
    p[:,0]=x*np.cos(a)+z*np.sin(a);p[:,2]=-x*np.sin(a)+z*np.cos(a)
    phi=np.radians(35);k=1200/(1200-p[:,1]*np.sin(phi)-p[:,2]*np.cos(phi))
    return (p[:,2]*np.sin(phi)-p[:,1]*np.cos(phi))*k

class SnesModels(unittest.TestCase):
    def test_physical_envelopes_use_one_uniform_scale(self):
        packaged=json.loads((SLOT/'consoles/specs.json').read_text())
        for name,s in SPECS.items():
            with self.subTest(name=name):
                magic,v,i,door=native(name);q=s['scale']
                self.assertEqual(magic,b'SCTOON2\0');self.assertLessEqual(len(v),65535)
                info=json.loads((SLOT/'consoles'/name/'mesh-info.json').read_text())
                self.assertLess(len(i)//3,info['triangle_limit']);self.assertEqual(door,len(i))
                np.testing.assert_allclose(np.ptp(v[:,:3],axis=0)/q,s['size'],atol=.35)
                p=packaged[name];self.assertEqual(p['yscale'],1)
                self.assertAlmostEqual(p['entry']/q,s['entry']);self.assertAlmostEqual(p['slot']/q,s['slot'])
                self.assertAlmostEqual(p['cart']/q,s['media'][0]);self.assertAlmostEqual(p['sink']/q,s['seat_depth'])
                for stem in ('model-master','model-physical','media-master','media-physical'):
                    g=glb(SLOT/'consoles'/name/(stem+'.glb'))
                    extras=g['scenes'][g['scene']]['extras']
                    self.assertAlmostEqual(extras['slotters_native_units_per_mm'],q)
                    self.assertAlmostEqual(extras['slotters_glb_to_metres'],1 if stem.endswith('physical') else 1/(10*q))

    def test_real_slot_is_open_above_the_connector_floor(self):
        for name,s in SPECS.items():
            with self.subTest(name=name):
                _,v,i,_=native(name);tri=(v[:,:3]/s['scale'])[i].reshape(-1,3,3)
                for x in (-s['media'][0]/2+.6,0,s['media'][0]/2-.6):
                    for z in (s['slot']-9.5,s['slot'],s['slot']+9.5):
                        hits=top_hits(tri,x,z)
                        self.assertGreater(len(hits),0,'A real connector floor must remain')
                        self.assertLess(hits.max(),s['entry']-s['seat_depth']-.5,(name,x,z,hits))

    def test_runtime_retains_source_landmark_envelopes(self):
        for name,s in SPECS.items():
            folder=SLOT/'consoles'/name
            master=part_bounds(glb(folder/'model-master.glb'));runtime=part_bounds(glb(folder/'model.glb'))
            parts=('PAL upper enclosure','PAL inset panel','PAL power slider','PAL reset button') if name=='snes' else ('US upper enclosure','US lower enclosure','US power slider','US reset button')
            for part in parts:
                with self.subTest(name=name,part=part):
                    np.testing.assert_allclose(runtime[part]*100/s['scale'],master[part]*100/s['scale'],atol=.35)

    def test_us_controls_are_whole_source_mouldings(self):
        # Prepared parts are metres, x right/y up/z front. Triangle-centre boxes
        # once left switch ends on the housing, coloured the whole rear wall and
        # front port blocks, and floated a text patch 2.5 mm above the lever.
        bounds={k:v*1000 for k,v in part_bounds(glb(ROOT/'third_party/models/ibbqcats-snes/model.glb')).items()}
        span=lambda part:np.ptp(bounds[part],axis=0)
        for part in ('US power slider','US reset button'):
            with self.subTest(part=part):np.testing.assert_allclose(span(part),(57.44,5.88,20.28),atol=.3)
        self.assertEqual(COLORS['uspower'],COLORS['usreset'])
        np.testing.assert_allclose(span('US eject lever'),(35.26,2.15,58.55),atol=.3)
        self.assertLess(bounds['US eject lever'][1][1],bounds['US power slider'][0][1]+.5)
        self.assertLess(span('US controller sockets')[1],11)
        self.assertLess(span('US rear connectors')[0],62)

    def test_paint_never_reaches_controls_contacts_or_printing(self):
        for name in SPECS:
            _,v,_,_=native(name);mask=(SLOT/'consoles'/name/'paint.mask').read_bytes()
            weights=np.frombuffer(mask,'uint8',offset=20);colours=v[:,6:9]
            eligible=np.any([np.max(np.abs(colours-COLORS[p]),axis=1)<.005 for p in ENCLOSURE_PALETTES[name]],axis=0)
            self.assertTrue(np.all(eligible[weights>0]))
            self.assertGreater(np.count_nonzero(weights),100)
            self.assertGreater(np.count_nonzero(~eligible),100)

    def test_source_is_image_free_licensed_and_identifiable(self):
        credits=(SLOT/'MODEL_CREDITS.txt').read_text()
        for name,s in SPECS.items():
            folder=ROOT/'third_party/models'/s['creator'];source=json.loads((folder/'source.json').read_text())
            self.assertEqual(source['licence'],'CC-BY-4.0')
            for key in ('source_file_sha256','archive_sha256'):self.assertRegex(source[key],r'^[0-9a-f]{64}$')
            self.assertIn(source['url'],credits)
            g=glb(folder/'model.glb');self.assertFalse(g.get('images'));self.assertFalse(g.get('textures'))
            for mesh in g['meshes']:
                for primitive in mesh['primitives']:self.assertNotIn('TEXCOORD_0',primitive['attributes'])
            self.assertTrue(all(n['extras']['source_licence']=='CC-BY-4.0' for n in g['nodes'] if 'mesh' in n))

    def test_loaded_console_and_aligned_hover_fit_the_viewport(self):
        for name,s in SPECS.items():
            _,v,_,_=native(name);case=v[:,:3]
            raw=(SLOT/'consoles'/name/'media.mesh').read_bytes();n=struct.unpack_from('<I',raw,8)[0]
            cart=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)[:,:3].copy()
            cart[:,1]+=(s['media'][1]/2+s['entry'])*s['scale']+55
            cart[:,2]+=s['slot']*s['scale']
            self.assertGreater(project(cart,-22).min()+s['origin'],8)
            self.assertLess(max(project(case,yaw).max() for yaw in (-8,-22))+s['origin'],472)

if __name__=='__main__':unittest.main()
