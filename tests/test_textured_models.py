"""Contracts for source-faithful textured models (SCTOON2 + SCTEX003 + albedo PNG)."""
import json, struct, unittest
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONSOLES = ROOT / 'theme/art-book-slot/_slot/consoles'
TEXTURED = sorted(p.parent.name for p in CONSOLES.glob('*/model.texture'))


def fnv(data):
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & 0xffffffffffffffff
    return h


class TexturedModels(unittest.TestCase):
    def test_gbc_is_textured(self):
        self.assertIn('gbc', TEXTURED)

    def test_sidecar_binds_mesh_indices_and_albedo(self):
        for name in TEXTURED:
            with self.subTest(name=name):
                folder = CONSOLES / name
                mesh = (folder / 'model.mesh').read_bytes()
                magic, vertices, indices, door = struct.unpack_from('<8sIII', mesh)
                raw = mesh[20:20 + vertices * 36]
                index_bytes = mesh[20 + vertices * 36:]
                sidecar = (folder / 'model.texture').read_bytes()
                tag, count, w, h, luma, vh, ih, ph = struct.unpack_from('<8sIIIfQQQ', sidecar)
                self.assertEqual(tag, b'SCTEX003')
                self.assertEqual(count, vertices)
                self.assertEqual(len(sidecar), 48 + count * 8)
                self.assertEqual(vh, fnv(raw))
                self.assertEqual(ih, fnv(index_bytes))
                self.assertTrue(.02 <= luma <= 1)
                # Power-of-two atlas for GLES2 mipmaps; within the loader limit.
                self.assertTrue(w == h and w & (w - 1) == 0 and w <= 4096)
                uv = np.frombuffer(sidecar, '<f4', count * 2, 48)
                self.assertTrue(np.isfinite(uv).all() and uv.min() >= 0 and uv.max() <= 1)
                albedo = np.asarray(Image.open(folder / 'model.albedo.png').convert('RGBA'))
                self.assertEqual(albedo.shape, (h, w, 4))
                self.assertEqual(ph, fnv((folder / 'model.albedo.png').read_bytes()))
                mask = (folder / 'paint.mask').read_bytes()
                self.assertEqual(struct.unpack_from('<8sIQ', mask), (b'SCPAINT1', vertices, fnv(raw)))

    def test_registration_credits_and_cleared_source_art(self):
        credits = (ROOT / 'theme/art-book-slot/_slot/MODEL_CREDITS.txt').read_text(encoding='utf-8')
        ledger = (ROOT / 'CREDITS.md').read_text(encoding='utf-8')
        for name in TEXTURED:
            with self.subTest(name=name):
                folder = CONSOLES / name
                reg = json.loads((folder / 'registration.json').read_text())
                info = json.loads((folder / 'mesh-info.json').read_text())
                self.assertIn(reg['url'], credits)
                self.assertIn(reg['url'], ledger)
                self.assertTrue(reg['licence'].startswith('CC-BY'))
                self.assertEqual(len(reg['source_sha256']), 64)
                self.assertIn('no PBR', info['texture']['lighting'])
                # Texels no kept face samples were cleared (removed media art).
                self.assertGreater(info['atlas']['cleared_texels'], 0)
                self.assertTrue(info['atlas']['blank'] or reg.get('excluded_source_materials') or reg.get('source_game_art','').startswith('None'),
                                'Clear kept game art or exclude its complete material')


if __name__ == '__main__':
    unittest.main()
