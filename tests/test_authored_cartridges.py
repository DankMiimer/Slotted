"""Selected source cartridges: integrity, original labels, style bake and isolation."""
import hashlib,importlib,json,struct,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];SLOT=ROOT/'theme/art-book-slot/_slot'
sys.path.insert(0,str(SLOT))
from slotcart import render
baker=importlib.import_module('slotcart.__main__')

class AuthoredCartridges(unittest.TestCase):
    def test_full_source_counts_and_bound_label_topology(self):
        for family,part,triangles,licence in [('snes','media',33839,'CC-BY-4.0'),('gba','media',5802,'CC-BY-4.0'),
                ('pico8','media',438,'CC-BY-4.0'),('n64','media',1050,'CC-BY-NC-SA-4.0'),
                ('snes','media-tzakol',216,'CC-BY-4.0'),('snes-us','media-tzakol',216,'CC-BY-4.0')]:
            with self.subTest(family=family,part=part):
                folder=SLOT/'consoles'/family;reg=json.loads((folder/(part+'-registration.json')).read_text())
                raw=(folder/(part+'.mesh')).read_bytes();_,n,count,_=struct.unpack_from('<8sIII',raw)
                self.assertEqual(count//3,triangles);self.assertFalse(reg['decimation']);self.assertEqual(reg['licence'],licence)
                self.assertEqual(hashlib.sha256(raw).hexdigest(),reg['prepared']['mesh_sha256'])
                label=(folder/(part+'-label.mesh')).read_bytes();_,ln,lc,_=struct.unpack_from('<8sIII',label)
                self.assertEqual(lc//3,reg['label_triangles'])
                p=np.frombuffer(label,'<f4',ln*9,20).reshape(-1,9)[:,:3]/reg['q']
                self.assertLessEqual(np.abs(p[:,0]).max(),reg['size_mm'][0]/2+.05)
                self.assertLessEqual(np.abs(p[:,1]).max(),reg['size_mm'][1]/2+.05)
                if family=='snes' and part=='media':self.assertGreater(np.ptp(p[:,2]),1,'Keep the curved source sticker')
                if family=='n64':self.assertTrue(reg['atlas']['excluded_images'])
                if family=='gba':self.assertTrue(reg['atlas']['blank_pixel_rectangles'])

    def test_snes_bakes_both_styles_atomically_and_caches_each(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'snes';folder.mkdir();rom=folder/'Fixture (Europe).sfc'
            rom.write_bytes(bytes(1024));original=hashlib.sha256(rom.read_bytes()).digest()
            args=['--roms',str(root),'--systems','snes','--cache',str(root/'cache'),'--offline','--jobs','1']
            self.assertEqual(baker.main(args),0)
            paths=[folder/'media/slotcarts'/('Fixture (Europe)'+suffix) for suffix in ('.png','.tzakol.png','.tzakol.back.png')]
            self.assertTrue(all(p.exists() for p in paths));before=[p.stat().st_mtime_ns for p in paths]
            self.assertNotEqual(paths[0].read_bytes(),paths[1].read_bytes())
            self.assertEqual(baker.main(args),0);self.assertEqual(before,[p.stat().st_mtime_ns for p in paths])
            self.assertEqual(hashlib.sha256(rom.read_bytes()).digest(),original)
            manifest=json.loads((paths[0].parent/'.slotcart.json').read_text())
            self.assertIn('Fixture (Europe)',manifest);self.assertIn('Fixture (Europe).tzakol',manifest)
