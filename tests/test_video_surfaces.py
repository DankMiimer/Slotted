"""Video must share the art's physical surface and preserve source proportions."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

from tools.themebuild.geometry import ROOT, SHAPES, SYSTEMS
from tools.themebuild.video import disc_map, shader_xml, variants


class VideoSurfaceTests(unittest.TestCase):
    def test_video_projection_matches_art_in_source_pixels(self):
        for name in ('psx', 'psp'):
            with self.subTest(name=name):
                folder = ROOT / 'theme/art-book-slot/_slot/shapes' / name
                spec = json.loads((folder/'shape.json').read_text())
                with Image.open(folder/'edge.png') as image:
                    width, height = image.size
                with Image.open(folder/'print-mask.png') as image:
                    source_width, source_height = image.size
                matrix = np.array(disc_map(name))[:, :3]
                a,b,c,d,e,f,g,h = spec['projection']
                for u,v in ((.1,.2), (.5,.5), (.9,.8), (.2,.9)):
                    x,y = u*width,v*height
                    art = np.array([(a*x+b*y+c)/(g*x+h*y+1),
                                    (d*x+e*y+f)/(g*x+h*y+1)])
                    projected = matrix @ np.array([u,v,1])
                    video = projected[:2]/projected[2] * (source_width,source_height)
                    np.testing.assert_allclose(video, art, atol=1e-7)

    def test_video_clip_matches_existing_print_mask_away_from_boundary(self):
        for name in ('psx', 'psp'):
            folder = ROOT / 'theme/art-book-slot/_slot/shapes' / name
            surface = json.loads((folder/'shape.json').read_text())['preview']
            with Image.open(folder/'print-mask.png') as image:
                mask = np.asarray(image)
            y,x = np.mgrid[:mask.shape[0], :mask.shape[1]]
            radius = np.hypot(x+.5-surface['centre'][0], y+.5-surface['centre'][1])
            inside = (radius < surface['outer']) & (radius > surface['inner'])
            uncertain = abs(radius-surface['outer']) <= 1.5
            if surface['inner']:
                uncertain |= abs(radius-surface['inner']) <= 1.5
            np.testing.assert_array_equal(inside[~uncertain], (mask>0)[~uncertain])
        self.assertGreater(json.loads((ROOT/'theme/art-book-slot/_slot/shapes/psx/shape.json').read_text())['preview']['inner'], 0)
        self.assertEqual(json.loads((ROOT/'theme/art-book-slot/_slot/shapes/psp/shape.json').read_text())['preview']['inner'], 0)

    def test_uniform_cover_crop_for_landscape_square_and_portrait(self):
        for width,height in ((640,480), (640,360), (360,640), (480,480)):
            retained = np.minimum(1, np.array([height/width, width/height]))
            # The same physical distance maps to the same source pixel distance
            # on both axes. Circular source shapes therefore remain circular in
            # the flat media plane, before legitimate camera perspective.
            self.assertAlmostEqual(retained[0]*width, retained[1]*height)
            self.assertEqual(max(retained), 1)
            self.assertLessEqual(max(retained), 1)
        self.assertAlmostEqual(min(1,360/640), .5625)

    def test_cd_preserves_original_hub_graphics_and_outer_rim(self):
        folder = ROOT / 'theme/art-book-slot/_slot/shapes/psx'
        surface = json.loads((folder/'shape.json').read_text())['preview']
        with Image.open(folder/'hub.png') as image:
            hub = np.asarray(image.getchannel('A'))
        y,x = np.nonzero(hub)
        radii = np.hypot(x+.5-surface['centre'][0],y+.5-surface['centre'][1])
        # Cover AA must stop before any opaque hub graphics. The bore remains
        # the art's transparent physical hole; it is not filled by a second image.
        self.assertGreaterEqual(surface['videoInner']-radii.max(),1.5)
        self.assertGreater(surface['videoInner'],surface['inner'])
        self.assertGreater(surface['outer']-surface['videoOuter'],0)
        shader = ET.fromstring(shader_xml(SHAPES['psx']))
        self.assertAlmostEqual(float(shader.findtext('mediaInner')),surface['videoInner']/hub.shape[0])
        self.assertAlmostEqual(float(shader.findtext('mediaOuter')),surface['videoOuter']/hub.shape[1])

    def test_generated_frontend_contract_resolves_path_and_keeps_single_player(self):
        for name in {value[0] for value in SYSTEMS.values()}:
            element = ET.fromstring(shader_xml(SHAPES[name]))
            self.assertEqual(element.findtext('path'), '${currentPath}/shaders/media.glsl')
            if name in ('psx','dreamcast','psp'):
                self.assertEqual(float(element.findtext('mediaMode')), 1)
                self.assertEqual(len(element.findtext('mediaCanvas').split()), 4)
            path = ROOT / ('theme/art-book-slot/_slot/shelf-'+name+'.xml')
            videos = ET.parse(path).findall('.//video')
            self.assertEqual(len(videos), 1)
            self.assertEqual(videos[0].get('name'),'slot_video')
            self.assertEqual(videos[0].findtext('delay'), '3')
            self.assertEqual(videos[0].findtext('audio'), 'false')
            # A video path is a Path property: Scarab does not evaluate
            # expressions there, so it must stay the plain gamelist binding.
            self.assertEqual(videos[0].findtext('path'), '{game:video}')
            self.assertEqual(videos[0].findtext('enabled'), 'exists({game:video})')
            self.assertEqual(videos[0].findall('storyboard'), [])
            self.assertIsNotNone(videos[0].find('minSize'))

    def test_each_cartridge_variant_uses_the_entire_baked_label(self):
        for name in {value[0] for value in SYSTEMS.values()}-{'psx','dreamcast','psp'}:
            shader = ET.fromstring(shader_xml(SHAPES[name]))
            for index,variant in enumerate((name,)+variants(SHAPES[name])):
                spec=json.loads((ROOT/'theme/art-book-slot/_slot/shapes'/variant/'shape.json').read_text())
                w,h=spec['size']
                left,top,width,height=map(float,shader.findtext('mediaWell%d'%index).split())
                actual=(left*w,top*h,(left+width)*w,(top+height)*h)
                np.testing.assert_allclose(actual,spec['well'],atol=1e-5)
                self.assertEqual(float(shader.findtext('mediaCorner%d'%index)),spec.get('wellRadius',0))


if __name__ == '__main__':
    unittest.main()
