"""Physical cartridge media: envelopes, budgets, label contract and variant choice."""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT/'theme/art-book-slot/_slot'
sys.path.insert(0, str(ROOT/'tools/consolebuild'))
import media  # noqa: E402

# Mouldings that stand proud of the faces beyond the shell's own thickness.
EXTRA_DEPTH = {'md': 1.4, 'md-jp': 1.55, 'md-ea': 1.2, 'pico8': .5, 'snes-us': .32, 'n64': 1.25, 'nds': .03}


def mesh(folder, part):
    raw = (SLOT/'consoles'/folder/(part+'.mesh')).read_bytes()
    magic, n, count, door = struct.unpack_from('<8sIII', raw)
    vertices = np.frombuffer(raw, '<f4', n*9, 20).reshape(-1, 9)
    indices = np.frombuffer(raw, '<u2', count, 20+n*36)
    return magic, vertices, indices, door


def outline_rows(path):
    """cartridge_outline(): 33 rows between the first and last opaque rows."""
    alpha = np.asarray(Image.open(path).convert('RGBA'))[:, :, 3] > 240
    h, w = alpha.shape
    ys = np.where(alpha.any(axis=1))[0]; top, bottom = ys[0], ys[-1]
    rows = []
    for i in range(33):
        xs = np.where(alpha[top+(bottom-top)*i//32])[0]
        if len(xs):
            rows.append(2*(xs[-1]+1)/w-2*xs[0]/w)
    return rows


def variant_for(console, rows):
    """Mirror of cartridge_media_variant() in cartridge-console.h."""
    widest = max(rows)
    if console in ('snes', 'snes-us'):
        return 'snes-us' if rows[1] < .85*widest else 'snes'
    if console in ('md', 'md-jp'):
        return 'md-ea' if widest < 1.76 else 'md-jp' if rows[-2] < .92*widest else 'md'
    return console


class CartridgeMedia(unittest.TestCase):
    def test_physical_envelopes_and_native_budgets(self):
        for variant, spec in media.MEDIA.items():
            with self.subTest(variant=variant):
                magic, v, indices, door = mesh(spec['folder'], spec['part'])
                self.assertEqual(magic, b'SCTOON2\0')
                self.assertLessEqual(len(v), 65535)
                registered=media.authored(variant)
                if registered:self.assertEqual(len(indices)//3,registered['prepared']['triangles'])
                else:self.assertLess(len(indices)//3, 15000)
                self.assertTrue((indices < len(v)).all())
                self.assertEqual(door, len(indices), 'Media have no hinged range')
                q = media.SCALES[spec['folder']]; w, h, t = registered['size_mm'] if registered else spec['size']
                size = (v[:, :3].max(axis=0)-v[:, :3].min(axis=0))/q
                self.assertAlmostEqual(size[0], w, delta=.45)
                self.assertAlmostEqual(size[1], h, delta=.45)
                self.assertGreaterEqual(size[2], t-.01)
                self.assertLessEqual(size[2], t+EXTRA_DEPTH.get(variant, 0)+.05)
                # Centred on the body, mid-thickness at the origin.
                centre = (v[:, :3].max(axis=0)+v[:, :3].min(axis=0))/2/q
                self.assertLess(abs(centre[0]), .45); self.assertLess(abs(centre[1]), .45)

    def test_reserved_plastic_and_physical_details(self):
        for variant, spec in media.MEDIA.items():
            with self.subTest(variant=variant):
                if media.authored(variant):
                    raw=(SLOT/'consoles'/spec['folder']/(spec['part']+'.paint.mask')).read_bytes()
                    magic,n,hash_=struct.unpack_from('<8sIQ',raw)
                    self.assertEqual(magic,b'SCPAINT1');self.assertEqual(n,len(mesh(spec['folder'],spec['part'])[1]))
                    self.assertGreater(np.count_nonzero(np.frombuffer(raw,np.uint8,offset=20)),n*.1)
                    self.assertIn(media.authored(variant)['licence'],('CC-BY-4.0','CC-BY-NC-SA-4.0'))
                    continue
                colours = mesh(spec['folder'], spec['part'])[1][:, 6:9]
                def share(rgb): return np.all(np.abs(colours-rgb) < .005, axis=1).mean()
                self.assertGreater(share(media.SHELL), .2, 'Shell must carry the tintable plastic')
                self.assertGreater(share(media.SHADE), 0, 'Shaded recess floors / mouldings')
                self.assertGreater(share((.77, .75, .68)), 0, 'Blank recessed label plate')
                self.assertGreater(share((.73, .57, .26)), 0, 'Gold edge fingers or card contacts')
                if variant != 'nds':
                    self.assertGreater(share((.10, .33, .18)), 0, 'Connector board inside the edge')
                if variant == 'md-ea':
                    self.assertGreater(share((.83, .64, .07)), 0, 'EA yellow grip')
                info = json.loads((SLOT/'consoles'/spec['folder']/(spec['part']+'-info.json')).read_text())
                self.assertEqual(info['licence'], 'MIT')
                self.assertIn('Original', info['source'])

    def test_generated_header_matches_the_python_frames(self):
        self.assertEqual((ROOT/'tools/slotlaunch/media-specs.h').read_text(), media.header_text())

    def test_label_contract_stays_on_the_body_and_canvas(self):
        for variant, spec in media.MEDIA.items():
            with self.subTest(variant=variant):
                frame = media.Frame(variant); (cx, cy, w, h), depth = frame.label()
                self.assertLessEqual(abs(cx)+w/2, frame.w/2+.01)
                self.assertLessEqual(abs(cy)+h/2, frame.h/2+.01)
                name='snes-tzakol' if 'tzakol' in variant else variant
                shape = json.loads((SLOT/'shapes'/name/'shape.json').read_text())
                self.assertEqual(spec['canvas'], tuple(shape['size']))
                if media.authored(variant):
                    well=json.loads(media.hero_path(variant).read_text())['label']
                    self.assertEqual(well,shape['label'])
                elif variant != 'pico8':
                    well=media.WELLS[variant][0]
                    self.assertEqual(list(well), shape['well'], 'Native crop is the baker\'s label well')

    def test_baked_outline_selects_the_matching_physical_shell(self):
        for variant, spec in media.MEDIA.items():
            with self.subTest(variant=variant):
                if 'tzakol' in variant:continue # explicit setting, not regional outline inference
                rows = outline_rows(SLOT/'shells'/(variant+'.png'))
                self.assertEqual(variant_for(spec['folder'], rows), variant)
        # Regional faces on the other console still pick their own shell.
        self.assertEqual(variant_for('snes', outline_rows(SLOT/'shells/snes-us.png')), 'snes-us')
        self.assertEqual(variant_for('md-jp', outline_rows(SLOT/'shells/md.png')), 'md')
        self.assertEqual(variant_for('md-jp', outline_rows(SLOT/'shells/md-ea.png')), 'md-ea')

    def test_shelf_faces_are_the_3d_hero_renders(self):
        hero = ROOT/'tools/themebuild/assets/hero'
        header = (ROOT/'tools/slotlaunch/media-specs.h').read_text()
        for shape in ('gb', 'gbc', 'gba', 'snes', 'snes-us', 'nes', 'n64', 'md', 'md-jp', 'md-ea', 'nds', 'pico8'):
            with self.subTest(shape=shape):
                spec = json.loads((SLOT/'shapes'/shape/'shape.json').read_text())
                render = Image.open(hero/(shape+'.png'))
                measured = json.loads((hero/(shape+'.json')).read_text())
                self.assertTrue(spec['model'])
                self.assertEqual(render.size, tuple(spec['size']))
                self.assertEqual(measured['canvas'], spec['size'])
                mask = np.asarray(Image.open(SLOT/'shapes'/shape/'mask.png'), dtype=int)
                self.assertLessEqual(np.abs(mask-np.asarray(render.getchannel('A'), dtype=int)).max(), 1)
                if shape in media.EXEMPLARS:
                    # The Game Pak recess is the label: baker, header and render agree.
                    self.assertEqual(spec['label'], measured['label'])
                    self.assertIn('{%s}' % ','.join(map(str, measured['label'])), header)
                elif shape != 'pico8':
                    self.assertLessEqual(max(abs(a-b) for a, b in zip(measured['label'], spec['well'])), 1)

    def test_baker_pastes_the_label_into_the_model_recess(self):
        sys.path.insert(0, str(SLOT))
        from slotcart import render, shells
        for name, shell in (('gb', shells.DMG_GREY), ('snes', shells.SNES_GREY)):
            shape = render.Shape(SLOT/'shapes'/name)
            face = np.asarray(render.face(shape, shell, Image.new('RGB', (64, 64), (0, 255, 96))))
            green = (face[:, :, 0] < 20) & (face[:, :, 1] > 240) & (face[:, :, 3] > 0)
            ys, xs = np.where(green)
            x0, y0, x1, y1 = shape.label
            self.assertEqual((xs.min(), ys.min(), xs.max()+1, ys.max()+1), (x0, y0, x1, y1))

    def test_gba_lower_panel_normals_do_not_blend_across_the_edge(self):
        # A long planar triangle used to interpolate a curved edge normal over
        # this strip, producing a diagonal stripe with the Realistic gloss term.
        _, vertices, indices, _ = mesh('gba', 'media')
        faces = vertices[indices.reshape(-1, 3)]
        points = faces[:, :, :3]; q = 224/82
        panel = ((np.ptp(points[:, :, 2], axis=1) < .0001)
                 & (points.mean(axis=1)[:, 1] < -11*q)
                 & (points.mean(axis=1)[:, 2] > .8*q))
        self.assertGreater(panel.sum(), 5)
        # Blender packs custom normals; allow its small angular quantization.
        normals=faces[panel,:,3:6]
        normals=normals/np.linalg.norm(normals,axis=2,keepdims=True)
        self.assertLess(np.abs(normals[:,:,:2]).max(), .01)
        self.assertGreater(np.abs(normals[:,:,2]).min(), .9999)

    @unittest.skipUnless(os.name == 'posix', 'native GLES hand-off requires WSL')
    def test_native_shelf_handoff(self):
        # Render the actual first scene frame, including the baked plastic
        # sample and label crop. Supported shelf faces now match Realistic.
        lib = Path(os.environ.get('SLOT_DESKTOP_IMAGE_LIB', str(
            ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu')))
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary); native = out/'native'
            subprocess.run(['gcc', '-O2', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-DSLOT_AUTHORED_MEDIA', '-DSLOT_NEXT_MEDIA', '-DSLOT_CARTRIDGE_MEDIA',
                            '-I'+str(ROOT/'build/native/SDL-release-2.32.8/include'),
                            '-DSLOT_HELPER_SOURCE="'+str(ROOT/'tools/slotlaunch/slot-launch.c')+'"',
                            str(ROOT/'tools/consolebuild/offline-preview.c'), '-L'+str(lib),
                            '-l:libSDL2_image-2.0.so.0', '-l:libSDL2-2.0.so.0', '-lm', '-o', str(native)],
                           check=True, capture_output=True)
            errors = {}
            for name, system, foot in (
                    ('gb', 'gb', 380), ('gbc', 'gbc', 380), ('gba', 'gba', 346),
                    ('snes', 'snes', 334), ('snes-us', 'snes-us', 334), ('n64', 'n64', 332),
                    ('nes', 'nes', 380), ('md', 'md', 346), ('md-jp', 'md-jp', 346),
                    ('md-ea', 'md', 346), ('nds', 'nds', 382), ('pico8', 'pico8', 380)):
                with self.subTest(shape=name):
                    env = dict(os.environ, LD_LIBRARY_PATH=str(lib), SDL_VIDEODRIVER='offscreen',
                               EGL_PLATFORM='surfaceless', LIBGL_ALWAYS_SOFTWARE='1',
                               SLOT_CONSOLE_COLOR='original',
                               SLOT_MODEL_STYLE='realistic')
                    subprocess.run([str(native), system, str(SLOT), str(out), 'insert',
                                    'shell='+name, 'first'], env=env, check=True, capture_output=True)
                    face = Image.open(SLOT/'shells'/(name+'.png')).convert('RGBA')
                    shelf = Image.new('RGBA', (720, 480), (22, 24, 28, 255))
                    x = (720-face.width)//2; y = foot-face.height
                    shelf.alpha_composite(face, (x, y))
                    actual = np.asarray(Image.open(out/'insert-00.png').convert('RGB'), dtype=float)
                    expected = np.asarray(shelf.convert('RGB'), dtype=float)
                    difference = np.abs(actual[y:foot, x:x+face.width]-expected[y:foot, x:x+face.width])
                    errors[name] = float(difference.mean())
                    # Multiplicative baking, clear-board layers and resampling
                    # are not lossless; bound the mean error to 3.2% of RGB.
                    self.assertLess(difference.mean(), 8, (name, difference.mean()))
                    # Independently require the shipped hero to be the exact
                    # native capture with the selected shader, not just similar.
                    subprocess.run([str(native), system, str(SLOT), str(out), 'hero',
                                    'shell='+name], env=env, check=True, capture_output=True)
                    np.testing.assert_array_equal(np.asarray(Image.open(out/'hero.png')),
                        np.asarray(Image.open(ROOT/'tools/themebuild/assets/hero'/(name+'.png'))))
                    self.assertEqual(json.loads((out/'hero.json').read_text()), json.loads(
                        (ROOT/'tools/themebuild/assets/hero'/(name+'.json')).read_text()))
            # The explicit style works on both regional consoles. Unknown values
            # render exactly the regional default through the actual C selector.
            for system in ('snes','snes-us'):
                results={}
                for choice in ('regional','unknown-fixture','tzakol'):
                    env['SLOT_SNES_CARTRIDGE']=choice
                    shell='snes-tzakol' if choice=='tzakol' else system
                    subprocess.run([str(native),system,str(SLOT),str(out),'insert','shell='+shell,'first'],env=env,check=True,capture_output=True)
                    results[choice]=Image.open(out/'insert-00.png').tobytes()
                self.assertEqual(results['regional'],results['unknown-fixture'])
                self.assertNotEqual(results['regional'],results['tzakol'])
            if os.environ.get('SLOT_MEDIA_EVIDENCE'):
                (Path(os.environ['SLOT_MEDIA_EVIDENCE'])/'handoff.json').write_text(
                    json.dumps(dict(mean_rgb_error=errors), indent=2)+'\n')

    def test_slot_openings_fit_the_thickest_media_with_clearance(self):
        for console, variants in media.CONSOLE_VARIANTS.items():
            if console in ('nes', 'nds', 'pico8'):
                continue
            q = media.SCALES[console]
            for variant in variants:
                t = media.MEDIA[variant]['size'][2]+2*media.PROUD.get(variant, 0)
                self.assertGreaterEqual(media.opening(console)/q-t, 1.99, (console, variant))


if __name__ == '__main__':
    unittest.main()
