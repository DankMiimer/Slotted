"""The scene's standard three-quarter view, shared by TVs, home consoles and handheld reading poses."""
import json
import re
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / 'theme/art-book-slot/_slot'
LAUNCH = ROOT / 'tools/slotlaunch'
OVERLAY = ROOT / 'tools/frontend/overlay/es-app/src/components'


class StandardView(unittest.TestCase):
    def test_home_consoles_face_opposite_tvs_without_changing_handheld_reading(self):
        psx = (LAUNCH / 'psx.h').read_text(encoding='utf-8')
        self.assertIn('#define SLOT_STANDARD_YAW_DEGREES (-22)', psx)
        self.assertIn('#define SLOT_HOME_YAW_DEGREES (22)', psx)
        self.assertIn('#define PSX_PHI (35*PSX_PI/180)', psx)
        native = (OVERLAY / 'SlotNative.c').read_text(encoding='utf-8')
        self.assertNotIn('kind==6?-8', native)                       # PSX/Dreamcast no longer face 8 degrees
        self.assertEqual(native.count('SLOT_STANDARD_YAW_DEGREES'), 2)   # camera and projection agree
        self.assertIn('console_matrix_turn(target,SLOT_STANDARD_YAW,target_lean);', native)
        scene = (LAUNCH / 'ps1-scene.h').read_text(encoding='utf-8')
        self.assertIn('double yaw=SLOT_HOME_YAW', scene)
        self.assertIn('+yaw*travel', scene)                           # the disc lands aligned with the console
        gl = (LAUNCH / 'console-gl.h').read_text(encoding='utf-8')
        turn = gl.split('static void console_matrix_turn')[1].split('static bool console_mesh_draw_range')[0]
        self.assertIn('camera_up={0,cos(PSX_PHI),-sin(PSX_PHI)}', turn)  # a skew of the screen, never a roll
        self.assertIn('console_rotate(camera_up,0,-lean)', turn)
        self.assertIn('if(home)console_matrix(target,SLOT_HOME_YAW,0);', native)

    def test_tvs_are_rendered_at_the_standard_angle_with_registered_glass_and_floor(self):
        registry = json.loads((SLOT / 'stage/tv/profiles.json').read_text())
        self.assertEqual(registry['default'], 'panasonic')
        for profile in registry['profiles']:
            with self.subTest(tv=profile['id']):
                with Image.open(SLOT / profile['image']) as image:
                    width = image.width
                w, h = profile['display']
                self.assertAlmostEqual(width / 2, w, delta=.01)         # 2x render, logical display size
                self.assertLessEqual(h, 352)                           # fits the 360 px scene with margins
                self.assertTrue(all(0 < v < 1 for p in profile['quad'] for v in p))
                bx, by = profile['base']
                self.assertTrue(0 < bx < w and h * .5 < by < h)       # floor point under the cabinet
                self.assertGreater(profile['footprint'][0], w * .7)
                # The glass is turned: its top edge slopes down toward the cabinet's right side.
                q = profile['quad']
                self.assertGreater(q[1][1], q[0][1] + .05)
                detail = json.loads((SLOT / 'stage/tv' / ('profile.json' if profile['id'] == 'panasonic' else profile['id'] + '.json')).read_text())
                self.assertEqual((detail['view']['elevation_degrees'], detail['view']['yaw_degrees']), (35, -22))
                self.assertEqual(detail['render_scale'], 2)
        header = (OVERLAY / 'SlotTelevision.h').read_text(encoding='utf-8')
        self.assertIn('float display[2]; float base[2]; float footprint[2];', header)

    def test_console_and_tv_align_front_contacts_with_separate_shadows(self):
        presentation = (OVERLAY / 'SlotPresentation.cpp').read_text(encoding='utf-8')
        self.assertIn('slot_native_ground(mNative,centre,extent)', presentation)
        self.assertIn('slot_native_contact(mNative,front)', presentation)
        self.assertIn('slotHomeLayout(model.c_str()', presentation)
        self.assertIn('mTargetRect.y()+centre[1]*scale', presentation)
        self.assertIn('mShadow.setPosition(tvX,tvY)', presentation)
        for name in ('shadow.png', 'floor.png'):
            image = Image.open(SLOT / 'stage' / name).convert('RGBA')
            alpha = image.getchannel('A')
            self.assertEqual(alpha.getpixel((0, 0)), 0)               # soft edge
            self.assertGreater(alpha.getpixel((image.width // 2, image.height // 2)), 30)
        native = (OVERLAY / 'SlotNative.c').read_text(encoding='utf-8')
        self.assertIn('int slot_native_ground(SlotNative *s,float centre[2],float extent[2])', native)
        self.assertIn('bool has_footprint;float floor_y,footprint[4];', (LAUNCH / 'console-gl.h').read_text(encoding='utf-8'))

    def test_titles_never_exceed_two_fitted_lines(self):
        presentation = (OVERLAY / 'SlotPresentation.cpp').read_text(encoding='utf-8')
        body = presentation.split('std::string titleLines(')[1].split('void texture(')[0]
        self.assertIn('const float limit=width-4;', body)               # TextComponent cannot wrap it again
        self.assertIn('lines.resize(2)', body)
        self.assertIn('(static_cast<unsigned char>(line.back())&0xC0)==0x80', body)   # whole UTF-8 characters
        # A TV glass smaller than ~200 px uses the compact type set.
        layout=(OVERLAY/'SlotMetadataLayout.h').read_text()
        self.assertIn('width<200?.84f:1.f',layout)
        self.assertIn('slotMetadataLayout(mScreenWidth,mScreenHeight',presentation)

    def test_reading_and_optical_poses_fit_the_native_raster(self):
        native = (OVERLAY / 'SlotNative.c').read_text(encoding='utf-8')
        self.assertIn('kind==4?326:', native)                         # DS raised for the turned pose
        specs = (LAUNCH / 'console-specs.h').read_text(encoding='utf-8')
        psx = re.search(r'\{"psx",6,[^}]*\}', specs).group(0).split(',')
        self.assertEqual(psx[10], '304')                              # PSX origin raised 16 px


if __name__ == '__main__':
    unittest.main()
