"""Sega dump formats, regional mouldings and cropped labels on opaque cartridges."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import labels, launchbox, render, shells
from slotcart.library import CrcCache, scan
from tools.themebuild.geometry import MD, MD_JP, MD_EA


class MegaDriveIntegration(unittest.TestCase):
    def test_dumps_zip_and_alias_keep_console_identity(self):
        head=bytearray(0x150)
        head[0x100:0x104]=b'SEGA'
        head[0x120:0x130]=b'ART BOOK SLOT   '
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            folder=root/'genesis'
            folder.mkdir()
            for suffix in ('.md','.bin','.gen','.smd'):
                (folder/('Game'+suffix)).write_bytes(head if suffix!='.smd' else bytes(2048))
            with zipfile.ZipFile(folder/'Game.zip','w') as archive:
                archive.writestr('Game.MD',head)
            games=scan(root,['genesis'],CrcCache(root/'cache'))
            self.assertEqual(len(games),5)
            class NoHandheldArt:
                def entry(self,crc): raise AssertionError('MD must not query handheld art')
            for game in games:
                self.assertEqual(game.header.platform,'md')
                self.assertEqual(shells.choose(game.header,game.stem,{}),('md',shells.MD_BLACK))
                self.assertEqual(labels.candidates(game,NoHandheldArt())[0][0],'text')
                self.assertEqual(game.header.title,'' if game.path.suffix=='.smd' else 'ART BOOK SLOT')

    def test_region_tags_and_ea_title_select_physical_body(self):
        header=shells.read_header('md',b'')
        for stem,shape in (('Gunstar Heroes (USA)','md'),('Gunstar Heroes (Japan)','md-jp'),
                           ('Japan Adventure (Europe)','md'),('Sonic 2 (World)','md'),
                           ('Blades of Vengeance','md-ea')):
            self.assertEqual(shells.choose(header,stem,{}),(shape,shells.MD_BLACK))
        stem='Gunstar Heroes (Japan)'
        override=shells.parse_overrides(stem+' = rounded 112233 solid')
        self.assertEqual(shells.choose(header,stem,override),('md-jp',shells.Shell((17,34,51))))
        self.assertEqual(launchbox.regions('Game (Japan)','md'),('Japan',))
        self.assertEqual(launchbox.regions('Game (USA, Japan)','md'),('North America',))
        self.assertEqual(launchbox.regions('Game (Europe, Japan)','md')[0],'Europe')

    def test_common_video_stays_inside_every_label_and_bodies_are_opaque(self):
        for geometry in (MD,MD_JP,MD_EA):
            shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes'/geometry.name)
            video=tuple(round(v*n) for v,n in zip(MD.video_well,(360,270,360,270)))
            x0,y0,x1,y1=shape.well
            self.assertTrue(x0<video[0]<video[2]<x1 and y0<video[1]<video[3]<y1)
            face=render.face(shape,shells.MD_BLACK,Image.new('RGB',(200,200),'navy'))
            self.assertEqual(face.getchannel('A').crop(video).getextrema(),(255,255))
            self.assertEqual(face.getpixel((180,240))[3],255)
            self.assertEqual(face.getpixel((0,0))[3],0)
            if geometry.name=='md-ea':
                r,g,b,a=face.getpixel((60,60))
                self.assertGreater(r,b*3)
                self.assertGreater(g,b*2)
                self.assertEqual(a,255)

    def test_western_japan_and_ea_crops_omit_photographed_body(self):
        for size,region,box in (((600,390),'Europe',(.145,.012,.86,.910)),
                                ((600,390),'Japan',(.129,.016,.858,.872)),
                                ((600,556),'Europe',(.213,.011,.923,.831))):
            photo=Image.new('RGBA',size,'grey')
            x0,y0,x1,y1=tuple(round(v*n) for v,n in zip(box,size*2))
            ImageDraw.Draw(photo).rectangle((x0,y0,x1-1,y1-1),fill='navy')
            padded=Image.new('RGBA',(size[0]+40,size[1]+40))
            padded.paste(photo,(20,20))
            crop=launchbox.label_crop(padded,region,'md')
            self.assertEqual(crop.getpixel((crop.width//2,crop.height//2)),(0,0,128))
            self.assertEqual(crop.tobytes(),launchbox.label_crop(photo,region,'md').tobytes())
        with self.assertRaises(ValueError):
            launchbox.label_crop(Image.new('RGB',(200,350)),'Europe','md')


if __name__=='__main__':
    unittest.main()
