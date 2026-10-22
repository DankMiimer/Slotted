import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.tabletop.editor import room

HERE=Path(__file__).resolve().parents[1]/'tools/tabletop/editor'

class RoomProfiles(unittest.TestCase):
    def home(self,tv='panasonic'):
        return room.parse_home((HERE/('home-default-'+tv+'.scene')).read_text(),tv)

    def test_full_home_source_and_native_round_trip(self):
        for tv in room.TVS:
            p=self.home(tv);self.assertEqual(len(p['consoles']),11)
            self.assertEqual(room.parse_home(room.native_text(p),tv),p)
            p['screen']=dict(position=[0,800,1100],target=[0,450,0],fov=40)
            self.assertEqual(room.parse_home(room.native_text(p),tv),p)

    def test_room_native_and_rejected_values(self):
        p=room.default_room();text=room.native_text(p)
        self.assertTrue(text.startswith('SLOTWORLD1\n'))
        self.assertEqual(text.count('\ntable '),3)
        self.assertEqual(room.parse_world(text),room.validate(p))
        self.assertEqual(room.native_text(room.parse_world(text)),text)
        for path,value in [(('floor',),True),(('floor',),float('nan')),(('tables','table','rotation'),[1,0,0]),(('tables','table','position'),[9000,0,0])]:
            bad=copy.deepcopy(p);target=bad
            for key in path[:-1]:target=target[key]
            target[path[-1]]=value
            with self.assertRaises(ValueError):room.validate(bad)
        bad=copy.deepcopy(p);bad['paths'].append(copy.deepcopy(bad['paths'][0]))
        with self.assertRaises(ValueError):room.validate(bad)

    def test_room_import_refuses_unknown_duplicate_and_incomplete_records(self):
        text=room.native_text(room.default_room())
        for invalid in [text+'future 1\n',text+'table table 0 0 0 0 0 0\n',text.replace('room 0','room nan'),
                        '\n'.join(text.splitlines()[2:]),'SLOTWORLD1\nroom 0 0 10 0 10 3000\n',
                        text+'path table wooden-table 1.4 0 0 0 0 0 0\n']:
            with self.subTest(text=invalid),self.assertRaises((ValueError,KeyError)):room.parse_world(invalid)

    def test_room_surfaces_write_slotworld2_and_round_trip(self):
        p=room.default_room()
        p['surfaces']=dict(floor=dict(color=[1,1,1],tile=1600,texture='oak-planks'),ceiling=dict(color=[.8,.8,.78],tile=1000))
        text=room.native_text(p)
        self.assertTrue(text.startswith('SLOTWORLD2\n'))
        self.assertIn('\nsurface floor 1 1 1 1600 oak-planks\n',text);self.assertIn('\nsurface ceiling 0.8 0.8 0.78 1000 -\n',text)
        self.assertEqual(room.parse_world(text),room.validate(p))
        self.assertEqual(room.textures(room.validate(p)),['oak-planks'])
        # No surfaces keeps the original format byte for byte.
        p['surfaces']={};self.assertEqual(room.native_text(p),room.native_text(room.default_room()))
        for surfaces in [dict(roof=dict(color=[1,1,1],tile=1000)),dict(floor=dict(color=[1.5,1,1],tile=1000)),
                         dict(floor=dict(color=[1,1,1],tile=20)),dict(wall=dict(color=[1,1,1],tile=1000,texture='../x')),
                         dict(wall=dict(color=[1,1,1]))]:
            bad=room.default_room();bad['surfaces']=surfaces
            with self.subTest(surfaces=surfaces),self.assertRaises(ValueError):room.validate(bad)
        old=room.native_text(room.default_room())
        for invalid in [old.replace('\nroom','\nsurface floor 1 1 1 1000 -\nroom',1),  # needs SLOTWORLD2
                        text.replace('surface ceiling','surface floor'),text+'surface wall 1 1 1 1000\n']:
            with self.subTest(text=invalid),self.assertRaises((ValueError,KeyError)):room.parse_world(invalid)

    def test_regional_duplicates_are_rejected(self):
        p=self.home();p['consoles']['snes-us']=copy.deepcopy(p['consoles']['snes'])
        with self.assertRaises(ValueError):room.validate(p)

    def test_saved_history_stale_editor_and_byte_preservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);p=self.home();result=room.save(root,p)
            path=Path(result['json']);original=path.read_bytes()
            # A no-op round trip preserves the exact durable JSON bytes.
            formatted=json.dumps(json.loads(original),separators=(',',':')).encode();path.write_bytes(formatted)
            sha=hashlib.sha256(formatted).hexdigest()
            same=room.save(root,p,sha);self.assertEqual(path.read_bytes(),formatted)
            p['objects']['tv']['position'][0]+=50
            with self.assertRaises(ValueError):room.save(root,p,result['sha256'])
            changed=room.save(root,p,same['sha256'])
            self.assertNotEqual(changed['sha256'],same['sha256'])
            self.assertEqual(next((root/'scene-layouts/history').glob('*.json')).read_bytes(),formatted)
            self.assertEqual(Path(changed['native']).read_text(),room.native_text(p))
            # Room creates separate files; it never rewrites the home scene.
            room.save(root,room.default_room());self.assertEqual(path.read_bytes(),(json.dumps(room.validate(p),indent=2)+'\n').encode())

if __name__=='__main__':unittest.main()
