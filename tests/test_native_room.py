"""Native UI capture fixture/comparison checks without a frontend build or display."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from PIL import Image
from tools.frontend.tests import native_room
from tools.frontend.tests.room_fixture import make

def capture(folder,colour=(10,20,30),tv='panasonic',width=720,changed=None):
    folder.mkdir(parents=True)
    for kind,size in [('room',(width,480)),('ui',(640,480))]:
        image=Image.new('RGB',size,colour)
        if changed and kind=='room':image.putpixel(changed,(255,0,255))
        image.save(folder/('home-'+kind+'.png'))
    (folder/'capture.json').write_text(json.dumps(dict(tv=tv,width=width,height=480,scriptSha256='0'*64,
        nativeAudioVideo=False,shots=[dict(name='home',frame=10)])))
    return folder

class NativeRoomComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)

    def test_identical_captures_pass_exactly(self):
        result=native_room.compare(capture(self.root/'a'),capture(self.root/'b'),self.root/'diff')
        self.assertTrue(result['passed']);self.assertEqual(result['comparison'],'exact-rgb-no-masks')
        self.assertEqual([row['changedPixels'] for row in result['images']],[0,0])

    def test_single_changed_pixel_fails_and_keeps_difference_image(self):
        result=native_room.compare(capture(self.root/'a',changed=(700,5)),capture(self.root/'b'),self.root/'diff')
        self.assertFalse(result['passed'])
        room=next(row for row in result['images'] if row['file']=='home-room.png')
        self.assertEqual((room['changedPixels'],room['bounds']),(1,(700,5,701,6)))
        self.assertTrue((self.root/'diff/home-room.png').is_file());self.assertFalse((self.root/'diff/home-ui.png').exists())

    def test_different_conditions_are_refused_instead_of_compared(self):
        for name,options in [('tv',dict(tv='pvm')),('width',dict(width=640))]:
            with self.subTest(name),self.assertRaisesRegex(ValueError,'conditions differ'):
                native_room.compare(capture(self.root/(name+'-a'),**options),capture(self.root/(name+'-b')),self.root/(name+'-diff'))
            self.assertFalse((self.root/(name+'-diff')).exists())

    def test_existing_comparison_folder_is_never_reused(self):
        (self.root/'diff').mkdir()
        with self.assertRaises(FileExistsError):native_room.compare(capture(self.root/'a'),capture(self.root/'b'),self.root/'diff')

    def test_run_checks_size_and_binary_receipt_before_creating_output(self):
        build=self.root/'build';(build/'frontend').mkdir(parents=True);(build/'frontend/emulationstation').write_bytes(b'host binary')
        (build/'host-build.json').write_text(json.dumps(dict(binarySha256='0'*64)))
        with self.assertRaisesRegex(ValueError,'640x480 or 720x480'):native_room.run(build,self.root,self.root/'out',width=800)
        with self.assertRaisesRegex(ValueError,'receipt differs'):native_room.run(build,self.root,self.root/'out')
        self.assertFalse((self.root/'out').exists())

class RoomFixtureTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.source=self.root/'source';(self.source/'theme/slotted').mkdir(parents=True);(self.source/'theme/slotted/theme.xml').write_text('<theme/>')
        (self.source/'theme/art-book-slot/_slot').mkdir(parents=True);self.frontend=self.root/'frontend';(self.frontend/'resources').mkdir(parents=True)
        try:os.symlink(self.frontend,self.root/'link-check',target_is_directory=True)
        except OSError:self.skipTest('Symlinks unavailable (native captures run on Linux)')

    def test_unknown_tv_and_existing_fixture_are_refused(self):
        with self.assertRaisesRegex(ValueError,'Unsupported test TV'):make(self.root/'box',self.source,self.frontend,'crt')
        (self.root/'used').mkdir()
        with self.assertRaises(FileExistsError):make(self.root/'used',self.source,self.frontend)
        self.assertFalse((self.root/'box').exists())

    def test_fixture_is_synthetic_and_isolated(self):
        result=make(self.root/'box',self.source,self.frontend,'oldtv')
        self.assertEqual((result['synthetic'],result['tv'],result['motion']),(True,'oldtv','reduced'))
        user=self.root/'box/userdata'
        settings={item.get('name'):item.get('value') for item in ET.parse(user/'system/configs/emulationstation/es_settings.cfg').getroot()}
        self.assertEqual((settings['ThemeSet'],settings['subset.slot-tv-model']),('Slotted','oldtv'))
        roms=[p for p in (user/'roms').rglob('*') if p.is_file() and p.parent.name!='images' and p.name!='gamelist.xml']
        self.assertTrue(roms);self.assertTrue(all(p.stat().st_size==0 for p in roms))
        self.assertEqual((user/'themes/Slotted/theme.xml').resolve(),(self.source/'theme/slotted/theme.xml').resolve())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),['box','frontend','link-check','source'])

if __name__=='__main__':unittest.main()
