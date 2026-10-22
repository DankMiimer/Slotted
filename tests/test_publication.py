"""Publication isolation, hash verification and no-overwrite restore boundaries."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.publication.export import checkout_bytes, digest, export, inputs, relative, verify
from tools.publication.restore_assets import restore


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        self.root.mkdir()
        self.output = self.base / 'public'
        self.write('README.md', b'Original project code is MIT.\n')
        self.write('build/tabletop/assets/table/part.mesh', b'\0original-full-detail-mesh')
        self.asset = dict(source='build/tabletop/assets/table/part.mesh',
                          destination='assets/tabletop/table/part.mesh',
                          restore='build/tabletop/assets/table/part.mesh',
                          sha256=digest(self.root / 'build/tabletop/assets/table/part.mesh'),
                          license='CC-BY-4.0')
        self.write('release/publication.json', json.dumps(dict(schema=1, assets=[self.asset])).encode())
        self.write('release/public-files.txt', b'README.md\nrelease/publication.json\nrelease/public-files.txt\n')

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_exports_only_allowlist_and_pinned_assets_without_changing_sources(self):
        private = self.write('tools/dev/device.txt', b'private target')
        editorial = self.write('theme/art-book-slot/_slot/local-models/model.glb', b'editorial')
        before = {p.relative_to(self.root).as_posix(): digest(p) for p in self.root.rglob('*') if p.is_file()}
        result = export(self.output, self.root)
        self.assertEqual(result, verify(self.output))
        self.assertFalse((self.output / private.relative_to(self.root)).exists())
        self.assertFalse((self.output / editorial.relative_to(self.root)).exists())
        after = {p.relative_to(self.root).as_posix(): digest(p) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_asset_hash_change_fails_before_output_created(self):
        self.write(self.asset['source'], b'different model')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            export(self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_export_normalizes_code_for_git_without_changing_source_or_assets(self):
        self.write('README.md', b'first\r\nsecond\r\n')
        export(self.output, self.root)
        self.assertEqual((self.output/'README.md').read_bytes(), b'first\nsecond\n')
        self.assertEqual((self.root/'README.md').read_bytes(), b'first\r\nsecond\r\n')
        self.assertEqual(checkout_bytes('tools/example.ps1', b'line\n'), b'line\r\n')
        for name in ['assets/table/scene.txt', 'theme/model-info.json',
                     'third_party/source.json', 'scene-layouts/authored.json']:
            self.assertEqual(checkout_bytes(name, b'original\r\n'), b'original\r\n')
        self.assertEqual(checkout_bytes('binary.ico', b'\0\r\n'), b'\0\r\n')
        self.assertEqual(checkout_bytes('legacy.md', b'Upload\x92\r\n'), b'Upload\x92\n')
        self.assertEqual(checkout_bytes('audio.pcm', b'\xff\r\n'), b'\xff\r\n')

    def test_refuses_existing_output_and_audit(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            export(self.output, self.root)
        other = self.base / 'other'
        (self.base / 'other-audit.json').write_text('previous report')
        with self.assertRaisesRegex(ValueError, 'Audit report already exists'):
            export(other, self.root)
        self.assertFalse(other.exists())

    def test_detects_extra_missing_and_changed_files(self):
        export(self.output, self.root)
        (self.output / 'extra.txt').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'file set differs'):
            verify(self.output)
        (self.output / 'extra.txt').unlink()
        saved = (self.output / 'README.md').read_bytes()
        (self.output / 'README.md').unlink()
        with self.assertRaisesRegex(ValueError, 'file set differs'):
            verify(self.output)
        (self.output / 'README.md').write_bytes(saved + b'altered')
        with self.assertRaisesRegex(ValueError, 'checksum differs'):
            verify(self.output)

    def test_sensitive_file_is_blocked_even_if_allowlisted(self):
        self.write('tools/dev/device.txt', b'target')
        with (self.root / 'release/public-files.txt').open('a') as stream:
            stream.write('tools/dev/device.txt\n')
        with self.assertRaisesRegex(ValueError, 'Forbidden publication path'):
            inputs(self.root)

    def test_secret_scan_does_not_print_secret(self):
        secret = b'ghp_' + b'x' * 40
        self.write('README.md', secret)
        with self.assertRaises(ValueError) as failure:
            inputs(self.root)
        self.assertIn('GitHub token', str(failure.exception))
        self.assertNotIn(secret.decode(), str(failure.exception))

    def test_rejects_unsafe_paths(self):
        for value in ('../outside', '/absolute', 'C:/drive', 'a\\b', '.', 'a//b', 'a/../b', '*.py'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                relative(value)

    def test_rejects_source_links(self):
        target = self.write('original.txt', b'outside allowlist')
        readme = self.root / 'README.md'
        readme.unlink()
        try:
            readme.symlink_to(target)
        except OSError:
            self.skipTest('Symlinks require Windows developer mode or privilege')
        with self.assertRaisesRegex(ValueError, 'Linked publication input'):
            inputs(self.root)

    def test_restore_is_idempotent_and_refuses_conflicts_before_any_write(self):
        export(self.output, self.root)
        self.assertEqual(restore(self.output), dict(copied=1, alreadyPresent=0))
        self.assertEqual(restore(self.output), dict(copied=0, alreadyPresent=1))
        restored = self.output / self.asset['restore']
        restored.write_bytes(b'user edited model')
        with self.assertRaisesRegex(ValueError, 'Existing asset differs'):
            restore(self.output)
        self.assertEqual(restored.read_bytes(), b'user edited model')

    def test_reexport_from_public_clone_uses_durable_asset_copy(self):
        export(self.output, self.root)
        second = self.base / 'second'
        export(second, self.output)
        self.assertEqual((second / self.asset['destination']).read_bytes(),
                         (self.root / self.asset['source']).read_bytes())
        verify(second)

    def derivative(self, destination, original, corrected):
        source = self.write('assets/publication-derivatives/approved.dat', corrected)
        record = dict(destination=destination, source=source.relative_to(self.root).as_posix(),
                      originalSha256=__import__('hashlib').sha256(original).hexdigest(), sha256=digest(source))
        self.write('release/asset-derivatives.json', json.dumps(dict(schema=1, files=[record])).encode())
        with (self.root/'release/public-files.txt').open('a') as stream:
            stream.write('release/asset-derivatives.json\n')
        return record

    def test_public_derivative_preserves_original_and_reexports_without_private_inputs(self):
        original = (self.root/'README.md').read_bytes()
        record = self.derivative('README.md', original, b'Reviewed public derivative\n')
        export(self.output, self.root)
        self.assertEqual((self.root/'README.md').read_bytes(), original)
        self.assertEqual(digest(self.output/'README.md'), record['sha256'])
        self.assertFalse((self.output/record['source']).exists())
        second = self.base/'second'
        export(second, self.output)
        verify(second)
        self.assertEqual(digest(second/'README.md'), record['sha256'])

    def test_asset_derivative_updates_public_pin_and_restore_map(self):
        original = (self.root/self.asset['source']).read_bytes()
        record = self.derivative(self.asset['destination'], original, b'\0corrected model')
        export(self.output, self.root)
        verify(self.output)
        config = json.loads((self.output/'release/publication.json').read_text())
        self.assertEqual(config['assets'][0]['sha256'], record['sha256'])
        self.assertEqual(config['assets'][0]['bytes'], len(b'\0corrected model'))
        restore(self.output)
        self.assertEqual(digest(self.output/self.asset['restore']), record['sha256'])
        export(self.base/'second', self.output)
        self.assertEqual(digest(self.root/self.asset['source']), self.asset['sha256'])

    def test_derivative_rejects_changed_original_before_export(self):
        self.derivative('README.md', (self.root/'README.md').read_bytes(), b'corrected')
        self.write('README.md', b'user edited input')
        with self.assertRaisesRegex(ValueError, 'Unreviewed derivative input'):
            export(self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_derivative_rejects_unsafe_source_and_tampering(self):
        original = (self.root/'README.md').read_bytes()
        record = self.derivative('README.md', original, b'approved')
        self.write(record['source'], b'changed')
        with self.assertRaisesRegex(ValueError, 'Derivative hash differs'):
            export(self.output, self.root)
        self.assertFalse(self.output.exists())
        record['source'] = '../outside'
        self.write('release/asset-derivatives.json', json.dumps(dict(schema=1, files=[record])).encode())
        with self.assertRaisesRegex(ValueError, 'Derivative source must be under'):
            export(self.output, self.root)

    def test_derivative_pin_rejects_art_reintroduced_into_rehashed_snapshot(self):
        original=(self.root/'README.md').read_bytes()
        self.derivative('README.md',original,b'approved')
        export(self.output,self.root)
        (self.output/'README.md').write_bytes(original)
        manifest=self.output/'PUBLICATION_MANIFEST.json'
        value=json.loads(manifest.read_text());value['files']['README.md'].update(bytes=len(original),sha256=digest(self.output/'README.md'))
        manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Public derivative pin differs'):
            verify(self.output)

    def test_public_rebuild_keeps_approved_repair_and_rejects_other_changes(self):
        import numpy as np
        from PIL import Image
        from tools.publication.derivatives import approved_albedo
        name = 'theme/model.albedo.png'
        pixels = np.full((4,4,4), 255, dtype=np.uint8)
        approved = pixels.copy();approved[1:3,1:3,:3] = 100
        path = self.root/name;path.parent.mkdir(parents=True);Image.fromarray(approved).save(path)
        record = dict(destination=name,source='assets/publication-derivatives/test.png',
                      originalSha256='0'*64,sha256=digest(path),pixelBox=[1,1,3,3])
        self.write('release/asset-derivatives.json', json.dumps(dict(schema=1,files=[record])).encode())
        self.assertTrue(np.array_equal(approved_albedo(self.root,name,pixels),pixels))
        self.write('PUBLICATION_MANIFEST.json',b'{}')
        self.assertTrue(np.array_equal(approved_albedo(self.root,name,pixels),approved))
        changed=pixels.copy();changed[0,0,0]=1
        with self.assertRaisesRegex(ValueError,'unreviewed albedo pixels'):
            approved_albedo(self.root,name,changed)

    def test_restore_rejects_destination_outside_build_research(self):
        export(self.output, self.root)
        record = dict(self.asset, restore='README.md')
        (self.output / 'assets/restore-map.json').write_text(json.dumps([record]))
        with self.assertRaisesRegex(ValueError, 'under build/research'):
            restore(self.output)

    def test_duplicate_restore_destinations_rejected_before_writes(self):
        export(self.output, self.root)
        (self.output / 'assets/restore-map.json').write_text(json.dumps([self.asset, self.asset]))
        with self.assertRaisesRegex(ValueError, 'Duplicate asset restore'):
            restore(self.output)
        self.assertFalse((self.output / self.asset['restore']).exists())

    @unittest.skipUnless(shutil.which('git'), 'Git is required for checkout verification')
    def test_real_git_checkout_keeps_manifest_and_asset_hashes(self):
        self.write('.gitattributes', (Path(__file__).resolve().parents[1]/'.gitattributes').read_bytes())
        self.write('README.md', b'Legacy punctuation \x92\r\n')
        self.write('tools/check.ps1', b'Write-Output "hello"\n')
        self.write('theme/model-info.json', b'{"keep":true}\r\n')
        source = self.write('build/tabletop/assets/table/scene.txt', b'SCTABLETOP1\r\n')
        self.asset = dict(self.asset, source='build/tabletop/assets/table/scene.txt',
                          destination='assets/tabletop/table/scene.txt',
                          restore='build/tabletop/assets/table/scene.txt', sha256=digest(source))
        self.write('release/publication.json', json.dumps(dict(schema=1, assets=[self.asset])).encode())
        with (self.root/'release/public-files.txt').open('a') as stream:
            stream.write('.gitattributes\ntools/check.ps1\ntheme/model-info.json\n')
        export(self.output, self.root)
        def git(*args):
            subprocess.run(['git', *args], cwd=self.output, check=True, capture_output=True)
        git('init', '--quiet', '-b', 'main')
        git('add', '--pathspec-from-file=UPLOAD_PATHS.txt')
        git('-c', 'user.name=Publication Test', '-c', 'user.email=publication@example.invalid',
            '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=unused-test-hooks',
            'commit', '--quiet', '-m', 'Test publication checkout')
        checkout = self.base/'checkout'
        git('-c', 'core.autocrlf=true', 'clone', '--quiet', '--no-hardlinks', str(self.output), str(checkout))
        verify(checkout)
        self.assertEqual((checkout/'assets/tabletop/table/scene.txt').read_bytes(), b'SCTABLETOP1\r\n')


if __name__ == '__main__':
    unittest.main()
