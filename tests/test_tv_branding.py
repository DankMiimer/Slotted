"""RETROvision TV branding: shipped prepared TVs carry no Panasonic/Sony marks."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from tools.tabletop import tv_branding

ROOT = Path(__file__).resolve().parents[1]
ASSETS = next((p for p in (ROOT / 'assets/tabletop', ROOT / 'build/tabletop/assets') if (p / 'panasonic/scene.txt').is_file()), None)


@unittest.skipUnless(ASSETS, 'prepared TV assets not restored')
class TvBrandingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)

    def test_prepared_tvs_are_branded(self):
        self.assertEqual(tv_branding.check(ASSETS), [])

    def test_logo_is_read_the_right_way_round(self):
        alpha = tv_branding.retrovision(ASSETS / 'oldtv/albedo-00.png')
        self.assertGreater(alpha.shape[1] / alpha.shape[0], 3.5)
        third = alpha.shape[1] // 3
        self.assertGreater(alpha[:, :third].mean(), alpha[:, -third:].mean())  # bold RETRO first, then "vision"

    def test_branded_or_unexpected_models_are_refused(self):
        shutil.copytree(ASSETS / 'panasonic', self.root / 'panasonic')
        with self.assertRaisesRegex(ValueError, 'already branded'):
            tv_branding.apply(self.root, ('panasonic',), ASSETS / 'oldtv/albedo-00.png')
        scene = json.loads((self.root / 'panasonic/scene.json').read_text())
        scene['changes'] = [c for c in scene['changes'] if not c.startswith(tv_branding.MARK)]
        (self.root / 'panasonic/scene.json').write_text(json.dumps(scene))
        before = {p.name: p.read_bytes() for p in (self.root / 'panasonic').iterdir()}
        with self.assertRaisesRegex(ValueError, 'Not the unbranded Panasonic'):
            tv_branding.apply(self.root, ('panasonic',), ASSETS / 'oldtv/albedo-00.png')
        self.assertEqual({p.name: p.read_bytes() for p in (self.root / 'panasonic').iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
