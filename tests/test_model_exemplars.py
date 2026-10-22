"""Physical anchors, protected contours and seated clearance of exported assets."""
import json
import struct
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'theme/art-book-slot/_slot/consoles'


def gltf(system,stem='model'):
    raw=(ASSETS/system/(stem+'.glb')).read_bytes()
    length=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+length])


def bounds(g,name):
    node=next(n for n in g['nodes'] if n.get('name')==name)
    accessor=g['accessors'][g['meshes'][node['mesh']]['primitives'][0]['attributes']['POSITION']]
    return np.array(accessor['min']),np.array(accessor['max'])


def triangles(system,name,stem='media'):
    raw=(ASSETS/system/(stem+'.glb')).read_bytes()
    length=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+length])
    binary=memoryview(raw)[28+length:]
    node=next(n for n in g['nodes'] if n.get('name')==name)
    primitive=g['meshes'][node['mesh']]['primitives'][0]
    def read(index,columns):
        a=g['accessors'][index];v=g['bufferViews'][a['bufferView']]
        dtype={5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
        offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        stride=v.get('byteStride',np.dtype(dtype).itemsize*columns)
        return np.ndarray((a['count'],columns),dtype,buffer=binary,offset=offset,
                          strides=(stride,np.dtype(dtype).itemsize))
    q={'gb':168/90,'psp':480/169.4,'gbc':168/78,'gba':224/82}[system]
    points=read(primitive['attributes']['POSITION'],3)*100/q
    return points[read(primitive['indices'],1).ravel()].reshape(-1,3,3)


def ray_depths(mesh,x,y):
    """Intersect an orthographic depth ray with actual exported triangles."""
    a=mesh[:,0,:2];b=mesh[:,1,:2]-a;c=mesh[:,2,:2]-a;p=np.array((x,y))-a
    area=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid=np.abs(area)>1e-8
    b,c,p,area=b[valid],c[valid],p[valid],area[valid]
    u=(p[:,0]*c[:,1]-p[:,1]*c[:,0])/area
    v=(b[:,0]*p[:,1]-b[:,1]*p[:,0])/area
    inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
    z=mesh[valid,:,2]
    return (z[:,0]+u*(z[:,1]-z[:,0])+v*(z[:,2]-z[:,0]))[inside]


class ModelExemplars(unittest.TestCase):
    def test_dmg_rear_wall_and_cartridge_depth_clearance(self):
        # Bram Verheyen's rear housing, registered by tools/consolebuild/verheyen_gb.py.
        case=triangles('gb','DMG rear housing','model')
        reg=json.loads((ASSETS/'gb/registration.json').read_text());q=168/90
        floor=-reg['bay_floor_mm'];label=-(reg['bay_floor_mm']+.2+reg['game_pak_mm'][2])
        wall=np.unique(np.round(ray_depths(case,0,40),3))
        self.assertLess(wall[0],-17)                           # outer rear moulding
        self.assertAlmostEqual(wall[-1],floor,delta=.01)       # measured bay floor
        self.assertGreater(label-wall[1],.5)                   # clearance behind the label
        self.assertGreater(floor-(label+reg['game_pak_mm'][2]),.15)  # and in front of the Game Pak
        # Above the measured rear lip the bay is open; below it the wall is closed.
        self.assertLess(ray_depths(case,0,reg['rear_lip_mm']-.5).min(),-17)
        self.assertGreater(ray_depths(case,0,reg['rear_lip_mm']+.5).min(),floor-.01)
        specs=json.loads((ASSETS/'specs.json').read_text())['gb']
        self.assertAlmostEqual(specs['slot']/q,reg['rear_lip_mm'],delta=.01)
        self.assertAlmostEqual(reg['cart_label_native'],label*q,delta=.01)

    def test_dmg_keeps_every_source_triangle_and_lcd_is_separate(self):
        info=json.loads((ASSETS/'gb/mesh-info.json').read_text())
        reg=json.loads((ASSETS/'gb/registration.json').read_text())
        self.assertEqual((info['triangles'],reg['source_triangles'],reg['decimation']),(9856,9856,False))
        g=gltf('gb');names={n.get('name') for n in g['nodes'] if 'mesh' in n}
        self.assertTrue({'DMG front housing','DMG rear housing','LCD screen','DMG LCD bevel'}<=names)
        lo,hi=bounds(g,'LCD screen');q=168/90
        np.testing.assert_allclose((hi-lo)[:2]*100/q,reg['lcd_size_mm'],atol=.01)

    def test_editable_exports_retain_motion_and_unit_metadata(self):
        for system,q in (('gb',168/90),('psp',480/169.4)):
            for stem in ('model','model-master','model-physical','media-master','media-physical'):
                g=gltf(system,stem);extras=g['scenes'][g['scene']]['extras']
                self.assertAlmostEqual(extras['slotters_native_units_per_mm'],q)
                self.assertAlmostEqual(extras['slotters_glb_to_metres'],1 if stem.endswith('-physical') else 1/(10*q))
                nodes=[n for n in g['nodes'] if 'mesh' in n]
                self.assertTrue(all(isinstance(n['extras']['printed'],bool) and isinstance(n['extras']['hinged'],bool) for n in nodes))
                hinged={n['name'] for n in nodes if n['extras']['hinged']}
                if system=='psp' and stem.startswith('model'):
                    self.assertEqual(hinged,{'PSP UMD cover','PSP UMD cover inside','PSP UMD holder rail 0',
                                             'PSP UMD holder rail 1','PSP UMD holder stop'})
                else:self.assertFalse(hinged)
        # The source has no mechanism: the fitted hinge is registered, not claimed.
        reg=json.loads((ASSETS/'psp/registration.json').read_text())
        np.testing.assert_allclose(np.array(reg['hinge_native'])/(480/169.4),(0,-36.5,-10.6),atol=1e-6)
        self.assertIn('approximations',reg['hinge_uncertainty'])

    def test_complete_media_envelope_and_umd_hub(self):
        for system,q,dimensions in (('gb',168/90,(57,65.5,7.8)),('psp',480/169.4,(64,65,4.21))):
            raw=(ASSETS/system/'media.mesh').read_bytes();count=struct.unpack_from('<I',raw,8)[0]
            points=np.frombuffer(raw,'<f4',count*9,20).reshape(-1,9)[:,:3]/q
            np.testing.assert_allclose(np.ptp(points,axis=0),dimensions,atol=.015)
        low,high=bounds(gltf('psp','media'),'UMD clamping plate')
        np.testing.assert_allclose((high-low)*100/(480/169.4),(13,13,.18),atol=.015)

    def test_umd_rear_apertures_have_correct_handedness_depth_and_closed_front(self):
        case=triangles('psp','UMD original ECMA case')
        for x,y,minimum in ((20.5,-26.3,1.5),(-20.5,-26.3,1.5),(0,0,.1),(20,0,.1),(-31,-7.2,1.3)):
            depths=ray_depths(case,x,y)
            self.assertGreaterEqual(depths.min(),minimum-.005)
            self.assertAlmostEqual(depths.max(),2.1,delta=.005)
        self.assertAlmostEqual(ray_depths(case,-20,0).min(),-2.1,delta=.005)
        self.assertAlmostEqual(ray_depths(case,10.6,0).min(),-2.1,delta=.005)
        self.assertGreater(ray_depths(case,10.8,0).min(),.09)
        self.assertGreater(ray_depths(case,-22.6,-26.3).min(),1.49)
        self.assertAlmostEqual(ray_depths(case,22.6,-26.3).min(),-2.1,delta=.005)

    def test_game_pak_label_is_inside_the_recreated_recess(self):
        case=triangles('gb','DMG Game Pak recreation shell')
        self.assertGreater(ray_depths(case,0,27).max(),2.8)
        self.assertAlmostEqual(ray_depths(case,0,-2.5).max(),3.5532,delta=.01)
        self.assertGreater(ray_depths(case,0,-29).min(),-3.9)
        g=gltf('gb','media');low,high=bounds(g,'Blank Game Pak label')
        self.assertLess(high[2]*100/(168/90),3.9)
        self.assertLess((high-low)[0]*100/(168/90),57)

    def test_published_envelopes_and_corrected_psp_display(self):
        raw=(ASSETS/'gb/model.mesh').read_bytes();count=struct.unpack_from('<I',raw,8)[0]
        points=np.frombuffer(raw,'<f4',count*9,20).reshape(-1,9)[:,:3]/(168/90)
        reg=json.loads((ASSETS/'gb/registration.json').read_text());w,depth,height=reg['source_size_mm']
        np.testing.assert_allclose(np.ptp(points,axis=0),(w,height,depth),atol=.04)
        low,high=bounds(gltf('psp'),'PSP LCD glass');q=480/169.4
        size=(high-low)[:2]*100/q
        self.assertAlmostEqual(size[0]/size[1],480/272,delta=.02)   # source glass is 16:9
        self.assertAlmostEqual(size[0],95.3,delta=.1)
        np.testing.assert_allclose((high+low)[:2]*50/q,(0,2.5),atol=.05)
        low,high=bounds(gltf('psp'),'PSP UMD cover')
        np.testing.assert_allclose((high-low)[:2]*100/q,(76,74.04),atol=.01)

    def test_runtime_preserves_hero_contours(self):
        parts={'gb':('DMG front housing','DMG rear housing','DMG LCD bevel','LCD screen'),
               'psp':('PSP front housing','PSP LCD glass','PSP UMD cover','PSP UMD holder stop')}
        for system,names in parts.items():
            runtime=gltf(system);master=gltf(system,'model-master')
            for name in names:np.testing.assert_allclose(bounds(runtime,name),bounds(master,name),atol=1e-6)

    def test_psp_keeps_the_fifteen_source_buttons_and_splits_the_cover(self):
        g=gltf('psp');names={n.get('name') for n in g['nodes'] if 'mesh' in n}
        self.assertEqual({n for n in names if n.startswith('PSP button')},{'PSP button%d'%i for i in range(1,16)})
        self.assertTrue({'PSP rear left wing','PSP rear right wing','PSP UMD cover'}<=names)
        q=480/169.4;lo,hi=bounds(g,'PSP UMD cover')
        left=bounds(g,'PSP rear left wing')[1][0]*100/q;right=bounds(g,'PSP rear right wing')[0][0]*100/q
        self.assertAlmostEqual(left,lo[0]*100/q,delta=.01);self.assertAlmostEqual(right,hi[0]*100/q,delta=.01)

    def test_seated_umd_fits_holder_and_real_cover(self):
        q=480/169.4;g=gltf('psp');media=gltf('psp','media')
        low,high=bounds(media,'UMD original ECMA case')
        dl,dh=bounds(g,'PSP UMD cover')
        self.assertTrue(np.all(low[:2]>dl[:2]))
        self.assertTrue(np.all(high[:2]<dh[:2]))
        inside=bounds(g,'PSP UMD cover inside')[1][2]*100/q
        # The SDL label plane is in front of the measured inner lining.
        seat=json.loads((ASSETS/'psp/registration.json').read_text())['umd_label_native'][2]/q
        self.assertGreater(seat-inside,.20)
        ll,lh=bounds(g,'PSP UMD holder rail 0');rl,rh=bounds(g,'PSP UMD holder rail 1')
        self.assertGreater(rl[0]-lh[0],high[0]-low[0])

    def test_runtime_budget_physical_masters_and_credit(self):
        for system,q,author,licence in (('gb',168/90,'Bram Verheyen','CC-BY-NC'),('psp',480/169.4,'Ilya Ostrovsky','CC-BY-4.0')):
            info=json.loads((ASSETS/system/'mesh-info.json').read_text())
            self.assertIn(author,[c['author'] for c in info['creators']])
            self.assertIn(licence,info['licence'])
            for stem in ('model','media'):
                raw=(ASSETS/system/(stem+'.mesh')).read_bytes();magic,vertices,indices,door=struct.unpack_from('<8sIII',raw)
                self.assertEqual(magic,b'SCTOON2\0');self.assertEqual(len(raw),20+vertices*36+indices*2)
                # Source detail is kept undecimated (PSP: 58.7k triangles); frame time is a device check.
                self.assertLess(indices//3,{'gb':15000,'psp':60000}[system])
                physical=gltf(system,stem+'-physical')
                self.assertFalse(physical.get('images'))
                self.assertTrue(all('TEXCOORD_0' not in p['attributes'] for m in physical['meshes'] for p in m['primitives']))
                for node in physical['nodes']:
                    if 'mesh' in node:np.testing.assert_allclose(node['scale'],[1/(10*q)]*3,atol=1e-7)


if __name__=='__main__':unittest.main()
