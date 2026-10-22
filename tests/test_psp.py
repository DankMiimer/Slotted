"""UMD library cost, region-safe scans, original shell opacity and runtime assets."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import launchbox,render,shells
from slotcart.library import CrcCache,scan,HEAD


class PspIntegration(unittest.TestCase):
    def test_large_iso_is_bounded_and_media_not_scanned_as_rom(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'psp';folder.mkdir()
            with (folder/'Game (USA).iso').open('wb') as f:
                f.write(b'CD001'+bytes(HEAD));f.seek(1024*1024*1024);f.write(b'X')
            (folder/'Portable (Japan).cso').write_bytes(b'CISO'+bytes(400))
            (folder/'Homebrew.pbp').write_bytes(b'\0PBP'+bytes(400))
            (folder/'media').mkdir();(folder/'media/Ignore.iso').touch()
            (folder/'Archive.zip').touch()
            with patch('slotcart.library.read_rom',side_effect=AssertionError('full-ROM CRC')):
                games=scan(root,['psp'],CrcCache(root/'cache'))
            self.assertEqual(len(games),3)
            for game in games:
                self.assertEqual(game.crc,'');self.assertEqual(len(game.head),HEAD)
                self.assertEqual(shells.outline_for(game.header),'psp')

    def test_regions_and_crop_do_not_put_a_shell_inside_a_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'launchbox';folder.mkdir()
            images=[dict(DatabaseID='1',FileName=region+'.png',Region=region,Type='Disc')
                    for region in ('North America','Japan','Europe')]
            (folder/'psp.json').write_text(json.dumps(dict(games={'1':['Game']},images=images)))
            provider=launchbox.LaunchBox(temp,platform='psp')
            for tag,region in (('USA','North America'),('Japan','Japan'),('Europe','Europe')):
                game=SimpleNamespace(stem='Game ('+tag+')',title='Game',header=shells.Header('psp'))
                self.assertEqual([x['Region'] for x in provider.candidates(game)],[region])
            game.stem='Game';self.assertEqual(provider.candidates(game),[])
        source=Image.new('RGB',(800,800),'white')
        source.paste((20,80,130),(44,44,766,756))
        label=launchbox.label_crop(source,'Japan','psp')
        self.assertEqual(label.getpixel((324,324)),(20,80,130,255))
        with self.assertRaises(ValueError):launchbox.label_crop(Image.new('RGB',(400,700)),'Japan','psp')

    def test_window_and_plastic_are_opaque_video_corners_stay_on_print(self):
        shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/psp')
        flat=render.umd_texture(shape,Image.new('RGBA',(648,648),(20,80,130,0)))
        self.assertEqual(flat.getpixel((324,324)),(20,80,130,255))
        self.assertEqual(flat.getpixel((324,15))[3],255)
        self.assertEqual(flat.getpixel((0,0))[3],0)
        poster=render.disc_poster(shape,flat)
        for xy in ((106,223),(229,223),(106,289),(229,289)):
            self.assertEqual(poster.getpixel(xy)[3],255)
        self.assertEqual(poster.getpixel((168,168))[3],255)
        for name in ('underside','lid','lid-inside','deck'):
            self.assertTrue((ROOT/f'theme/art-book-slot/_slot/shapes/psp/{name}.tga').exists())


if __name__=='__main__':unittest.main()
