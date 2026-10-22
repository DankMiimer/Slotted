"""PS1 boot identity, regional disc selection, physical opacity and cache completeness."""
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
from slotcart import discs,launchbox,render,shells
from slotcart import __main__ as baker
from slotcart.library import CrcCache,scan


class PsxIntegration(unittest.TestCase):
    def test_bounded_boot_identity_cue_and_chd_sha_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'psx';folder.mkdir();cache=CrcCache(root/'cache')
            data=b'BOOT = cdrom:\\GAME\\SLUS_012.51;1\r\n'+bytes(128)
            (folder/'Game.bin').write_bytes(data)
            (folder/'Game.cue').write_text('FILE "Game.bin" BINARY\n TRACK 01 MODE2/2352')
            head=bytearray(124);head[:8]=b'MComprHD';head[12:16]=(5).to_bytes(4,'big');head[64:84]=bytes(range(20))
            (folder/'Final Fantasy IX (Disc 2).chd').write_bytes(head)
            cache.identities[bytes(range(20)).hex()]='SLUS-01295'
            (folder/'Empty.iso').touch()
            with patch.object(discs.shutil,'which',return_value=None):games=scan(root,['psx'],cache)
            self.assertEqual(len(games),3)
            self.assertEqual({g.header.code for g in games},{'SLUS-01251','SLUS-01295'})
            for g in games:self.assertEqual(discs.region(g),('North America',));self.assertEqual(g.crc,'')
            cache.save();self.assertEqual(CrcCache(root/'cache').identities,cache.identities)
            # The bin's serial outside the bounded boot area must not be found.
            (folder/'Large.iso').write_bytes(bytes(discs.LIMIT)+data)
            self.assertEqual(discs.identify(folder/'Large.iso',{}),b'')

    def test_unknown_region_and_ambiguous_multidisc_never_guess(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'launchbox';folder.mkdir()
            images=[dict(DatabaseID='527',FileName=file,Region='North America',Type='Disc')
                    for file in launchbox.DISC_NUMBERS]
            images.append(dict(DatabaseID='527',FileName='europe.png',Region='Europe',Type='Disc'))
            (folder/'psx.json').write_text(json.dumps(dict(games={'527':['Final Fantasy IX']},images=images)))
            provider=launchbox.LaunchBox(temp,platform='psx')
            game=SimpleNamespace(stem='Final Fantasy IX (Disc 3)',title='Final Fantasy IX',header=shells.Header('psx',code='SLUS-01296'))
            self.assertEqual([i['FileName'] for i in provider.candidates(game)],['03a2d77e-1dbf-4348-be24-aa43974afeaa.png'])
            game.header=shells.Header('psx');self.assertEqual(provider.candidates(game),[])
            game.stem='Final Fantasy IX (Europe) (Disc 3)';self.assertEqual(provider.candidates(game),[])

    def test_ring_is_opaque_bore_open_and_video_corners_on_disc(self):
        shape=render.Shape(ROOT/'theme/art-book-slot/_slot/shapes/psx')
        flat=render.disc_texture(shape,Image.new('RGBA',(648,648),(20,90,140,0)))
        self.assertEqual(flat.getpixel((324,80)),(20,90,140,255))
        self.assertEqual(flat.getpixel((324,324))[3],0)
        self.assertEqual(flat.getpixel((0,0))[3],0)
        poster=render.disc_poster(shape,flat)
        for xy in ((98,225),(237,225),(98,298),(237,298)):
            self.assertEqual(poster.getpixel(xy)[3],255)
        self.assertEqual(poster.getpixel((168,168))[3],0)
        with self.assertRaises(ValueError):launchbox.label_crop(Image.new('RGB',(600,900)),'Europe','psx')

    def test_missing_motion_texture_is_rebaked_and_dump_formats_share_face(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'roms/psx';folder.mkdir(parents=True)
            (folder/'Unknown (Disc 1).bin').write_bytes(b'BOOT = cdrom:\\SLES_123.45;1')
            (folder/'Unknown (Disc 1).cue').write_text('FILE "Unknown (Disc 1).bin" BINARY')
            jobs=[]
            class Pool:
                def __init__(self,*a,initializer):initializer()
                def __enter__(self):return self
                def __exit__(self,*a):pass
                def imap_unordered(self,f,items,**kw):jobs.extend(items);return map(f,items)
            class NoArt:
                def __init__(self,*a,**kw):pass
                def candidates(self,g):return []
            with patch.object(baker,'Pool',Pool),patch.object(baker.labels,'ArtSet',NoArt),patch.object(baker,'LaunchBox',NoArt):
                args=['--roms',str(root/'roms'),'--systems','psx','--offline','--cache',str(root/'cache')]
                self.assertEqual(baker.main(args),0);self.assertEqual(len(jobs),1)
                jobs.clear();self.assertEqual(baker.main(args),0);self.assertEqual(jobs,[])
                raw=folder/'media/slotcarts/Unknown (Disc 1).disc.png';self.assertTrue(raw.exists())
                raw.unlink();self.assertEqual(baker.main(args),0);self.assertEqual(len(jobs),1)


if __name__=='__main__':unittest.main()
