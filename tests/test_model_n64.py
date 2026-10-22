"""NUS-001 envelope, widened bay and open slot, paint isolation, provenance, Game Pak."""
import json,struct,sys,unittest
import numpy as np
from tools.consolebuild.n64 import SPECS,COLORS,ENCLOSURE_PALETTES,BAY,bay_warp,FLAPS,flap_angle
from tests.test_model_snes import ROOT,SLOT,native,glb,part_bounds,top_hits,project
sys.path.insert(0,str(ROOT/'tools/consolebuild'))
import media  # noqa: E402

S=SPECS['n64']

class N64Model(unittest.TestCase):
    def test_physical_envelope_uses_one_uniform_scale(self):
        magic,v,i,door=native('n64');q=S['scale']
        self.assertEqual(magic,b'SCTOON2\0');self.assertLessEqual(len(v),65535);self.assertLess(door,len(i))
        self.assertLess(len(i)//3,15000)
        np.testing.assert_allclose(np.ptp(v[:,:3],axis=0)/q,S['size'],atol=.35)
        p=json.loads((SLOT/'consoles/specs.json').read_text())['n64'];self.assertEqual(p['yscale'],1)
        self.assertAlmostEqual(p['entry']/q,S['entry']);self.assertAlmostEqual(p['slot']/q,S['slot'])
        self.assertAlmostEqual(p['cart']/q,S['media'][0]);self.assertAlmostEqual(p['sink']/q,S['seat_depth'])
        self.assertAlmostEqual(media.SCALES['n64'],q)
        for stem in ('model-master','model-physical','media-master','media-physical'):
            g=glb(SLOT/'consoles/n64'/(stem+'.glb'));extras=g['scenes'][g['scene']]['extras']
            self.assertAlmostEqual(extras['slotters_native_units_per_mm'],q)

    def test_widened_slot_is_open_across_the_game_pak(self):
        _,v,i,door=native('n64');tri=(v[:,:3]/S['scale'])[i[:door]].reshape(-1,3,3)
        self.assertGreater(S['opening'][0],S['media'][0]+2)
        for x in (-S['media'][0]/2+.6,0,S['media'][0]/2-.6):
            for z in (S['slot']-8.5,S['slot'],S['slot']+8.5):
                hits=top_hits(tri,x,z)
                self.assertGreater(len(hits),0,'A real connector floor must remain')
                self.assertLess(hits.max(),S['entry']-S['seat_depth']-.5,(x,z,hits))

    def test_bay_warp_is_local_continuous_and_monotonic(self):
        xs=np.linspace(-7,7,1401)
        for y,z in ((3.0,-3.6),(2.6,-1.0),(1.0,-3.6),(3.0,1.0)):
            out=np.array([bay_warp(x,y,z) for x in xs])
            self.assertTrue(np.all(np.diff(out)>0),(y,z))
            np.testing.assert_allclose(out[np.abs(xs)>=BAY['outer']],xs[np.abs(xs)>=BAY['outer']])
        self.assertEqual(bay_warp(2.0,1.0,-3.6),2.0)   # rear connectors below the ramp
        self.assertEqual(bay_warp(2.0,3.0,1.0),2.0)    # expansion door in front of it

    def test_paint_never_reaches_controls_ports_or_badge(self):
        _,v,_,_=native('n64');weights=np.frombuffer((SLOT/'consoles/n64/paint.mask').read_bytes(),'uint8',offset=20)
        eligible=np.any([np.max(np.abs(v[:,6:9]-COLORS[p]),axis=1)<.005 for p in ENCLOSURE_PALETTES['n64']],axis=0)
        self.assertTrue(np.all(eligible[weights>0]));self.assertGreater(np.count_nonzero(weights),100)
        self.assertGreater(np.count_nonzero(~eligible),100)

    def test_source_is_image_free_licensed_and_credited(self):
        credits=(SLOT/'MODEL_CREDITS.txt').read_text();folder=ROOT/'third_party/models'/S['creator']
        source=json.loads((folder/'source.json').read_text())
        self.assertEqual(source['licence'],'CC-BY-4.0');self.assertIn(source['url'],credits)
        for key in ('source_file_sha256','archive_sha256'):self.assertRegex(source[key],r'^[0-9a-f]{64}$')
        g=glb(folder/'model.glb');self.assertFalse(g.get('images'));self.assertFalse(g.get('textures'))
        for mesh in g['meshes']:
            for primitive in mesh['primitives']:self.assertNotIn('TEXCOORD_0',primitive['attributes'])
        names={n['name'] for n in g['nodes'] if 'mesh' in n}
        # The two actual source leaves are now separate moving parts; extras go.
        self.assertTrue(set(FLAPS)<=names)
        self.assertFalse({n for n in names if n.split('.')[0] in
            ('slot_cover_1','slot_cover_2','Controller_main','wire','cartridge')})
        self.assertTrue(all(n.startswith('N64 ') for n in names),names)
        bounds=part_bounds(g)['N64 upper enclosure']*1000
        np.testing.assert_allclose(np.ptp(bounds,axis=0)[[0,2]],(260,190),atol=.5)

    def test_leaf_ranges_and_contact_follow_the_cartridge(self):
        info=json.loads((SLOT/'consoles/n64/mesh-info.json').read_text())
        source=json.loads((ROOT/'third_party/models/josephrohm-n64/source.json').read_text())
        _,v,i,door=native('n64');ranges=info['moving_parts']
        self.assertEqual(set(ranges),set(FLAPS))
        self.assertEqual(sum(r['count'] for r in ranges.values()),len(i)-door)
        for name in FLAPS:
            f=source['flaps'][name];r=ranges[name]
            self.assertGreaterEqual(r['first'],door);self.assertLessEqual(r['first']+r['count'],len(i))
            angles=[flap_angle(f['profile_yz_mm'],f['hinge_yz_mm'],f['side'],bottom,9.25)
                    for bottom in np.linspace(S['entry']+36.7,S['entry']-27,101)]
            self.assertEqual(angles[0],0)
            self.assertTrue(np.all(np.diff(np.abs(angles))>=-1e-8))
            self.assertGreater(abs(angles[-1]),np.radians(65));self.assertLess(abs(angles[-1]),np.radians(85))
            self.assertGreater(-f['side']*angles[-1],0,'Leaves open downwards away from the centre')

    def test_loaded_console_and_aligned_hover_fit_the_viewport(self):
        _,v,_,_=native('n64');case=v[:,:3]
        raw=(SLOT/'consoles/n64/media.mesh').read_bytes();n=struct.unpack_from('<I',raw,8)[0]
        cart=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)[:,:3].copy()
        cart[:,1]+=(S['media'][1]/2+S['entry'])*S['scale']+55;cart[:,2]+=S['slot']*S['scale']
        self.assertGreater(project(cart,-22).min()+S['origin'],8)
        self.assertLess(max(project(case,yaw).max() for yaw in (-8,-22))+S['origin'],472)

    def test_game_pak_label_recess_fills_the_central_panel(self):
        # NUS-006: the label recess spans nearly the panel between the parting
        # lines (x = 70.5 and 289.5 on the 360-pixel, 116-mm shelf drawing).
        (x0,y0,x1,y1),_=media.WELLS['n64'];mm=116/360
        self.assertGreater(x0,70.5+1.4);self.assertLess(x1,289.5-1.4)
        self.assertGreater((x1-x0)*mm,64);self.assertGreater((y1-y0)*76.6/241,58)

if __name__=='__main__':unittest.main()
