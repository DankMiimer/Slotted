"""Baked physical identity must follow manual/special shell changes without art rebuilds."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'theme/art-book-slot/_slot'))
from slotcart import surfaces


class SurfaceVariantTests(unittest.TestCase):
    def test_existing_nested_cache_migrates_and_stale_markers_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            media=root/'snes/folder/media/slotcarts'
            media.mkdir(parents=True)
            poster=media/'Manual.png'
            poster.write_bytes(b'keep existing artwork')
            manifest=media/'.slotcart.json'
            manifest.write_text(json.dumps({'Manual':json.dumps([1,'snes-us'])}))
            before=manifest.read_bytes()
            self.assertEqual(surfaces.migrate(root),1)
            marker=media/'Manual.slot-profile-snes-us'
            self.assertTrue(marker.is_file())
            self.assertEqual(poster.read_bytes(),b'keep existing artwork')
            self.assertEqual(manifest.read_bytes(),before)
            surfaces.write_variant(poster,'snes')
            self.assertFalse(marker.exists())
            surfaces.write_variant(poster,'md-ea')
            self.assertTrue((media/'Manual.slot-profile-md-ea').is_file())
            surfaces.write_variant(poster,'md-jp')
            self.assertFalse((media/'Manual.slot-profile-md-ea').exists())
            self.assertTrue((media/'Manual.slot-profile-md-jp').is_file())


if __name__=='__main__':
    unittest.main()
