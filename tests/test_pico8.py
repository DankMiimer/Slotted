"""Embedded artwork, executable data isolation, launcher fallback and rebake contracts."""
import hashlib
import importlib
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import pico8,render,shells
from slotcart.library import CrcCache,scan
baker=importlib.import_module('slotcart.__main__')


class PicoCartridges(unittest.TestCase):
    def test_png_art_and_credits_survive_with_opaque_alpha_and_rom_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'Game.p8.png'
            image=Image.new('RGBA',(160,205),(95,87,79,252))
            image.paste((41,173,255,253),(16,24,144,152))
            image.paste((255,241,232,254),(20,172,130,180));image.save(path)
            original=hashlib.sha256(path.read_bytes()).digest()
            shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/pico8')
            face=pico8.cartridge(shape,path)
            expected=render.face(shape,shells.PICO_GREY,image.convert('RGB').crop((16,24,144,196)))
            self.assertEqual(face.tobytes(),expected.tobytes())
            colours=set(face.convert('RGB').getdata())
            self.assertIn((41,173,255),colours);self.assertIn((255,241,232),colours)
            self.assertEqual(face.getpixel((132,180))[3],255)
            self.assertEqual(face.getpixel((0,0))[3],0)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),original)

    def test_text_section_is_bounded_and_never_runs_lua(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'Text.p8'
            source='pico-8 cartridge // http://www.pico-8.com\nversion 42\n__lua__\nerror("must not run")\n__label__\n'
            path.write_text(source+('8'*128+'\n')*128)
            label=pico8.text_label(path);self.assertEqual(label.size,(128,128))
            self.assertEqual(label.getpixel((127,127)),(255,0,77))
            path.write_text(source+'0'*127+'\n');self.assertIsNone(pico8.text_label(path))
            with path.open('wb') as stream:stream.truncate(pico8.MAX_TEXT+1)
            self.assertIsNone(pico8.text_label(path))

    def test_library_scans_png_text_and_launcher_without_crc_or_media_recursion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'pico8';folder.mkdir()
            Image.new('RGB',(160,205)).save(folder/'Game.p8.png')
            (folder/'Splore.png').write_text('Splore\n')
            (folder/'Text.p8').write_text('pico-8 cartridge\n')
            (folder/'media').mkdir();Image.new('RGB',(160,205)).save(folder/'media/Ignore.png')
            (folder/'Ignore.zip').touch()
            with patch('slotcart.library.read_rom',side_effect=AssertionError('CRC must not read ROM')):
                games=scan(root,['pico8'],CrcCache(root/'cache'))
            self.assertEqual({g.stem for g in games},{'Game.p8','Splore','Text'})
            self.assertTrue(all(g.crc=='' and g.header.platform=='pico8' for g in games))
            plans={g.stem:pico8.plan(g) for g in games}
            self.assertEqual(plans['Game.p8'][0],'pico-cart')
            self.assertEqual(plans['Splore'][0],'pico-browser')
            self.assertIsNone(plans['Text'])

    def test_bake_is_offline_idempotent_and_reacts_to_embedded_art_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'pico8';folder.mkdir();path=folder/'Game.p8.png'
            Image.new('RGB',(160,205),(30,70,90)).save(path)
            args=['--roms',str(root),'--systems','pico8','--cache',str(root/'cache'),'--offline','--jobs','1']
            self.assertEqual(baker.main(args),0)
            output=folder/'media/slotcarts/Game.p8.png';before=output.stat().st_mtime_ns
            self.assertEqual(baker.main(args),0);self.assertEqual(output.stat().st_mtime_ns,before)
            Image.new('RGB',(160,205),(90,70,30)).save(path)
            self.assertEqual(baker.main(args),0)
            self.assertEqual(Image.open(output).getpixel((132,180)),(90,70,30,255))


if __name__=='__main__':unittest.main()
