import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('session_data',
    Path(__file__).resolve().parents[1] / 'tools/dev/session_data.py')
session_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_data)


class SnapshotTests(unittest.TestCase):
    def test_restore_preserves_changes_and_leaves_new_runtime_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save = root / 'saves/nds/example.sav'
            runtime = root / 'themes/art-book-slot/theme.xml'
            for path in (save, runtime):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'original')
            snapshot = session_data.Snapshot(root, 'session')
            snapshot.backup()
            save.write_bytes(b'changed save')
            runtime.write_bytes(b'new theme')
            added = save.with_name('new.sav')
            added.write_bytes(b'new save')
            result = snapshot.restore()
            self.assertEqual((result['modified'], result['new']), (1, 1))
            self.assertEqual(save.read_bytes(), b'original')
            self.assertFalse(added.exists())
            self.assertEqual(runtime.read_bytes(), b'new theme')
            park = Path(result['preserved']) / 'data/saves/nds'
            self.assertEqual((park / 'example.sav').read_bytes(), b'changed save')
            self.assertEqual((park / 'new.sav').read_bytes(), b'new save')
            self.assertFalse(snapshot.audit()['data']['changed'])
            snapshot.restore(runtime=True)
            self.assertEqual(runtime.read_bytes(), b'original')

    def test_corrupt_backup_is_rejected_before_live_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save = root / 'saves/example.sav'
            save.parent.mkdir()
            save.write_bytes(b'original')
            snapshot = session_data.Snapshot(root, 'session')
            snapshot.backup()
            save.write_bytes(b'keep this')
            (snapshot.directory / 'data/saves/example.sav').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                snapshot.restore()
            self.assertEqual(save.read_bytes(), b'keep this')
            with self.assertRaises(FileExistsError):
                snapshot.backup()

    def test_session_and_manifest_paths_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                session_data.Snapshot(directory, '../other')
            snapshot = session_data.Snapshot(directory, 'session')
            with self.assertRaises(ValueError):
                snapshot.checked('../outside')
