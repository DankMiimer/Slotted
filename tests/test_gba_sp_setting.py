"""Theme setting "slot-gba-sp-model": NeilVFX (local file, default) or the packaged thegraphicsgeek SP."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / 'theme/art-book-slot'
OVERLAY = ROOT / 'tools/frontend/overlay/es-app/src/components'


class GbaSpSetting(unittest.TestCase):
    def test_theme_offers_both_models_with_neilvfx_as_the_default(self):
        xml = (THEME / 'theme.xml').read_text(encoding='utf-8')
        block = re.search(r'<subset name="slot-gba-sp-model"[^>]*>(.*?)</subset>', xml, re.S).group(1)
        names = re.findall(r'<include name="([^"]+)"', block)
        self.assertEqual(names, ['neilvfx', 'graphicsgeek'])          # first entry is the default
        self.assertIn('CC BY', block)
        self.assertNotIn('zelda', block.lower())                       # the unavailable SP is not offered

    def test_frontend_exports_the_choice_and_native_skips_the_local_profile(self):
        presentation = (OVERLAY / 'SlotPresentation.cpp').read_text(encoding='utf-8')
        self.assertIn('subset.slot-gba-sp-model', presentation)
        self.assertEqual(presentation.count('setenv("SLOT_GBA_SP"'), 3)   # highlight, native open and tabletop open
        self.assertIn('gbaSpChoice()', presentation.split('const auto nativeId=')[1].split(';')[0])
        # The tabletop reopens (its key changes) when the SP choice changes.
        table = presentation.split('bool SlotPresentation::tabletop(')[1].split('slot_tabletop_open(')[0]
        self.assertIn('gbaSpChoice()', table.split('const std::string key=')[1].split(';')[0])
        self.assertIn('setenv("SLOT_GBA_SP",gbaSpChoice()', table)
        tabletop = (OVERLAY / 'SlotTabletop.cpp').read_text(encoding='utf-8')
        self.assertIn('getenv("SLOT_GBA_SP")', tabletop.split('Console loadConsole(')[1].split('return c;')[0])
        native = (OVERLAY / 'SlotNative.c').read_text(encoding='utf-8')
        local = native.split('static int slot_local')[1].split('int slot_native_lcd')[0]
        self.assertIn('getenv("SLOT_GBA_SP")', local)
        self.assertLess(local.index('graphicsgeek'), local.index('model.pose'))   # decided before any file access

    def test_launch_script_exports_the_same_default(self):
        common = (THEME / '_slot/launch/common.sh').read_text(encoding='utf-8')
        self.assertIn('export SLOT_GBA_SP=$(slot_option slot-gba-sp-model neilvfx)', common)

    def test_packaged_model_is_the_textured_cc_source_and_local_assets_stay_unpackaged(self):
        gba = THEME / '_slot/consoles/gba'
        self.assertTrue((gba / 'model.texture').exists())
        self.assertIn('thegraphicsgeek', (gba / 'registration.json').read_text(encoding='utf-8'))
        self.assertIn('/theme/art-book-slot/_slot/local-models/', (ROOT / '.gitignore').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
