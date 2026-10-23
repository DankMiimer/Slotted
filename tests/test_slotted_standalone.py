"""Complete package, authored-profile precedence and rejection before install writes."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.frontend.apply import PIN
from tools.publication.export import export
from tools.slot_theme import H700_RUNTIME_LIBRARIES
from tools.slotted import standalone,runtime
from tools.tabletop.editor import room

def elf():return b'\x7fELF\x02\x01'+bytes(12)+b'\xb7\x00'

def runtime_files():
    files={name:b'fixture' for name in runtime.REQUIRED}
    files['_slot/consoles/specs.json']=json.dumps({name:{} for name in runtime.MODELS}).encode()
    for name in runtime.SCENES:
        base='_slot/tabletop/'+name+'/'
        files[base+'scene.txt']=b'SCTABLETOP1 1\n0 0 0 1 1 1\n0 0 0 1 1 1\npart.mesh colour.png 0\n'
        files[base+'part.mesh']=b'full detail geometry'
        files[base+'colour.png']=b'texture'
    return files

class StandaloneTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.source=self.base/'source';self.source.mkdir()
        self.names=[]
        for name,data in runtime_files().items():
            if name=='_slot/launch/slot-launch':continue
            self.write(('theme/art-book-slot/' if name.startswith('_slot/') else 'theme/slotted/')+name,data)
        p=room.default_room();self.write('scene-layouts/room.json',json.dumps(p).encode())
        self.write('assets/tabletop/layouts/room.world',b'older generated derivative')
        self.write('LICENSE',b'MIT notice')
        self.write('release/publication.json',b'{"schema":1,"assets":[]}')
        self.names.append('release/public-files.txt')
        self.write('release/public-files.txt',('\n'.join(self.names)+'\n').encode(),add=False)
        # An ignored/private asset exists, but is never selected for the export.
        path=self.source/'theme/art-book-slot/_slot/local-models/master.glb'
        path.parent.mkdir(parents=True);path.write_bytes(b'valuable private full detail original')
        self.public=self.base/'public';export(self.public,self.source)
        self.work=self.base/'sdk';self.frontend=self.work/'frontend/emulationstation'
        self.frontend.parent.mkdir(parents=True);self.frontend.write_bytes(elf()+b''.join(standalone.MARKERS))
        self.helper=self.work/'slot-launch';self.helper.write_bytes(elf())
        inputs=dict(inputs=[dict(kind='target-library',runtimeName=name,sha256='1'*64) for name in H700_RUNTIME_LIBRARIES])
        (self.work/'build-inputs.json').write_text(json.dumps(inputs))
        digest=standalone.sha(self.work/'build-inputs.json')
        (self.work/'native-build.json').write_text(json.dumps(dict(sourcePin=PIN,frontendSha256=standalone.sha(self.frontend),
            buildInputsSha256=digest,compiler='test compiler')))
        (self.work/'slot-launch.json').write_text(json.dumps(dict(sourcePin=PIN,sha256=standalone.sha(self.helper),buildInputsSha256=digest)))
        for name in ['pugixml/LICENSE.md','id3v2lib/LICENSE','libcheevos/rcheevos/LICENSE','nanosvg/nanosvg_license.txt']:
            path=self.work/'frontend/external'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'required notice')

    def write(self,name,data,add=True):
        path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        if add:self.names.append(name)
        return path

    def package(self,name='bundle'):
        path=self.base/name
        standalone.package(self.public,self.frontend,self.helper,path)
        return path

    def test_deterministic_complete_bundle_uses_saved_json_and_retains_notices(self):
        before={p.relative_to(self.source).as_posix():standalone.sha(p) for p in self.source.rglob('*') if p.is_file()}
        first=self.package();second=self.package('second')
        self.assertEqual(standalone.sha(first/'payload.tar'),standalone.sha(second/'payload.tar'))
        release=standalone.inspect(first);self.assertFalse(release['firmwareLibrariesBundled'])
        with tarfile.open(first/'payload.tar') as tar:
            self.assertEqual(tar.extractfile('_slot/tabletop/layouts/room.world').read(),room.native_text(room.default_room()).encode())
            self.assertEqual(tar.getmember('_slot/launch/slot-launch').mode,0o755)
            self.assertEqual(len([n for n in tar.getnames() if n.startswith('_licenses/vendor/')]),4)
            self.assertFalse(any('local-models' in n or n.endswith('.so') for n in tar.getnames()))
        self.assertEqual(before,{p.relative_to(self.source).as_posix():standalone.sha(p) for p in self.source.rglob('*') if p.is_file()})
        with self.assertRaises(FileExistsError):self.package()

    def test_missing_referenced_scene_mesh_is_rejected_before_output(self):
        manifest=json.loads((self.public/'PUBLICATION_MANIFEST.json').read_text())
        selected=standalone.payload_files(self.public,manifest)
        selected['_slot/launch/slot-launch']=self.helper
        del selected['_slot/tabletop/pvm/part.mesh']
        with self.assertRaisesRegex(ValueError,'Missing standalone scene part'):
            runtime.validate(selected,lambda name:selected[name].read_bytes())

    def test_tampered_source_and_mismatched_helper_reject_before_output(self):
        helper_receipt=self.helper.with_suffix('.json');data=json.loads(helper_receipt.read_text());data['buildInputsSha256']='0'*64
        helper_receipt.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Helper and prepared'):self.package()
        self.assertFalse((self.base/'bundle').exists())
        (self.public/'theme/slotted/theme.xml').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.package()
        self.assertFalse((self.base/'bundle').exists())

    def test_inspect_rejects_archive_traversal_even_with_updated_receipts(self):
        path=self.package();manifest=json.loads((path/'manifest.json').read_text())
        data=b'escape';name='../outside';manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mode=0o644)
        with tarfile.open(path/'payload.tar','a') as tar:
            info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
        (path/'manifest.json').write_text(json.dumps(manifest))
        release=json.loads((path/'release.json').read_text());release['payloadSha256']=standalone.sha(path/'payload.tar')
        (path/'release.json').write_text(json.dumps(release))
        with self.assertRaisesRegex(ValueError,'Invalid publication path'):standalone.inspect(path)
        self.assertFalse((self.base/'outside').exists())

    def test_inspect_detects_missing_and_changed_runtime_members(self):
        path=self.package();release=json.loads((path/'release.json').read_text())
        manifest=json.loads((path/'manifest.json').read_text());del manifest['_slot/tabletop/pvm/part.mesh']
        (path/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):standalone.inspect(path)
        (path/'frontend-candidate').write_bytes(elf()+b'wrong')
        with self.assertRaisesRegex(ValueError,'checksum differs'):standalone.inspect(path)

if __name__=='__main__':unittest.main()
