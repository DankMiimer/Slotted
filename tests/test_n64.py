"""N64 dump formats, regional plastics and independent portrait label crops."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import struct
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import labels, launchbox, render, shells
from slotcart import __main__ as baker
from slotcart.library import CrcCache, scan


class N64Integration(unittest.TestCase):
    def test_duplicate_formats_share_one_job_and_keep_scraped_logo(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            folder=root/'roms'/'n64'
            folder.mkdir(parents=True)
            for suffix in ('.n64','.z64'):
                (folder/('Unlisted Game (USA)'+suffix)).write_bytes(b'\x80\x37\x12\x40'+bytes(1020))
            logo=folder/'logo.png'
            Image.new('RGB',(100,50),'navy').save(logo)
            (folder/'gamelist.xml').write_text('<gameList><game><path>./Unlisted Game (USA).n64</path>'
                '<name>Unlisted Game</name><marquee>./logo.png</marquee></game></gameList>')
            jobs=[]
            class SerialPool:
                def __init__(self,*args,initializer): initializer()
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def imap_unordered(self,function,items,**kwargs):
                    jobs.extend(items)
                    return map(function,items)
            class NoHandheldArt:
                def __init__(self,*args): pass
            class NoConsoleArt:
                def __init__(self,*args,**kwargs): pass
                def candidates(self,game): return []
            with patch.object(baker,'Pool',SerialPool), patch.object(labels,'ArtSet',NoHandheldArt), \
                 patch.object(baker,'LaunchBox',NoConsoleArt):
                args=['--roms',str(root/'roms'),'--systems','n64','--offline','--cache',str(root/'cache')]
                self.assertEqual(baker.main(args),0)
                self.assertEqual(len(jobs),1)
                self.assertEqual(jobs[0][4],'logo')
                jobs.clear()
                self.assertEqual(baker.main(args),0)
                self.assertEqual(jobs,[])
            face=folder/'media'/'slotcarts'/'Unlisted Game (USA).png'
            self.assertTrue(face.exists())
            self.assertTrue(face.with_name('Unlisted Game (USA).back.png').exists())

    def test_invalid_ancillary_png_metadata_does_not_discard_valid_pixels(self):
        image = Image.new('RGB',(400,268),'navy')
        output=BytesIO()
        image.save(output,'PNG')
        data=output.getvalue()
        kind,payload=b'tEXt',b'Author\0cartridge photograph'
        chunk=struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',0)
        # Insert a corrupt ancillary chunk just after the valid IHDR.
        damaged=data[:33]+chunk+data[33:]
        repaired=launchbox.image_bytes(damaged)
        self.assertEqual(repaired,data)
        self.assertEqual(Image.open(BytesIO(repaired)).tobytes(),image.tobytes())

    def test_corrupt_critical_png_data_is_not_repaired(self):
        output=BytesIO()
        Image.new('RGB',(10,10)).save(output,'PNG')
        data=bytearray(output.getvalue())
        data[29]^=1  # IHDR checksum; unlike metadata this is essential image data.
        with self.assertRaises(ValueError):
            launchbox.image_bytes(bytes(data))

    def test_three_dump_byte_orders_and_zip_preserve_platform_and_title(self):
        data = bytearray(1024)
        data[:4] = b'\x80\x37\x12\x40'
        data[0x20:0x34] = b'ART BOOK SLOT       '
        # This must never select the GB Color shell or handheld art provider.
        data[0x143] = 0xC0
        swapped = bytes(data[i^1] for i in range(len(data)))
        little = b''.join(data[i:i+4][::-1] for i in range(0,len(data),4))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'n64h'
            folder.mkdir()
            for suffix, payload in (('.z64',data),('.v64',swapped),('.n64',little)):
                (folder/('Game'+suffix)).write_bytes(payload)
            with zipfile.ZipFile(folder/'Game.zip','w') as archive:
                archive.writestr('Game.V64',swapped)
            games = scan(root,['n64h'],CrcCache(root/'cache'))
            self.assertEqual(len(games),4)
            class HandheldArt:
                def entry(self, crc):
                    raise AssertionError('N64 must not use handheld CRC art')
            for game in games:
                self.assertEqual(game.header.platform,'n64')
                self.assertEqual(game.header.title,'ART BOOK SLOT')
                self.assertEqual(shells.choose(game.header,game.stem,{}),('n64',shells.N64_GREY))
                self.assertEqual(labels.candidates(game,HandheldArt())[0][0],'text')

    def test_verified_regional_colours_and_user_override(self):
        header = shells.read_header('n64',b'')
        for name, shell in (('Donkey Kong 64 (USA)',shells.N64_YELLOW),
                            ('Donkey Kong 64 (Europe)',shells.N64_GREY),
                            ('Pokemon Stadium 2 (USA)',shells.N64_GOLD),
                            ('Pokémon Stadium 2 (USA)',shells.N64_GOLD),
                            ('Spider-Man (USA)',shells.N64_RED),
                            ('Spider-Man (Europe)',shells.N64_GREY),
                            ('Turok 2 - Seeds of Evil (USA)',shells.N64_BLACK),
                            ("Army Men - Sarge's Heroes 2 (USA)",shells.N64_GREEN)):
            self.assertEqual(shells.choose(header,name,{}),('n64',shell))
        name='Donkey Kong 64 (USA)'
        override=shells.parse_overrides(name+' = rounded 112233 clear')
        self.assertEqual(shells.choose(header,name,override),('n64',shells.Shell((17,34,51),'clear')))

    def test_portrait_crop_excludes_body_with_transparent_padding(self):
        cart=Image.new('RGBA',(400,268),'grey')
        box=tuple(round(v*n) for v,n in zip((.260,.108,.742,.914),(400,268,400,268)))
        ImageDraw.Draw(cart).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill='navy')
        padded=Image.new('RGBA',(440,308))
        padded.paste(cart,(20,20))
        a=launchbox.label_crop(cart,'North America','n64')
        b=launchbox.label_crop(padded,'North America','n64')
        self.assertEqual(a.tobytes(),b.tobytes())
        self.assertLess(a.width,a.height)
        self.assertEqual(a.getpixel((a.width//2,a.height//2)),(0,0,128))
        with self.assertRaises(ValueError):
            launchbox.label_crop(Image.new('RGB',(304,337)),'North America','n64')

    def test_offline_platform_isolation_and_own_label_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            cache=root/'launchbox'
            cache.mkdir()
            image={'DatabaseID':'1','FileName':'shared.png','Region':'North America','Type':'Cart - Front'}
            for platform in ('n64','snes'):
                (cache/(platform+'.json')).write_text(json.dumps({'games':{'1':['Shared Game']},'images':[image]}))
            n64=launchbox.LaunchBox(root,offline=True,platform='n64')
            snes=launchbox.LaunchBox(root,offline=True,platform='snes')
            self.assertNotEqual(n64.label_path(image),snes.label_path(image))
            self.assertEqual(n64.candidates(SimpleNamespace(stem='Shared Game (USA)',title='Shared Game')),[])
            path=n64.label_path(image)
            path.parent.mkdir()
            Image.new('RGB',(100,120)).save(path)
            own=root/'media'/'labels'/'Shared Game (USA).png'
            own.parent.mkdir(parents=True)
            Image.new('RGB',(100,120)).save(own)
            game=SimpleNamespace(kind='n64',stem='Shared Game (USA)',title='Shared Game',dir=root,crc='',marquee='')
            plans=labels.candidates(game,object(),carts={'n64':n64})
            self.assertEqual([p[0] for p in plans],['own','cart-scan','text'])

    def test_opaque_body_and_labels_for_all_front_plastics(self):
        shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/n64')
        for shell in (shells.N64_GREY,shells.N64_YELLOW,shells.N64_GOLD):
            face=render.face(shape,shell,Image.new('RGB',(100,120),'navy'))
            self.assertEqual(face.getchannel('A').crop(shape.well).getextrema(),(255,255))
            self.assertEqual(face.getpixel((40,150))[3],255)
            self.assertEqual(face.getpixel((0,0))[3],0)


if __name__ == '__main__':
    unittest.main()
