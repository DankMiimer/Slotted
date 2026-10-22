"""Physical presentation contracts: full silhouettes, input state and hook ownership."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import tempfile
import unittest

from PIL import Image,ImageDraw
from tools.themebuild.stage import compose, HEIGHT

ROOT=Path(__file__).resolve().parents[1]


class BrowseStage(unittest.TestCase):
    def test_tall_and_wide_housings_keep_the_complete_uniform_silhouette(self):
        for size in ((90,300),(500,140)):
            with self.subTest(size=size):
                image=Image.new('RGBA',(720,480))
                x,y=50,50
                ImageDraw.Draw(image).rectangle((x,y,x+size[0]-1,y+size[1]-1),fill=(90,130,180,255))
                stage,spec=compose(image)
                left,top,width,height=spec['bounds']
                self.assertLessEqual(abs(width/height-size[0]/size[1]),.025)
                self.assertGreaterEqual(top,0)
                self.assertLessEqual(top+height,HEIGHT)
                self.assertGreaterEqual(left,0)
                self.assertLessEqual(left+width,720)
                self.assertEqual(stage.getpixel((0,0))[3],0)
                self.assertGreater(stage.getpixel((left+width//2,top+height//2))[3],240)

    def test_current_appearance_variants_have_full_model_stage_renders(self):
        folder=ROOT/'theme/art-book-slot/_slot/stage'
        manifest=json.loads((folder/'manifest.json').read_text())
        for key,entry in manifest['renders'].items():
            style,color,model=key.split('/')
            with self.subTest(key=key):
                with Image.open(folder/style/color/('browse-console-'+model+'.png')) as image:
                    self.assertEqual(image.size,(720,HEIGHT))
                    self.assertIsNotNone(image.getchannel('A').getbbox())
                self.assertGreater(entry['bounds'][3],30)

    def test_registered_lcds_cover_glass_and_have_nonzero_area(self):
        folder=ROOT/'theme/art-book-slot/_slot/stage'
        screens=json.loads((folder/'screens.json').read_text())
        self.assertEqual({key:len(value['quads']) for key,value in screens.items()},
                         {'gb':1,'gbc':1,'gba':1,'nds':2,'psp':1})
        for model,spec in screens.items():
            with Image.open(folder/'front'/(model+'.png')) as image:
                self.assertEqual(list(image.size),spec['size'])
                for quad in spec['quads']:
                    with self.subTest(model=model,quad=quad):
                        area=abs(sum(quad[i][0]*quad[(i+1)%4][1]-quad[(i+1)%4][0]*quad[i][1] for i in range(4)))/2
                        self.assertGreater(area,.07)
                        centre=[sum(point[i] for point in quad)/4 for i in range(2)]
                        pixel=image.getpixel((round(centre[0]*image.width),round(centre[1]*image.height)))
                        self.assertGreater(pixel[3],240)
                        # The original DMG has the brighter olive reflective LCD.
                        self.assertLess(sum(pixel[:3])/3,130 if model=='gb' else 70,'LCD must land on glass, not housing')

    def test_panasonic_live_surface_is_inside_blank_glass(self):
        folder=ROOT/'theme/art-book-slot/_slot/stage/tv'
        profile=json.loads((folder/'profile.json').read_text())
        self.assertEqual(profile['license'],'CC BY 4.0')
        with Image.open(folder/'panasonic.png') as image:
            self.assertEqual(list(image.size),profile['size'])
            for a,b in ((0,0),(1,0),(1,1),(0,1),(.5,.5)):
                q=profile['quad']
                point=[(1-b)*((1-a)*q[0][i]+a*q[1][i])+b*((1-a)*q[3][i]+a*q[2][i]) for i in (0,1)]
                pixel=image.getpixel((int(point[0]*image.width),int(point[1]*image.height)))
                self.assertGreater(pixel[3],240)
                self.assertLess(max(pixel[:3]),130,'Content must remain on the glass')
                self.assertGreater(pixel[1]-pixel[0],8,'Glass must retain its teal tint; do not cover the grey bezel')
        raw=(ROOT/'third_party/models/damiantoons-panasonic/model.glb').read_bytes()
        length=struct.unpack_from('<I',raw,12)[0]
        model=json.loads(raw[20:20+length])
        self.assertEqual(len(model['images']),6,'Keep housing maps, exclude the three broadcast screen maps')
        self.assertNotIn('TVScreen',[m.get('name') for m in model['materials']])
        glass=next(m for m in model['materials'] if m.get('name')=='Blank live CRT glass')
        self.assertNotIn('baseColorTexture',glass['pbrMetallicRoughness'])

    def test_every_tv_profile_registers_blank_glass_and_its_licence(self):
        folder=ROOT/'theme/art-book-slot/_slot/stage/tv'
        registry=json.loads((folder/'profiles.json').read_text())
        self.assertEqual(registry['default'],'panasonic')
        header=(ROOT/'tools/frontend/overlay/es-app/src/components/SlotTelevision.h').read_text()
        theme=(ROOT/'theme/art-book-slot/theme.xml').read_text()
        credits=(ROOT/'theme/art-book-slot/_slot/MODEL_CREDITS.txt').read_text(encoding='utf-8')
        for profile in registry['profiles']:
            with self.subTest(tv=profile['id']):
                self.assertIn('"%s","%s"'%(profile['id'],profile['image']),header)
                self.assertIn('<include name="%s"'%profile['id'],theme)
                self.assertIn(profile['source'],credits)
                with Image.open(ROOT/'theme/art-book-slot/_slot'/profile['image']) as image:
                    self.assertAlmostEqual(image.width/image.height,profile['aspect'],places=4)
                    q=profile['quad']
                    for a,b in ((0,0),(1,0),(1,1),(0,1),(.5,.5)):
                        point=[(1-b)*((1-a)*q[0][i]+a*q[1][i])+b*((1-a)*q[3][i]+a*q[2][i]) for i in (0,1)]
                        pixel=image.getpixel((int(point[0]*image.width),int(point[1]*image.height)))
                        self.assertGreater(pixel[3],240)
                        self.assertLess(max(pixel[:3]),130,'Content must remain on the dark glass')
        retro=json.loads((folder/'retro.json').read_text())
        self.assertEqual(retro['license'],'CC BY-NC 4.0')


@unittest.skipUnless(os.name=='posix' and shutil.which('sh'),'requires Linux /proc and a POSIX shell')
class FrontendOwnership(unittest.TestCase):
    def test_only_a_matching_live_process_and_complete_record_owns_launch(self):
        source=ROOT/'theme/art-book-slot/_slot/launch/frontend-owned.sh'
        pid=os.getpid()
        stat=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
        start=stat[19]
        rom='/userdata/roms/gba/Cart & $(echo harmless) (Europe).gba'
        good=['1',str(pid),start,'0123456789abcdef'*2,rom]
        cases=[(good,rom,True), (good,rom+'x',False),
               (['2',*good[1:]],rom,False),
               ([good[0],'99999999',*good[2:]],rom,False),
               ([*good[:2],str(int(start)+1),*good[3:]],rom,False),
               ([*good[:3],'not-a-valid-token',rom],rom,False),
               ([*good,'extra'],rom,False), (good[:-1],rom,False)]
        with tempfile.TemporaryDirectory() as temporary:
            record=Path(temporary)/'frontend-owned'
            for fields,requested,expected in cases:
                with self.subTest(fields=fields):
                    record.write_text('\n'.join(fields)+'\n')
                    result=subprocess.run(['sh','-c','. "$1"; SLOT_STATE="$2"; slot_frontend_owned "$3"','slot-owner',str(source),temporary,requested],capture_output=True,text=True)
                    self.assertEqual(result.returncode==0,expected,result.stderr)
            literal=Path(temporary)/'Cart & $(echo harmless) (Europe).gba'
            literal.touch()
            record.write_text('\n'.join([*good[:-1],str(literal)])+'\n')
            escaped=str(literal).replace(' ','\\ ').replace('(','\\(').replace(')','\\)')
            result=subprocess.run(['sh','-c','. "$1"; SLOT_STATE="$2"; slot_frontend_owned "$3"','slot-owner',str(source),temporary,escaped],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
