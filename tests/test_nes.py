"""NES platform isolation, label cropping and cartridge coverage."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import labels, launchbox, render, shells
from slotcart.library import CrcCache, scan


class NesIntegration(unittest.TestCase):
    def test_rom_formats_and_header_do_not_select_handheld_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root/'roms'/'nesh'
            folder.mkdir(parents=True)
            data = bytearray(1024)
            data[:4] = b'NES\x1a'
            data[0x143] = 0xC0
            for ext in ('.nes', '.unf', '.unif'):
                (folder/('Game'+ext)).write_bytes(data)
            (folder/'gamelist.xml').write_text('<gameList><game><path>./Game.nes</path>'
                                             '<name>#NONGAME</name></game></gameList>')
            with zipfile.ZipFile(folder/'Compressed.zip', 'w') as archive:
                archive.writestr('Game.NES', data)
            class HandheldArt:
                def entry(self, crc):
                    raise AssertionError('NES must not query handheld label CRCs')
            games = scan(root/'roms', ['nesh'], CrcCache(root/'cache'))
            self.assertEqual(len(games), 4)
            for game in games:
                self.assertNotEqual(game.title, '#NONGAME')
                self.assertEqual(shells.choose(game.header, game.stem, {}), ('nes', shells.NES_GREY))
                self.assertEqual(labels.candidates(game, HandheldArt())[0][0], 'text')

    def test_platform_index_and_offline_crops_stay_separate(self):
        xml = '''<LaunchBox>
          <Game><DatabaseID>1</DatabaseID><Name>Shared Game</Name><Platform>Nintendo Entertainment System</Platform></Game>
          <Game><DatabaseID>2</DatabaseID><Name>Shared Game</Name><Platform>Super Nintendo Entertainment System</Platform></Game>
          <GameImage><DatabaseID>1</DatabaseID><FileName>nes.png</FileName><Region>North America</Region><Type>Cart - Front</Type></GameImage>
          <GameImage><DatabaseID>2</DatabaseID><FileName>snes.png</FileName><Region>North America</Region><Type>Cart - Front</Type></GameImage>
        </LaunchBox>'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root/'metadata.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('Metadata.xml', xml)
            cache = root/'launchbox'
            cache.mkdir()
            for platform in ('nes', 'snes'):
                index = launchbox.index_from_archive(archive, launchbox.PLATFORMS[platform])
                (cache/(platform+'.json')).write_text(json.dumps(index))
            providers = {p: launchbox.LaunchBox(root, offline=True, platform=p) for p in ('nes', 'snes')}
            game = SimpleNamespace(stem='Shared Game (USA)', title='Shared Game')
            self.assertEqual(providers['nes'].candidates(game), [])
            for platform, provider in providers.items():
                record = provider.index['images'][0]
                path = provider.label_path(record)
                path.parent.mkdir(exist_ok=True)
                Image.new('RGB', (10, 10)).save(path)
                self.assertEqual(provider.candidates(game)[0]['FileName'], platform+'.png')
            record = dict(FileName='same.png')
            self.assertNotEqual(providers['nes'].label_path(record), providers['snes'].label_path(record))

    def test_crop_extracts_right_hand_portrait_label_and_rejects_famicom(self):
        cart = Image.new('RGBA', (304, 337), 'grey')
        ImageDraw.Draw(cart).rectangle((122, 2, 263, 230), fill='navy')
        padded = Image.new('RGBA', (344, 377))
        padded.paste(cart, (20, 20))
        a = launchbox.label_crop(cart, 'North America', 'nes')
        b = launchbox.label_crop(padded, 'North America', 'nes')
        self.assertEqual(a.tobytes(), b.tobytes())
        self.assertLess(a.width, a.height)
        self.assertEqual(a.getpixel((a.width//2, a.height//2)), (0, 0, 128))
        with self.assertRaises(ValueError):
            launchbox.label_crop(Image.new('RGB', (360, 245)), 'Japan', 'nes')

    def test_shared_archive_needs_one_download_and_can_build_offline_index(self):
        xml = '''<LaunchBox>
          <Game><DatabaseID>1</DatabaseID><Name>NES Game</Name><Platform>Nintendo Entertainment System</Platform></Game>
          <Game><DatabaseID>2</DatabaseID><Name>SNES Game</Name><Platform>Super Nintendo Entertainment System</Platform></Game>
        </LaunchBox>'''
        payload = BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('Metadata.xml', xml)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(launchbox.urllib.request, 'urlopen',
                              side_effect=lambda *a, **k: BytesIO(payload.getvalue())) as download:
                nes = launchbox.LaunchBox(tmp, platform='nes')
                snes = launchbox.LaunchBox(tmp, platform='snes')
                self.assertEqual(download.call_count, 1)
                self.assertEqual(nes.index['games'], {'1': ['NES Game']})
                self.assertEqual(snes.index['games'], {'2': ['SNES Game']})
                (Path(tmp)/'launchbox'/'nes.json').unlink()
                offline = launchbox.LaunchBox(tmp, offline=True, platform='nes')
                self.assertEqual(offline.index, nes.index)
                self.assertEqual(download.call_count, 1)

    def test_gold_and_grey_shells_have_opaque_labels_and_body(self):
        shape = render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/nes')
        header = shells.read_header('nes', b'')
        for title in ('Legend of Zelda, The (USA)', 'Zelda II - The Adventure of Link (Europe)'):
            self.assertEqual(shells.choose(header, title, {}), ('nes', shells.NES_GOLD))
        for shell in (shells.NES_GREY, shells.NES_GOLD):
            face = render.face(shape, shell, Image.new('RGB', (100, 150), 'navy'))
            self.assertEqual(face.getchannel('A').crop(shape.well).getextrema(), (255, 255))
            self.assertEqual(face.getpixel((210, 300))[3], 255)
            self.assertEqual(face.getpixel((0, 0))[3], 0)


if __name__ == '__main__':
    unittest.main()
