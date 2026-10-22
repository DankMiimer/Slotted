"""SNES integration: compressed ROM discovery, platform isolation and opaque baked labels."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'theme/art-book-slot/_slot'))
from slotcart import labels, render, shells
from slotcart.library import CrcCache, scan


class SnesIntegration(unittest.TestCase):
    def test_physical_shell_matches_filename_region(self):
        header = shells.read_header('snes', b'')
        for region in ('USA', 'Canada', 'USA, Europe'):
            self.assertEqual(shells.choose(header, 'Game (%s)' % region, {}),
                             ('snes-us', shells.SNES_US_GREY))
        for region in ('Europe', 'Japan', 'Japan, Europe', 'World'):
            self.assertEqual(shells.choose(header, 'Game (%s)' % region, {}),
                             ('snes', shells.SNES_GREY))
        self.assertEqual(shells.choose(header, 'A Game About USA (Europe)', {})[0], 'snes')

    def test_snes_does_not_use_gb_header_flags_or_handheld_art(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root/'roms'/'snes'
            folder.mkdir(parents=True)
            # A GB flag-like byte in a SNES ROM must never select a transparent GBC shell.
            rom = bytearray(1024)
            rom[0x143] = 0xC0
            (folder/'Example (Europe).sfc').write_bytes(rom)
            with zipfile.ZipFile(folder/'Compressed.zip', 'w') as archive:
                archive.writestr('readme.txt', 'Not a ROM')
                archive.writestr('Game.SMC', rom)
            (folder/'media').mkdir()
            (folder/'media'/'Ignored.sfc').write_bytes(rom)
            cache = CrcCache(root/'cache')
            games = scan(root/'roms', ['snes'], cache)
            self.assertEqual(len(games), 2)
            self.assertEqual({g.crc for g in games}, {games[0].crc})
            class HandheldArt:
                def entry(self, crc):
                    raise AssertionError('SNES must not consult the handheld CRC art set')
            for game in games:
                self.assertEqual(shells.choose(game.header, game.stem, {}), ('snes', shells.SNES_GREY))
                self.assertEqual(labels.candidates(game, HandheldArt())[0][0], 'text')
            own = root/'labels'/'SNES'
            own.mkdir(parents=True)
            Image.new('RGB', (80, 40), 'red').save(own/(games[0].stem+'.png'))
            self.assertEqual(labels.candidates(games[0], HandheldArt(), root/'labels')[0][0], 'own')

    def test_baked_snes_label_and_body_are_opaque(self):
        for name, shell in (('snes', shells.SNES_GREY), ('snes-us', shells.SNES_US_GREY)):
            with self.subTest(name=name):
                shape = render.Shape(ROOT/('theme/art-book-slot/_slot/shapes/'+name))
                face = render.face(shape, shell, Image.new('RGBA', (100, 50), 'navy'))
                well = shape.well
                self.assertEqual(face.getchannel('A').crop(well).getextrema(), (255, 255))
                self.assertEqual(face.getpixel((180, 210))[3], 255)
                self.assertEqual(face.getpixel((0, 0))[3], 0)
                # The label's rounded corner reveals opaque plastic, not wallpaper or label ink.
                self.assertNotEqual(face.getpixel((well[0], well[1]))[:3], (0, 0, 128))


if __name__ == '__main__':
    unittest.main()
