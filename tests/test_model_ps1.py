"""Physical PS1 derivative, separate moving lid, disc fit and source provenance."""
import json,unittest,os,tempfile,subprocess
from pathlib import Path
from PIL import Image
import numpy as np
from tests.test_model_snes import ROOT,SLOT,native,glb,part_bounds,top_hits
from tools.consolebuild.ps1 import SPECS,registration

class PlayStationModel(unittest.TestCase):
    def test_closed_physical_envelope_and_separate_lid(self):
        magic,v,i,door=native('psx');q=SPECS['psx']['scale']
        self.assertEqual(magic,b'SCTOON2\0');self.assertEqual(len(i)//3,64717)
        textured=json.loads((SLOT/'consoles/psx/registration.json').read_text())
        self.assertFalse(textured['decimation'])
        self.assertEqual(sum(textured['source_parts'].values()),64717)
        self.assertGreater(door,0);self.assertLess(door,len(i))
        self.assertLessEqual(len(v),65535);self.assertLess(i.max(),len(v))
        np.testing.assert_allclose(np.ptp(v[:,:3],axis=0)/q,(270,60,188),atol=.4)
        bounds=part_bounds(glb(SLOT/'consoles/psx/model-physical.glb'))
        for name in ('PS1 enclosure','PS1 disc lid','PS1 disc well','PS1 spindle','PS1 optical pickup','PS1 socket interiors'):
            self.assertIn(name,bounds)
        g=glb(SLOT/'consoles/psx/model.glb')
        moving={n['name'] for n in g['nodes'] if 'mesh' in n and n.get('extras',{}).get('hinged')}
        self.assertEqual(moving,{'PS1 disc lid'})  # source print travels with the UV-mapped lid
        pickup=bounds['PS1 optical pickup']*1000
        self.assertLess(pickup[:,2].mean(),-20,'Early optical unit is behind the spindle')

    def test_cd_clears_the_open_well_and_closed_lid_covers_it(self):
        _,v,i,door=native('psx');q=SPECS['psx']['scale']
        body=(v[:,:3]/q)[i[:door]].reshape(-1,3,3)
        lid=(v[:,:3]/q)[i[door:]].reshape(-1,3,3)
        r=registration();x,y,z=r['disc_label_xyz_mm']
        # Independent vertical rays over a 120-mm disc footprint, excluding
        # the bore/spindle. At sampled rim points the body is below the disc,
        # and the closed lid has a surface above it.
        for angle in np.linspace(0,2*np.pi,17)[:-1]:
            px=x+58*np.cos(angle);pz=z+58*np.sin(angle)
            floor=top_hits(body,px,pz);cover=top_hits(lid,px,pz)
            self.assertGreater(len(floor),0,(px,pz))
            self.assertLess(floor.max(),y-1.2,(px,pz,floor))
            self.assertGreater(len(cover),0,(px,pz))
            self.assertGreater(cover.max(),y+.5,(px,pz,cover))

    def test_image_free_source_is_licensed_and_credited(self):
        folder=ROOT/'third_party/models/darkigorek-ps1'
        source=json.loads((folder/'source.json').read_text());g=glb(folder/'model.glb')
        self.assertEqual(source['licence'],'CC-BY-4.0')
        self.assertIn(source['url'],(SLOT/'MODEL_CREDITS.txt').read_text())
        self.assertFalse(g.get('images'));self.assertFalse(g.get('textures'))
        self.assertEqual(len(g['meshes']),7)
        for mesh in g['meshes']:
            for p in mesh['primitives']:self.assertNotIn('TEXCOORD_0',p['attributes'])
        for name in ('source_file_sha256','archive_sha256'):self.assertRegex(source[name],r'^[a-f0-9]{64}$')

    @unittest.skipUnless(os.name=='posix','POSIX native renderer')
    def test_native_lid_opens_above_the_console_and_hides_the_seated_disc(self):
        lib=ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary);binary=out/'preview'
            subprocess.run(['gcc','-O2','-std=c11','-Wall','-Wextra','-Werror',
                '-DSLOT_AUTHORED_MEDIA','-DSLOT_NEXT_MEDIA','-DSLOT_CARTRIDGE_MEDIA',
                '-I'+str(ROOT/'build/native/SDL-release-2.32.8/include'),
                '-DSLOT_HELPER_SOURCE="'+str(ROOT/'tools/slotlaunch/slot-launch.c')+'"',
                str(ROOT/'tools/consolebuild/offline-preview.c'),'-L'+str(lib),
                '-l:libSDL2_image-2.0.so.0','-l:libSDL2-2.0.so.0','-lm','-o',str(binary)],
                check=True,capture_output=True)
            env=dict(os.environ,LD_LIBRARY_PATH=str(lib),SDL_VIDEODRIVER='offscreen',
                EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',
                SLOT_MODEL_STYLE='realistic',SLOT_CONSOLE_COLOR='original')
            subprocess.run([str(binary),'psx',str(SLOT),str(out),'insert','diagnostic'],
                env=env,check=True,capture_output=True)
            def pixels(frame):return np.array(Image.open(out/f'insert-{frame:02d}.png').convert('RGB'))
            free,opened,closed=map(pixels,(0,33,60))
            def green(p):return (p[:,:,0]<20)&(p[:,:,1]>240)&(p[:,:,2]>70)&(p[:,:,2]<130)
            self.assertGreater(green(free).sum(),10000)
            self.assertGreater(green(opened).sum(),1000)
            self.assertEqual(green(closed).sum(),0,'Closed native lid must cover the disc')
            def highest_case(p):
                grey=(p.min(axis=2)>60)&(np.ptp(p.astype(int),axis=2)<15)
                return np.where(grey)[0].min()
            self.assertLess(highest_case(opened),highest_case(closed)-70,
                'Open lid must rise above the case, not rotate down through it')

if __name__=='__main__':unittest.main()
