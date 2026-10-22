"""New room formats must not be sent to legacy installs or old frontends."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.tabletop.editor import room, server, upload
from tests.test_editor_upload import device

class RoomUploadTests(unittest.TestCase):
    def profiles(self):
        home=room.parse_home((upload.HERE/'home-default-panasonic.scene').read_text(),'panasonic')
        return [room.default_room(),home]

    def test_new_formats_require_slotted_and_binary_capability(self):
        profiles=self.profiles();spec=dict(roomFormats=['SLOTWORLD1','SLOTHOME1'])
        for theme,record,binary in [('art-book-slot',spec,upload.ROOM_MARKER),('Slotted',{},upload.ROOM_MARKER),('Slotted',spec,b'old binary')]:
            with self.subTest(theme=theme,record=record),self.assertRaises(ValueError):upload.room_frontend(profiles,theme,record,binary)
        self.assertEqual(upload.room_frontend(profiles,'Slotted',spec,upload.ROOM_MARKER),['SLOTHOME1','SLOTWORLD1'])
        self.assertEqual(upload.room_frontend([dict(system='snes',tv='panasonic')],'art-book-slot',{},b'old binary'),[])

    def test_room_surfaces_need_the_surfaces_frontend_and_ship_their_textures(self):
        p=room.default_room();p['surfaces']=dict(floor=dict(color=[1,1,1],tile=1600,texture='oak-planks'),wall=dict(color=[.4,.4,.4],tile=1000))
        p=room.validate(p);old=dict(roomFormats=['SLOTWORLD1','SLOTHOME1']);new=dict(roomFormats=['SLOTWORLD1','SLOTWORLD2','SLOTHOME1'])
        for record,binary in [(old,upload.SURFACES_MARKER),(new,upload.ROOM_MARKER)]:
            with self.subTest(record=record,binary=binary),self.assertRaises(ValueError):upload.room_frontend([p],'Slotted',record,binary)
        self.assertEqual(upload.room_frontend([p],'Slotted',new,upload.SURFACES_MARKER),['SLOTWORLD1','SLOTWORLD2'])
        self.assertEqual(upload.room_frontend([room.default_room()],'Slotted',old,upload.ROOM_MARKER),['SLOTWORLD1'])
        with tempfile.TemporaryDirectory() as temporary,patch.object(upload,'ROOT',Path(temporary)):
            own=Path(temporary)/'scene-layouts/surfaces';own.mkdir(parents=True);(own/'oak-planks.png').write_bytes(b'png')
            with patch.object(upload,'BUILD',Path(temporary)/'build/tabletop'),patch.object(upload,'theme_slot',return_value=Path(temporary)/'missing'):
                with self.assertRaises(ValueError):upload.dependencies(p)  # tables are not prepared here
            self.assertEqual(room.texture_path(temporary,'oak-planks'),own/'oak-planks.png')
            with self.assertRaises(ValueError):room.texture_path(temporary,'walnut-planks')
        files=upload.dependencies(p)
        self.assertEqual(files['_slot/tabletop/surfaces/oak-planks.png'],room.texture_path(upload.ROOT,'oak-planks'))
        self.assertEqual([k for k in files if '/surfaces/' in k],['_slot/tabletop/surfaces/oak-planks.png'])
        request=dict(theme='Slotted',preview=False,layouts=['room'],roomFormats=['SLOTWORLD1','SLOTWORLD2'],files={})
        self.assertEqual(device.check_request(request),{})

    def test_device_refuses_undeclared_or_legacy_room_files(self):
        request=dict(theme='Slotted',preview=False,layouts=['room','home-panasonic'],roomFormats=['SLOTWORLD1','SLOTHOME1'],files={})
        self.assertEqual(device.check_request(request),{})
        for changes in [dict(theme='art-book-slot'),dict(roomFormats=[]),dict(layouts=['home-bad']),dict(layouts=[],files={'_slot/tabletop/layouts/room.world':dict(sha256='x')})]:
            bad=copy.deepcopy(request);bad.update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):device.check_request(bad)

    def test_batch_keeps_room_and_home_native_extensions_and_sources(self):
        profiles=self.profiles()
        with tempfile.TemporaryDirectory() as temporary,patch.object(upload,'BUILD',Path(temporary)),patch.object(upload.Uploads,'worker') as worker:
            entries=[dict(profile=p,source=json.dumps(p).encode(),native=room.native_text(p)) for p in profiles]
            jobs=upload.Uploads();result=jobs.start_batch(lambda:entries,background=False)
            self.assertEqual(result['layouts'],['room','home-panasonic']);worker.assert_called_once()
            for entry in entries:
                folder=Path(result['evidence'])/'layouts';key=upload.entry_key(entry)
                self.assertEqual((folder/Path(upload.native_file(entry)).name).read_text(),entry['native'])
                self.assertEqual((folder/(key+'.json')).read_bytes(),entry['source'])

    def test_saved_batch_detects_concurrent_room_edit(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(server,'ROOT',Path(temporary)):
            p=room.default_room();room.save(temporary,p)
            row=next(r for r in server.saved_layouts() if r['key']=='room')
            entries=server.batch_entries(['room'],{'room':row['sha256']})
            self.assertEqual(upload.native_file(entries[0]),'_slot/tabletop/layouts/room.world')
            path=Path(temporary)/'scene-layouts/room.json';sha=hashlib.sha256(path.read_bytes()).hexdigest()
            p['tables']['table']['position'][0]+=100;room.save(temporary,p,sha)
            with self.assertRaises(ValueError):server.batch_entries(['room'],{'room':row['sha256']})

    def test_current_home_dependencies_preserve_full_runtime_variants(self):
        files=upload.dependencies(self.profiles()[1])
        for key in ['snes','snes-us','md','md-jp','gba','psp']:
            self.assertIn('_slot/consoles/'+key+'/model.mesh',files)
        self.assertTrue(any('local-models/consoles/gba/' in name for name in files))
        self.assertFalse(any(path.suffix in ('.glb','.zip','.blend') for path in files.values()))

    def test_device_room_import_is_read_only_and_reports_local_differences(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(server,'ROOT',Path(temporary)):
            for p in self.profiles():
                key=room.profile_key(p);text=room.native_text(p)
                device=dict(theme='Slotted',layouts={key:dict(text=text,sha256=upload.digest(text.encode()))})
                with patch.object(server,'device_layouts',return_value=device):
                    result=server.device_room(p['kind'],p.get('tv','panasonic'))
                    self.assertTrue(result['found']);self.assertFalse(result['matchesSaved'])
                    self.assertEqual(room.native_text(result['profile']),text)
                    self.assertFalse((Path(temporary)/'scene-layouts'/(key+'.json')).exists())
                    saved=room.save(temporary,p);before=Path(saved['json']).read_bytes()
                    result=server.device_room(p['kind'],p.get('tv','panasonic'))
                    self.assertTrue(result['matchesSaved'])
                    self.assertEqual(Path(saved['json']).read_bytes(),before)
            with patch.object(server,'device_layouts',return_value=dict(layouts={})):
                self.assertFalse(server.device_room('room','pvm')['found'])

if __name__=='__main__':unittest.main()
