"""Publication isolation, hash verification and no-overwrite restore boundaries."""
import json
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
