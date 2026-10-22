"""Shipped finish/paint assets and live theme-setting precedence."""
import json,os,struct,subprocess,tempfile,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from tools.themebuild.appearance import COLORS,PAINT,STYLES,STYLE_MODELS,vertex_hash

ROOT=Path(__file__).resolve().parents[1]
SLOT=ROOT/'theme/art-book-slot/_slot'

class ModelAppearance(unittest.TestCase):
    def test_scope_is_completed_recreations_and_options_are_complete(self):
        self.assertEqual(set(PAINT),{'gb','gbc','gba','psp','snes','snes-us','n64','psx','dreamcast'})
        self.assertEqual(set(STYLE_MODELS),set(json.loads((SLOT/'consoles/specs.json').read_text())))
        manifest=json.loads((SLOT/'appearance/manifest.json').read_text())
        self.assertEqual(set(manifest['models']),set(PAINT))
        self.assertEqual(set(manifest['style_models']),set(STYLE_MODELS))
        theme=ET.parse(SLOT.parent/'theme.xml').getroot()
        for key,values in [('slot-model-style',STYLES),('slot-console-color',COLORS)]:
            subset=theme.find("subset[@name='%s']"%key)
            self.assertEqual([n.attrib['name'] for n in subset],list(values))
            for n in subset:self.assertTrue((SLOT.parent/n.text.strip()).is_file())
        for style in STYLES:
            for color in COLORS:
                for model in STYLE_MODELS:
                    b=Image.open(SLOT/'appearance'/style/color/('band-console-'+model+'.png'))
                    self.assertEqual(b.size,(720,58))
                    self.assertEqual(b.getchannel('A').getextrema(),(255,255))
                    self.assertGreater(np.asarray(b)[:,:,:3].sum(),1000)
                    self.assertTrue((SLOT/'appearance'/style/color/'consoles'/model/'body.png').is_file())

    def test_masks_are_bound_to_native_vertex_bytes(self):
        for model in PAINT:
            folder=SLOT/'consoles'/model;raw=(folder/'model.mesh').read_bytes()
            n=struct.unpack_from('<I',raw,8)[0];mask=(folder/'paint.mask').read_bytes()
            magic,count,h=struct.unpack_from('<8sIQ',mask)
            self.assertEqual((magic,count),(b'SCPAINT1',n))
            self.assertEqual(h,vertex_hash(raw[20:20+n*36]))
            self.assertEqual(len(mask),20+n)
            weights=np.frombuffer(mask,'uint8',offset=20)
            self.assertGreater(np.count_nonzero(weights),100)
            self.assertGreater(np.count_nonzero(weights==0),100)

    def test_unpainted_families_support_both_finishes_and_keep_original_colours(self):
        for model in set(STYLE_MODELS)-set(PAINT):
            folder=SLOT/'appearance'
            real=np.array(Image.open(folder/'realistic/original/consoles'/model/'body.png'))
            cel=np.array(Image.open(folder/'cel/original/consoles'/model/'body.png'))
            red=np.array(Image.open(folder/'realistic/red/consoles'/model/'body.png'))
            self.assertGreater(np.any(real!=cel,axis=2).sum(),100,model)
            np.testing.assert_array_equal(real,red,err_msg=model)

    def test_realistic_removes_contours_and_paint_changes_the_housing(self):
        for model in PAINT:
            folder=SLOT/'appearance'
            cel=np.array(Image.open(folder/'cel/original/consoles'/model/'body.png'))
            real=np.array(Image.open(folder/'realistic/original/consoles'/model/'body.png'))
            red=np.array(Image.open(folder/'realistic/red/consoles'/model/'body.png'))
            self.assertEqual(cel.shape,real.shape)
            self.assertGreater(np.any(cel!=real,axis=2).sum(),100)
            self.assertGreaterEqual((cel[:,:,3]>0).sum(),(real[:,:,3]>0).sum())
            self.assertGreater(np.any(red[:,:,:3]!=real[:,:,:3],axis=2).sum(),100)
            np.testing.assert_array_equal(red[:,:,3],real[:,:,3])

    @unittest.skipUnless(os.name=='posix','POSIX launch environment')
    def test_global_choices_and_live_system_override_reach_the_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);helper=root/'helper';helper.touch();helper.chmod(0o755)
            settings=root/'settings';profile=root/'profile'
            settings.write_text('<config><string name="ThemeSet" value="art-book-slot"/>'
                '<string name="subset.gba.slot-console-color" value="white"/></config>')
            profile.write_bytes(b'subset.slot-model-style=realistic\rsubset.slot-console-color=red\r')
            r=subprocess.run(['sh','-c','. "$1"; SLOT_HELPER="$2"; SLOT_SETTINGS="$3"; SLOT_THEME_SETTINGS="$4"; '
                'slot_enabled /userdata/roms/gba/Game.gba && printf "%s %s" "$SLOT_MODEL_STYLE" "$SLOT_CONSOLE_COLOR"',
                'appearance',str(SLOT/'launch/common.sh'),str(helper),str(settings),str(profile)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(r.stdout,'realistic white')
            # No saved choice means the Realistic default; an explicit Cel is kept.
            for saved,expected in ((b'',b'realistic original'),(b'subset.slot-model-style=cel\r',b'cel original')):
                profile.write_bytes(saved)
                settings.write_text('<config><string name="ThemeSet" value="art-book-slot"/></config>')
                r=subprocess.run(['sh','-c','. "$1"; SLOT_HELPER="$2"; SLOT_SETTINGS="$3"; SLOT_THEME_SETTINGS="$4"; '
                    'slot_enabled /userdata/roms/gba/Game.gba && printf "%s %s" "$SLOT_MODEL_STYLE" "$SLOT_CONSOLE_COLOR"',
                    'appearance',str(SLOT/'launch/common.sh'),str(helper),str(settings),str(profile)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout,expected)

if __name__=='__main__':unittest.main()
