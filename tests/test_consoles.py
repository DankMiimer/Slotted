"""Contracts for the shipped 3D assets and the bounded GLES loader."""
import json
from pathlib import Path
import struct
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT/'theme/art-book-slot/_slot/consoles'
NAMES = ('gb','gbc','gba','snes','snes-us','nes','n64','md','md-jp','nds','psp','pico8','psx','dreamcast')


class ConsoleAssets(unittest.TestCase):
    def test_native_buffers_are_bounded_and_complete(self):
        for name in NAMES:
            with self.subTest(name=name):
                raw=(MODELS/name/'model.mesh').read_bytes()
                magic,vertices,indices,door=struct.unpack_from('<8sIII',raw)
                self.assertEqual(magic,b'SCTOON2\0')
                self.assertTrue(0<vertices<=65535)
                self.assertTrue(0<indices<=600000 and indices%3==0)
                self.assertTrue(0<=door<=indices and door%3==0)
                self.assertEqual(len(raw),20+vertices*36+indices*2)
                points=np.frombuffer(raw,dtype='<f4',count=vertices*9,offset=20).reshape(-1,9)
                faces=np.frombuffer(raw,dtype='<u2',count=indices,offset=20+vertices*36)
                self.assertTrue(np.isfinite(points).all())
                lengths=np.linalg.norm(points[:,3:6],axis=1)
                # Ink keeps a directional normal but skips the black hull.
                self.assertTrue(np.logical_or(np.isclose(lengths,1,atol=.002),
                                              np.isclose(lengths,.25,atol=.002)).all())
                # Textured sources carry their printing in the albedo instead.
                if not (MODELS/name/'model.texture').exists():
                    self.assertTrue(np.isclose(lengths,.25,atol=.002).any())
                self.assertLess(abs(points[:,:3]).max(),1000)
                self.assertTrue((points[:,6:]>=0).all() and (points[:,6:]<=1).all())
                self.assertLess(int(faces.max()),vertices)
                self.assertGreater(np.ptp(points[:,0]),150)
                self.assertGreater(np.ptp(points[:,2]),40)
                self.assertEqual(door<indices,name in ('nes','psp','n64','psx','dreamcast','gba','nds'))
                if name=='psp':
                    hinge_points=points[faces[door:],:3]
                    self.assertGreater(hinge_points[:,2].min(),-34)
                    # Ostrovsky's rear cover is split at its seams; its curved
                    # forward rim reaches 7 native units short of the centre.
                    self.assertLess(hinge_points[:,2].max(),-6)
                    self.assertLess(np.ptp(points[:,2]),75)  # Ostrovsky's 26.06 mm depth
                info=json.loads((MODELS/name/'mesh-info.json').read_text())
                self.assertEqual((vertices,indices,door),(info['vertices'],info['indices'],info['door_first']))

    def test_editable_models_include_the_housings_and_no_game_textures(self):
        required={'gb':'DMG front housing','gbc':'CGB housing',
                  'gba':'SP lower housing','snes':'PAL upper enclosure',
                  'snes-us':'US upper enclosure','nes':'Upper ivory cover',
                  'n64':'N64 upper enclosure','md':'Upper shell','md-jp':'Upper shell',
                  'nds':'DS Lite lower housing','psp':'PSP front housing', 'pico8':'Fantasy 8 lower housing',
                  'psx':'PS1 enclosure','dreamcast':'Dreamcast enclosure'}
        for name in NAMES:
            with self.subTest(name=name):
                raw=(MODELS/name/'model.glb').read_bytes()
                length,kind=struct.unpack_from('<II',raw,12)
                self.assertEqual(kind,0x4e4f534a)
                gltf=json.loads(raw[20:20+length])
                nodes={n['name'] for n in gltf['nodes'] if 'mesh' in n}
                self.assertIn(required[name],nodes)
                self.assertFalse(gltf.get('images'))
                if not (MODELS/name/'model.texture').exists():
                    self.assertTrue(all('COLOR_0' in p['attributes'] for m in gltf['meshes'] for p in m['primitives']))

    def test_controls_and_connectors_keep_physical_proportions(self):
        def model(name):
            raw=(MODELS/name/'model.glb').read_bytes()
            length=struct.unpack_from('<I',raw,12)[0]
            return json.loads(raw[20:20+length])

        def extent(gltf,name):
            node=next(n for n in gltf['nodes'] if n.get('name')==name)
            primitive=gltf['meshes'][node['mesh']]['primitives'][0]
            accessor=gltf['accessors'][primitive['attributes']['POSITION']]
            return np.array(accessor['max'])-accessor['min']

        # Verheyen's DMG keeps its controls as source-textured moulding, so only
        # the separated active LCD has a measurable standalone part.
        width,height,_=extent(model('gb'),'LCD screen')
        self.assertAlmostEqual(width/height,160/144,delta=.02)
        gltf=model('gbc');width,height,_=extent(gltf,'CGB LCD glass')
        self.assertAlmostEqual(width/height,160/144,delta=.02)
        width,height,depth=extent(gltf,'Continuous D-pad')
        self.assertAlmostEqual(width/height,1,delta=.02)
        self.assertLess(depth,width*.32)
        # Authored NUS-001 sockets: four round ~21-mm surrounds side by side.
        n64=model('n64');width,height,depth=extent(n64,'N64 controller port surrounds')*100/1.5
        self.assertAlmostEqual(height,21,delta=1.5);self.assertGreater(width,4*height)
        for name in ('md','md-jp'):
            gltf=model(name);width,height,_=extent(gltf,'Controller cavity')
            self.assertAlmostEqual(width/height,58/22,delta=.05)
            pins=[n for n in gltf['nodes'] if n.get('name','').startswith('Controller contact')]
            self.assertEqual(len(pins),18)
        sp=model('gba')
        nodes={n.get('name') for n in sp['nodes']}
        self.assertTrue({'SP LinkPort','SP ChargingPort','SP DPad'}<=nodes)


if __name__=='__main__':unittest.main()
