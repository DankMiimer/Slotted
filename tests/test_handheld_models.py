"""Measured CGB/AGS geometry and offline source contracts."""
import json,struct,unittest
from pathlib import Path
import numpy as np
from test_model_exemplars import gltf,bounds,triangles,ray_depths
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'theme/art-book-slot/_slot/consoles'


class NextHandheldModels(unittest.TestCase):
    def test_cgb_physical_housing_and_lcd(self):
        # BPoole's source, uniformly scaled from its own 57 mm Game Pak width:
        # the artist's proportions are kept rather than stretched to 133.5 mm.
        g=gltf('gbc');q=168/78
        lo,hi=bounds(g,'CGB housing')
        np.testing.assert_allclose((hi-lo)*100/q,(78.03,131.33,28.55),atol=.05)
        lo,hi=bounds(g,'CGB LCD glass')
        np.testing.assert_allclose((hi-lo)[:2]*100/q,(44.45,40.26),atol=.05)
        reg=json.loads((ASSETS/'gbc/registration.json').read_text())
        self.assertAlmostEqual(reg['mm_per_source_unit']*7.13645,57,delta=.01)
        self.assertEqual(reg['licence'],'CC-BY-4.0')

    def test_cgb_full_cart_has_clearance_above_and_below_lip(self):
        case=triangles('gbc','CGB housing','model');q=168/78
        reg=json.loads((ASSETS/'gbc/registration.json').read_text())
        lip=reg['spec']['slot']/q;rear=reg['cart_label_native']/q;front=rear+7.8
        for x in (-26,0,26):
            wall=np.unique(np.round(ray_depths(case,x,lip-2),4))
            # Rear wall hides the seated Game Pak with clearance on both faces.
            self.assertLess(wall[1],rear-.15);self.assertGreater(wall[2],front+.15)
        # Above the measured lip the back is open: the label is visible.
        self.assertGreater(ray_depths(case,0,lip+1).min(),front)

    def test_ags_bay_admits_the_registered_game_pak(self):
        # Rays run vertically (y swapped with z) through the real cavity of thegraphicsgeek's base.
        case=triangles('gba','SP lower housing','model')[:,:,[0,2,1]];q=224/82
        reg=json.loads((ASSETS/'gba/registration.json').read_text());bay=reg['bay']
        floor=-85.1/q+bay['floor_mm'];cart=bay['cart_centre_native']/q
        shell=json.loads((ASSETS/'gba/media-registration.json').read_text())['size_mm'][2]
        for depth in (10,20,35):
            values=np.unique(np.round(ray_depths(case,0,depth),3))
            if depth<=30:self.assertTrue(np.any(np.isclose(values,floor,atol=.06)),values)   # open at the mouth
            roof=values[(values>cart+shell/2)&(values<cart+shell/2+3.5)]
            self.assertTrue(len(roof) and roof.min()>cart+shell/2+.1,(values,cart+shell/2))   # roof clears the shell
            self.assertLess(floor,cart-shell/2-.2)                                              # and so does the floor
        self.assertGreater(bay['roof_raised_mm'],1.0)

    def test_runtime_budgets_and_complete_media(self):
        registered=json.loads((ASSETS/'gba/media-registration.json').read_text())
        for system,q,dim in (('gbc',168/78,(57,65.5,7.9781)),('gba',224/82,registered['size_mm'])):
            for stem in ('model','media'):
                raw=(ASSETS/system/(stem+'.mesh')).read_bytes()
                magic,n,count,door=struct.unpack_from('<8sIII',raw)
                # Textured sources keep every visible source part (no collapse).
                # GBA SP keeps all 66,784 visible triangles of thegraphicsgeek's source (device-timed).
                limit=70000 if system=='gba' and stem=='model' else 16000 if stem=='model' and (ASSETS/system/'model.texture').exists() else 15000
                self.assertEqual(magic,b'SCTOON2\0');self.assertLess(count//3,limit)
                self.assertLessEqual(n,65535)
                if stem=='media':
                    points=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)[:,:3]/q
                    np.testing.assert_allclose(np.ptp(points,axis=0),dim,atol=.025)

    def test_gba_print_has_a_real_recess_and_preserves_crop_aspect(self):
        shell=triangles('gba','Cartridge_geo','media')
        self.assertGreater(ray_depths(shell,26,-2).max(),ray_depths(shell,0,-2).max()+.1)
        raw=(ASSETS/'gba/media-label.mesh').read_bytes();n=struct.unpack_from('<I',raw,8)[0]
        sticker=np.frombuffer(raw,'<f4',n*9,20).reshape(-1,9)[:,:3]/(224/82)
        self.assertLess(abs(sticker[:,0]).max(),22.2)
        self.assertLess(abs(sticker[:,1]+2).max(),12.1)
        # The selected artist's well is retained (no aspect stretch to the older
        # Vxcl mesh); its print aspect stays within 5% of the established crop.
        self.assertAlmostEqual(np.ptp(sticker[:,0])/np.ptp(sticker[:,1]),260/135,delta=.1)

    def test_image_free_offline_sources_and_editable_units(self):
        for system,q in (('gbc',168/78),('gba',224/82)):
            for stem in ('model','media','model-master','media-master','model-physical','media-physical'):
                g=gltf(system,stem);self.assertFalse(g.get('images'))
                extras=g['scenes'][g['scene']]['extras']
                self.assertAlmostEqual(extras['slotters_native_units_per_mm'],q)
                self.assertAlmostEqual(extras['slotters_glb_to_metres'],1 if stem.endswith('physical') else 1/(10*q))
                for mesh in g['meshes']:
                    self.assertTrue(all('TEXCOORD_0' not in p['attributes'] for p in mesh['primitives']))
        source=json.loads((ROOT/'third_party/models/bpoole-cgb/source.json').read_text())
        self.assertEqual(source['licence'],'CC-BY-4.0');self.assertEqual(len(source['source_sha256']),64)
        for family in ('wikiti-cgb','thegraphicsgeek-ags','dave-gba'):
            g=ROOT/'third_party/models'/family/'model.glb';raw=g.read_bytes()
            doc=json.loads(raw[20:20+struct.unpack_from('<I',raw,12)[0]])
            self.assertFalse(doc.get('images'))
            self.assertTrue(all(n['extras']['source_licence']=='CC-BY-4.0' for n in doc['nodes'] if 'mesh' in n))

    def test_ags_lid_is_registered_to_its_hinge_pin_and_closes_above_the_keys(self):
        q=224/82;a=json.loads((ASSETS/'gba/registration.json').read_text())
        self.assertAlmostEqual(a['source_open_degrees'],105.0,delta=.05)   # the source's own angle
        self.assertAlmostEqual(a['open_degrees'],105.45,delta=.1)          # after the 82 x 84.6 mm footprint correction
        self.assertEqual(a['hinge_native'][0],0);self.assertIn('hinge pin',a['hinge_basis'])
        g=gltf('gba');nodes=[n for n in g['nodes'] if 'mesh' in n]
        hinged={n['name'] for n in nodes if n['extras']['hinged']}
        self.assertEqual(hinged,{'SP display lid','SP LCD glass','SP Top_LargeHinge','SP Top_SmallHinge','SP ScreenGuard','SP LogoSticker'})
        # Rotate actual exported LCD triangles about the registered axis: flat, above the keys.
        p=triangles('gba','SP LCD glass','model').reshape(-1,3)
        h=np.array(a['hinge_native'])/q;v=p-h;t=np.radians(a['open_degrees'])
        closed_y=h[1]+np.cos(t)*v[:,1]-np.sin(t)*v[:,2]
        self.assertLess(np.ptp(closed_y),.2)
        keys=triangles('gba','SP DPad','model')
        self.assertGreater(closed_y.min(),keys[:,:,1].max()+.2)
        raw=(ASSETS/'gba/model.mesh').read_bytes();_,_,count,door=struct.unpack_from('<8sIII',raw)
        self.assertEqual((count-door)//3,6096+1280*2+1056+56+2)         # the complete source lid group
        header=(ROOT/'tools/slotlaunch/lid-data.h').read_text()
        self.assertIn('%.9f'%a['hinge_native'][1],header);self.assertIn('%.12f'%a['open_radians'],header)

    def test_gba_selected_source_and_preserved_vxcl_alternative(self):
        source=json.loads((ROOT/'third_party/models/dave-gba/source.json').read_text())
        self.assertEqual(source['licence'],'CC-BY-4.0')
        self.assertIn(source['url'],(ASSETS.parent/'MODEL_CREDITS.txt').read_text())
        self.assertEqual(source['source_assembled_wht_mm'],[60,34.4,7.7])
        names={n['name'] for n in gltf('gba','media')['nodes'] if 'mesh' in n}
        self.assertEqual(names,{'Cartridge_geo'})
        current=json.loads((ASSETS/'gba/media-registration.json').read_text())
        self.assertEqual(current['creator'],'thegraphicsgeek');self.assertFalse(current['decimation'])
        self.assertEqual(current['source_sha256'],'dad8725dd884d7254741b3a662358617d6bfc00a7b870365b2e3ebac51e2ed8f')
        prior=list((ASSETS.parent/'cartridges/models/gba').glob('previous-*/media-registration.json'))
        self.assertTrue(any(json.loads(p.read_text()).get('creator')=='Vxcl' for p in prior))


if __name__=='__main__':unittest.main()
