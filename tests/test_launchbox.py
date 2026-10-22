"""Regional label selection must not silently borrow artwork from another game/region."""
import json
import sys
import tempfile
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import __main__ as baker, launchbox, shells


class RegionalLabels(unittest.TestCase):
    def test_exact_alternate_name_region_and_offline_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'launchbox'
            folder.mkdir()
            def image(ident, name, region, kind='Cart - Front'):
                return dict(DatabaseID=ident, FileName=name+'.png', Region=region, Type=kind)
            index = dict(games={'1': ['The Legend of Zelda: A Link to the Past', 'Zelda no Densetsu'],
                                '2': ['Shared Name'], '3': ['Shared Name']},
                         images=[image('1', 'usa', 'North America'), image('1', 'europe', 'Europe'),
                                 image('1', 'japan', 'Japan'),
                                 image('1', 'reconstructed', 'North America', 'Fanart - Cart - Front')])
            (folder/'snes.json').write_text(json.dumps(index))
            carts = launchbox.LaunchBox(tmp, offline=True)
            game = SimpleNamespace(stem='Legend of Zelda, The - A Link to the Past (USA)', title='')
            # An index hit without a downloaded label still uses the logo/text fallback offline.
            self.assertEqual(carts.candidates(game), [])
            (folder/'labels').mkdir()
            for record in index['images']:
                Image.new('RGB', (30, 10)).save(carts.label_path(record))
            # Real scan first, then reconstructed label, always from the ROM's region.
            self.assertEqual([i['FileName'] for i in carts.candidates(game)],
                             ['usa.png', 'reconstructed.png'])
            game.stem = 'Zelda no Densetsu (Japan)'
            self.assertEqual([i['FileName'] for i in carts.candidates(game)], ['japan.png'])
            game.stem = 'Legend of Zelda, The - A Link to the Past II (Europe)'
            self.assertEqual(carts.candidates(game), [])
            game.stem = 'Shared Name (USA)'
            self.assertEqual(carts.candidates(game), [])

    def test_metadata_platform_isolation_and_alternate_names(self):
        xml = '''<LaunchBox>
          <Game><DatabaseID>1</DatabaseID><Name>Example</Name>
            <Platform>Super Nintendo Entertainment System</Platform></Game>
          <Game><DatabaseID>2</DatabaseID><Name>Example</Name><Platform>Windows</Platform></Game>
          <GameAlternateName><DatabaseID>1</DatabaseID><AlternateName>Alternate</AlternateName></GameAlternateName>
          <GameImage><DatabaseID>1</DatabaseID><FileName>cart.png</FileName><Region>Europe</Region><Type>Cart - Front</Type></GameImage>
          <GameImage><DatabaseID>1</DatabaseID><FileName>box.png</FileName><Type>Box - Front</Type></GameImage>
          <GameImage><DatabaseID>2</DatabaseID><FileName>other.png</FileName><Type>Cart - Front</Type></GameImage>
        </LaunchBox>'''
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'metadata.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('Metadata.xml', xml)
            index = launchbox.index_from_archive(archive)
            self.assertEqual(index['games'], {'1': ['Example', 'Alternate']})
            self.assertEqual([i['FileName'] for i in index['images']], ['cart.png'])

    def test_crop_ignores_transparent_outer_margin_and_rejects_portrait(self):
        cart = Image.new('RGBA', (360, 245), 'grey')
        ImageDraw.Draw(cart).rectangle((70, 0, 293, 111), fill='navy')
        padded = Image.new('RGBA', (400, 285))
        padded.paste(cart, (20, 20))
        a = launchbox.label_crop(cart, 'North America')
        b = launchbox.label_crop(padded, 'North America')
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertEqual(a.getpixel((a.width//2, a.height//2)), (0, 0, 128))
        with self.assertRaises(ValueError):
            launchbox.label_crop(Image.new('RGB', (100, 300)), 'North America')

    def test_only_changed_shape_invalidates_baked_carts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(baker, 'SLOT_DIR', Path(tmp)):
            for name, spec in [('gba', {}), ('snes', {'revision': 'one'})]:
                folder = Path(tmp)/'shapes'/name
                folder.mkdir(parents=True)
                (folder/'shape.json').write_text(json.dumps(spec))
            baker.shape_revision.cache_clear()
            plan = ('text', 'Example', (50, 50, 50))
            gba = baker.key_for('gba', shells.GBA_CHARCOAL, plan)
            snes = baker.key_for('snes', shells.SNES_GREY, plan)
            (Path(tmp)/'shapes/snes/shape.json').write_text('{"revision":"two"}')
            baker.shape_revision.cache_clear()
            self.assertEqual(gba, baker.key_for('gba', shells.GBA_CHARCOAL, plan))
            self.assertNotEqual(snes, baker.key_for('snes', shells.SNES_GREY, plan))
            baker.shape_revision.cache_clear()

    def test_shared_revision_scan_downloads_once_and_accepts_revision_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)/'launchbox'
            folder.mkdir()
            (folder/'snes.json').write_text('{"games":{},"images":[]}')
            carts = launchbox.LaunchBox(tmp, offline=True)
            carts.offline = False
            pixels = BytesIO()
            Image.new('RGB', (360, 245), 'navy').save(pixels, 'PNG')
            image = dict(DatabaseID='1', FileName='r2_example.png', Region='North America')
            with patch.object(launchbox.urllib.request, 'urlopen',
                              side_effect=lambda *a, **k: BytesIO(pixels.getvalue())) as download:
                with ThreadPoolExecutor(4) as workers:
                    paths = list(workers.map(carts.fetch, [image]*4))
                self.assertEqual(download.call_count, 1)
                self.assertEqual(len(set(paths)), 1)
                self.assertTrue(paths[0].exists())
                self.assertIsNone(carts.fetch(dict(image, FileName='../other.png')))
                self.assertEqual(download.call_count, 1)


if __name__ == '__main__':
    unittest.main()
