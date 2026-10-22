"""A physical-surface update must not replace manual or cached printed artwork."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import render
from tools.dev.refresh_psx_materials import refresh, digest


class DiscMaterialRefreshTests(unittest.TestCase):
    def test_print_and_original_cache_are_preserved_with_verified_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root/'slotcarts'
            media.mkdir()
            previous = Image.new('RGBA',(648,648),(217,34,76,255))
            raw = media/'Manual Print.disc.png'
            previous.save(raw)
            key = [[1,'old-revision'],'psx',[154,151,143],'solid','own','manual.png',None,[123,456]]
            manifest = media/'.slotcart.json'
            manifest.write_text(json.dumps({'Manual Print':json.dumps(key)}))
            original = {p.name:p.read_bytes() for p in (raw,manifest)}
            backup = root/'before-rings'
            result = refresh(media,ROOT/'theme/art-book-slot/_slot/shapes/psx',backup)
            self.assertEqual(result['updated'],1)
            hashes = json.loads((backup/'backup-sha256.json').read_text())
            for name,data in original.items():
                self.assertEqual((backup/name).read_bytes(),data)
                self.assertEqual(hashes[name],digest(backup/name))
            changed = json.loads(json.loads(manifest.read_text())['Manual Print'])
            self.assertEqual(changed[1:],key[1:])
            with Image.open(raw) as image:
                self.assertEqual(image.getpixel((324,80)),previous.getpixel((324,80)))
                self.assertLess(max(image.getpixel((324,2))[:3]),100)
                self.assertEqual(image.getpixel((324,324))[3],0)
            printed = Image.open(raw).convert('RGB')
            y,x = np.mgrid[:648,:648]
            radius = np.hypot(x+.5-324,y+.5-324)
            unaffected = (radius>100)&(radius<310)
            np.testing.assert_array_equal(np.asarray(printed)[unaffected],np.asarray(previous.convert('RGB'))[unaffected])
            self.assertTrue((media/'Manual Print.disc.tga').is_file())
            self.assertTrue((media/'Manual Print.png').is_file())
            with self.assertRaises(FileExistsError):
                refresh(media,ROOT/'theme/art-book-slot/_slot/shapes/psx',backup)


if __name__ == '__main__':
    unittest.main()
