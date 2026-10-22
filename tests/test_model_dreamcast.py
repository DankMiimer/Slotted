"""Dreamcast geometry, sloped optical seat, dynamic disc art and packaging."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
import numpy as np
from PIL import Image
from tests.test_model_snes import ROOT, SLOT, native, glb, part_bounds, top_hits
from tools.consolebuild.dreamcast import Q
from tools.frontend.deploy_set import owned
from tools.themebuild.geometry import SHAPES


class DreamcastModel(unittest.TestCase):
    def test_complete_source_console_and_separate_lid(self):
        _, v, i, door = native('dreamcast')
        self.assertTrue(36260<=len(i)//3<=36280)  # degenerate faces at float tolerance
        self.assertLess(len(v),65536)
        self.assertGreater(door,0); self.assertLess(door,len(i))
        np.testing.assert_allclose(np.ptp(v[:,:3],axis=0)/Q,(190,80.12,195.14),atol=.5)
        g = glb(SLOT/'consoles/dreamcast/model-physical.glb')
        parts = part_bounds(g)
        self.assertEqual(len(parts),13)
        self.assertIn('Dreamcast spindle',parts)
        self.assertNotIn('Disc',parts)
        moving = {n['name'] for n in g['nodes'] if n.get('extras',{}).get('hinged')}
        self.assertEqual(moving,{'Dreamcast disc lid'})
        reg = json.loads((SLOT/'consoles/dreamcast/registration.json').read_text())
        self.assertEqual(reg['excluded_source_materials'],['Disc'])
        provenance = json.loads((ROOT/'third_party/models/zerescas-dreamcast/source.json').read_text())
        self.assertEqual(set(provenance['source_images']),{'Case','Door_and_ports'})

    def test_disc_clears_drive_and_fits_beneath_closed_lid(self):
        _, v, i, door = native('dreamcast')
        body = (v[:,:3]/Q)[i[:door]].reshape(-1,3,3)
        lid = (v[:,:3]/Q)[i[door:]].reshape(-1,3,3)
        reg = json.loads((SLOT/'consoles/dreamcast/registration.json').read_text())
        x,y,z = np.array(reg['disc_centre_native'])/Q
        tilt = reg['disc_tilt_radians']
        self.assertAlmostEqual(np.degrees(tilt),87,delta=.1)
        # Independent rays around the disc edge: real 1.2-mm thickness and lid
        # clearance, on the artist's sloped drive (base remains level).
        for angle in np.linspace(0,2*np.pi,33)[:-1]:
            px,pz = x+58*np.cos(angle),z+58*np.sin(angle)
            plane = y-(pz-z)/np.tan(tilt)
            floor,cover = top_hits(body,px,pz),top_hits(lid,px,pz)
            self.assertGreater(len(floor),0); self.assertGreater(len(cover),0)
            self.assertLess(floor.max(),plane-1.2,(angle,floor.max(),plane))
            self.assertGreater(cover.min(),plane+.15,(angle,cover.min(),plane))

    def test_new_system_runtime_is_packaged(self):
        paths = {p.relative_to(ROOT/'theme/art-book-slot').as_posix() for p in owned(['dreamcast'])}
        for p in ('dreamcast/theme.xml','_slot/shelf-dreamcast.xml',
                  '_slot/consoles/dreamcast/model.texture','_slot/shapes/dreamcast/shape.json',
                  '_slot/shells/dreamcast.disc.tga','_slot/backings/dreamcast.png'):
            self.assertIn(p,paths)
        self.assertEqual(SHAPES['dreamcast'].size,(336,336))

    def test_disc_baker_uses_game_label_and_dreamcast_identity(self):
        import sys
        sys.path.insert(0,str(SLOT))
        from slotcart import discs, render, shells, library, launchbox
        shape = render.Shape(SLOT/'shapes/dreamcast')
        red = render.disc_texture(shape,Image.new('RGB',(648,648),'red'))
        blue = render.disc_texture(shape,Image.new('RGB',(648,648),'blue'))
        self.assertNotEqual(red.tobytes(),blue.tobytes())
        scan=Image.new('RGBA',(1024,1024),(140,20,30,255))
        self.assertEqual(launchbox.label_crop(scan,'North America','dreamcast').size,(648,648))
        self.assertEqual(shells.outline_for(shells.read_header('dreamcast',b'')),'dreamcast')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'dreamcast').mkdir()
            (root/'dreamcast/Example (USA).gdi').write_text('')
            games=library.scan(root,['dreamcast'],library.CrcCache(root/'cache'))
            self.assertEqual(len(games),1)
            self.assertEqual(games[0].header.platform,'dreamcast')

    @unittest.skipUnless(os.name=='posix','POSIX native renderer')
    def test_disc_and_tray_share_real_depth(self):
        lib=ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'depth'
            subprocess.run(['gcc','-O2','-std=c11','-Wall','-Wextra','-Werror',
                '-I'+str(ROOT/'build/native/SDL-release-2.32.8/include'),
                str(ROOT/'tools/frontend/tests/optical_depth.c'),'-L'+str(lib),
                '-l:libSDL2_image-2.0.so.0','-l:libSDL2-2.0.so.0','-lm','-o',str(binary)],
                check=True,capture_output=True)
            result=subprocess.run([str(binary)],capture_output=True,text=True,
                env=dict(os.environ,LD_LIBRARY_PATH=str(lib),SDL_VIDEODRIVER='offscreen',
                         EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('below tray: 0 green',result.stdout)

    @unittest.skipUnless(os.name=='posix','POSIX native renderer')
    def test_native_lid_hides_dynamic_disc_when_closed(self):
        lib=ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder); binary=out/'preview'
            subprocess.run(['gcc','-O2','-std=c11','-Wall','-Wextra','-Werror',
                '-I'+str(ROOT/'build/native/SDL-release-2.32.8/include'),
                str(ROOT/'tools/consolebuild/offline-preview.c'),'-L'+str(lib),
                '-l:libSDL2_image-2.0.so.0','-l:libSDL2-2.0.so.0','-lm','-o',str(binary)],
                check=True,capture_output=True)
            env=dict(os.environ,LD_LIBRARY_PATH=str(lib),SDL_VIDEODRIVER='offscreen',
                EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',SLOT_MODEL_STYLE='realistic')
            subprocess.run([str(binary),'dreamcast',str(SLOT),str(out),'insert','diagnostic'],
                           env=env,check=True,capture_output=True)
            def green(frame):
                p=np.array(Image.open(out/f'insert-{frame:02d}.png').convert('RGB'))
                return ((p[:,:,0]<20)&(p[:,:,1]>240)&(p[:,:,2]>70)&(p[:,:,2]<130)).sum()
            self.assertGreater(green(0),10000)
            self.assertGreater(green(33),1000)
            self.assertEqual(green(60),0)


if __name__=='__main__': unittest.main()
