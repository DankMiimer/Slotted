"""Boot activation, firmware fallback and exact startup recovery without a device."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.frontend import persistence as p


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PersistentFrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'userdata/frontend'
        self.hook = self.root / 'boot/postshare.sh'
        self.official = self.root / 'official'
        self.official.write_bytes(b'firmware')
        self.binary = self.root / 'new-frontend'
        self.binary.write_bytes(b'tabletop')
        self.mounts = self.root / 'mounts'
        self.mounts.write_text('/dev/test /boot vfat ro,relatime 0 0\n')
        for name, value in dict(BASE=self.base, HOOK=self.hook,
                                OFFICIAL=self.official, MOUNTS=self.mounts).items():
            manager = patch.object(p, name, value)
            manager.start()
            self.addCleanup(manager.stop)
        self.commands = []
        def run(args, **kw):
            self.commands.append(args)
            if args[:2] == ['mount', '--bind']:
                self.official.write_bytes(Path(args[2]).read_bytes())
                self.mounts.write_text(self.mounts.read_text() + 'bind ' + str(self.official) + ' none rw 0 0\n')
            return subprocess.CompletedProcess(args, 1 if args[0] == 'pidof' else 0)
        self.run = patch.object(p.subprocess, 'run', side_effect=run).start()
        self.addCleanup(patch.stopall)

    def install(self):
        return p.install(self.binary, sha(b'tabletop'), sha(b'firmware'))

    def test_boot_mounts_hash_pinned_frontend_once_without_launching(self):
        expected = self.install()
        p.verify(expected)
        result = p.activate()
        self.assertEqual(result['sha256'], sha(b'tabletop'))
        self.assertFalse(result['alreadyActive'])
        self.assertTrue(p.activate()['alreadyActive'])
        self.assertEqual(sum(c[:2] == ['mount', '--bind'] for c in self.commands), 1)
        self.assertFalse(any(c[0] in ('setsid', '/etc/init.d/S31emulationstation') for c in self.commands))
        self.assertEqual(self.commands[0:2], [['mount', '-o', 'remount,rw', '/boot'],
                                            ['mount', '-o', 'remount,ro', '/boot']])

    def test_corrupt_or_missing_binary_and_changed_firmware_keep_stock(self):
        expected = self.install()
        target = self.base / expected['binary']
        target.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            p.activate()
        target.unlink()
        with self.assertRaises(FileNotFoundError):
            p.activate()
        target.write_bytes(b'tabletop')
        self.official.write_bytes(b'new firmware')
        with self.assertRaisesRegex(RuntimeError, 'Firmware frontend changed'):
            p.activate()
        self.assertFalse(any(c[:2] == ['mount', '--bind'] for c in self.commands))

    def test_active_process_blocks_binding(self):
        self.install()
        self.run.side_effect = lambda args, **kw: subprocess.CompletedProcess(args, 0)
        with self.assertRaisesRegex(RuntimeError, 'already running'):
            p.activate()
        self.assertEqual(self.official.read_bytes(), b'firmware')

    def test_hook_preserves_existing_script_and_survives_its_exit(self):
        prior = b'#!/bin/bash\n# user hook\nexit 0\n'
        current = p.hook_bytes(prior)
        self.assertLess(current.index(p.BEGIN), current.index(b'exit 0'))
        self.assertEqual(p.hook_bytes(current), current)
        start = current.index(p.BEGIN)
        end = current.index(p.END) + len(p.END)
        self.assertEqual(current[:start] + current[end:], prior)
        with self.assertRaises(ValueError):
            p.hook_bytes(current + p.BEGIN)

    def test_recovery_restores_exact_hook_and_selection_after_upgrade(self):
        self.install()
        original = {k: f.read_bytes() for k, f in p.managed_paths().items()}
        backup = self.root / 'recovery'
        p.capture(backup)
        self.binary.write_bytes(b'newer tabletop')
        latest = p.install(self.binary, sha(b'newer tabletop'), sha(b'tabletop'))
        self.assertEqual(latest['stockSha256'], sha(b'firmware'))
        self.assertTrue((self.base / ('emulationstation-' + sha(b'tabletop'))).is_file())
        p.restore(backup)
        self.assertEqual({k: f.read_bytes() for k, f in p.managed_paths().items()}, original)
        self.assertTrue((self.base / latest['binary']).is_file(), 'Keep failed version for recovery')

    def test_initial_install_rollback_restores_absent_hook_and_config(self):
        backup = self.root / 'recovery'
        p.capture(backup)
        self.install()
        p.restore(backup)
        self.assertFalse(any(f.exists() for f in p.managed_paths().values()))
        self.assertTrue((self.base / ('emulationstation-' + sha(b'tabletop'))).is_file())

    def test_bad_upload_hash_does_not_change_startup_files(self):
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            p.install(self.binary, sha(b'bad'), sha(b'firmware'))
        self.assertFalse(self.hook.exists())
        self.assertFalse(self.base.exists())

    def test_readonly_boot_is_restored_when_writing_hook_fails(self):
        original = p.atomic
        def fail_hook(path, *args, **kw):
            if path == self.hook:
                raise OSError('disk full')
            return original(path, *args, **kw)
        with patch.object(p, 'atomic', side_effect=fail_hook), self.assertRaisesRegex(OSError, 'disk full'):
            self.install()
        self.assertEqual(self.commands[-1], ['mount', '-o', 'remount,ro', '/boot'])

    def test_corrupt_recovery_never_changes_live_startup(self):
        self.install()
        backup = self.root / 'recovery'
        p.capture(backup)
        (backup / 'hook').write_bytes(b'broken backup')
        before = self.hook.read_bytes()
        with self.assertRaises(ValueError):
            p.restore(backup)
        self.assertEqual(self.hook.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
