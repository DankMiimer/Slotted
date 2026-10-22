"""Exercise editor transforms against the cached, verified Three.js runtime."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node') and (ROOT / 'build/tabletop/editor-vendor/ready.json').is_file(),
                     'Scene editor Node/Three.js runtime not prepared')
class EditorTransformTests(unittest.TestCase):
    def test_world_swaps_shared_pivot_hierarchy_and_physical_scale(self):
        result = subprocess.run(['node', str(ROOT / 'tests/editor_selection.mjs')], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_near_plane_fit_and_label_occluders_match_native(self):
        result = subprocess.run(['node', str(ROOT / 'tests/view_depth.mjs')], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
