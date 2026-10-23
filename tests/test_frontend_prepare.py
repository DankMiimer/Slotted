"""Portable build input preflights and safe header extraction without network/compiler."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from tools.frontend import prepare_build as setup
from tools.frontend.apply import PIN

class BuildPreparationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.libs=self.root/'libs';self.libs.mkdir()
        for name in setup.LIBRARIES:(self.libs/name).write_bytes(b'\x7fELF\x02\x01'+bytes(12)+b'\xb7\x00')

    def test_wrong_abi_fails_before_creating_workspace(self):
        (self.libs/setup.LIBRARIES[0]).write_bytes(b'host x86_64 ELF')
        with self.assertRaisesRegex(ValueError,'AArch64'):
            setup.prepare(self.root/'sdk',self.libs,download=True)
        self.assertFalse((self.root/'sdk').exists())

    def test_wrong_cached_package_fails_before_creating_workspace(self):
        packages=self.root/'packages';packages.mkdir();(packages/'api.deb').write_bytes(b'altered')
        lock=self.root/'lock.json';lock.write_text(json.dumps(dict(packages=[dict(filename='api.deb',sha256='0'*64)])))
        with self.assertRaisesRegex(ValueError,'SHA-256 differs'):
            setup.prepare(self.root/'sdk',self.libs,packages=packages,lock=lock)
        self.assertFalse((self.root/'sdk').exists())

    def test_download_rejects_insecure_url_and_wrong_hash(self):
        target=self.root/'header';target.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError,'HTTPS'):setup.checked_download('http://example.org/a',target,'0'*64)
        with patch.object(setup.urllib.request,'urlopen') as network:
            with self.assertRaisesRegex(ValueError,'SHA-256 differs'):setup.checked_download('https://example.org/a',target,'0'*64)
            network.assert_not_called()
        self.assertEqual(target.read_bytes(),b'wrong')

    def test_sdl_extraction_rejects_traversal_and_header_links(self):
        for i,name in enumerate(['../escape','SDL-release-2/include/linked.h']):
            archive=self.root/('sdl'+str(i)+'.tar')
            with tarfile.open(archive,'w') as tar:
                member=tarfile.TarInfo(name)
                if i:member.type=tarfile.SYMTYPE;member.linkname='/outside'
                tar.addfile(member,io.BytesIO(b''))
            with self.assertRaises(ValueError):setup.sdl_headers(archive,self.root/('out'+str(i)),'2')
        self.assertFalse((self.root/'escape').exists())

    def test_verifier_detects_modified_target_library_or_header(self):
        work=self.root/'sdk';work.mkdir();(work/'headers').mkdir();(work/'headers/api.h').write_bytes(b'API')
        record=dict(sourcePin=PIN,sourcePrepared=False,libraries=str(self.libs),sdlHeaders=str(work/'headers'),
            inputs=[dict(kind='target-library',name=setup.LIBRARIES[0],sha256=setup.sha(self.libs/setup.LIBRARIES[0]))],
            headerHashes={'api.h':setup.sha(work/'headers/api.h')},sdlHeaderHashes={})
        (work/'build-inputs.json').write_text(json.dumps(record));setup.verify_workspace(work)
        (work/'headers/api.h').write_bytes(b'changed API')
        with self.assertRaisesRegex(ValueError,'header changed'):setup.verify_workspace(work)
        (self.libs/setup.LIBRARIES[0]).write_bytes(b'changed library')
        with self.assertRaisesRegex(ValueError,'input changed'):setup.verify_workspace(work)

if __name__=='__main__':unittest.main()
