"""DS headers, bounded library reads, region-safe scans and opaque game cards."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import launchbox,render,shells
from slotcart.library import CrcCache,scan,HEAD


class DsIntegration(unittest.TestCase):
    def test_native_and_zipped_roms_read_only_the_header(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'nds';folder.mkdir()
            head=bytearray(HEAD);head[:12]=b'POKEMON HG  ';head[12:16]=b'IPKE'
            with (folder/'HeartGold (USA).nds').open('wb') as stream:
                stream.write(head);stream.seek(512*1024*1024);stream.write(b'X')
            with zipfile.ZipFile(folder/'Archive.zip','w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('readme.txt',b'No ROM here')
                archive.writestr('Game.nds',head+bytes(100000))
            (folder/'media').mkdir();(folder/'media/Ignore.nds').touch()
            with patch('slotcart.library.read_rom',side_effect=AssertionError('full ROM read')):
                games=scan(root,['nds'],CrcCache(root/'cache'))
            self.assertEqual(len(games),2)
            for game in games:
                self.assertEqual((game.crc,len(game.head),game.header.code),('',HEAD,'IPKE'))
                self.assertEqual(shells.choose(game.header,game.stem,{}),('nds',shells.NDS_IR_BLACK))
            self.assertEqual(shells.outline_for(shells.read_header('nds',b'')),'nds')
            self.assertEqual(shells.default_shell(shells.read_header('nds',b'')),shells.NDS_GREY)

    def test_exact_titles_and_regions_do_not_borrow_retail_art_for_hacks(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'launchbox';folder.mkdir()
            images=[dict(DatabaseID='1',FileName=region+'.png',Region=region,Type='Cart - Front')
                    for region in ('North America','Europe','Japan')]
            (folder/'nds.json').write_text(json.dumps(dict(games={'1':['Mario Kart DS']},images=images)))
            provider=launchbox.LaunchBox(temp,platform='nds')
            for tag,region in (('USA','North America'),('Europe','Europe'),('Japan','Japan')):
                game=SimpleNamespace(stem='Mario Kart DS ('+tag+')',title='Mario Kart DS')
                self.assertEqual([x['Region'] for x in provider.candidates(game)],[region])
            game=SimpleNamespace(stem='Mario Kart DS - Custom Tracks (Europe)',title='Mario Kart DS - Custom Tracks')
            self.assertEqual(provider.candidates(game),[])
        source=Image.new('RGB',(312,341),'black');source.paste((20,80,130),(23,32,289,302))
        label=launchbox.label_crop(source,'Europe','nds')
        self.assertEqual(label.getpixel((label.width//2,label.height//2)),(20,80,130))
        with self.assertRaises(ValueError):launchbox.label_crop(Image.new('RGB',(700,400)),'Europe','nds')

    def test_card_video_well_and_connector_back_are_opaque(self):
        shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/nds')
        card=render.face(shape,shells.NDS_GREY,Image.new('RGBA',shape.well_size,(20,80,130,0)))
        for point in ((31,110),(280,110),(31,269),(280,269),(156,167)):
            self.assertEqual(card.getpixel(point)[3],255)
        self.assertEqual(card.getpixel((310,0))[3],0)
        self.assertEqual(card.getpixel((4,194))[3],0)  # Side latch clearance.
        self.assertEqual(card.getpixel((17,194))[3],255)
        self.assertEqual(card.getpixel((4,333))[3],0)  # Broad lower corner.
        self.assertEqual(card.getpixel((307,333))[3],255)
        rear=Image.open(ROOT/'theme/art-book-slot/_slot/shapes/nds/rear.png')
        self.assertEqual(rear.getpixel((156,160))[3],255)
        self.assertEqual(rear.getpixel((33,280)),(181,143,63,255))

    def test_variable_scan_border_preserves_the_top_branding(self):
        for top in (20,35):
            with self.subTest(top=top):
                source=Image.new('RGB',(312,341),(45,47,50))
                source.paste('white',(23,top,289,70))
                source.paste('black',(70,top+5,245,top+15))
                source.paste((20,80,130),(23,70,289,302))
                label=launchbox.label_crop(source,'Europe','nds')
                self.assertEqual(label.getpixel((label.width//2,0)),(255,255,255))


if __name__=='__main__':unittest.main()
