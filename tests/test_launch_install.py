"""Installer ownership guarantees: collisions leave both hooks untouched."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'theme/art-book-slot/_slot/launch/install.py'
spec = importlib.util.spec_from_file_location('launch_install', SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerOwnership(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'slot-launch').write_bytes(b'build fixture')
        (self.source / 'watch.py').write_bytes(b'watcher fixture')
        for name in installer.TARGETS:
            (self.source / name).write_bytes(b'#!/bin/sh\n# ' + installer.MARKER + b'\n')
        self.targets = {name: self.root / str(i) for i, name in enumerate(installer.TARGETS)}
        self.legacy = {name: self.root / 'legacy' for name in installer.LEGACY}

    def run_action(self, action):
        with patch.object(installer, 'TARGETS', self.targets), \
                patch.object(installer, 'LEGACY', self.legacy), \
                patch.object(installer, '__file__', str(self.source / 'install.py')), \
                patch.object(sys, 'argv', ['install.py', action]), \
                patch('subprocess.run') as watcher_action, \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            installer.main()
            if action in ('install', 'uninstall'):
                watcher_action.assert_called_once_with(
                    ['python3', str(self.source/'watch.py'), 'ensure' if action == 'install' else 'stop'], check=True)

    def test_collision_is_detected_before_either_hook_changes(self):
        names = list(self.targets)
        first = self.targets[names[0]] / names[0]
        second = self.targets[names[1]] / names[1]
        first.parent.mkdir()
        second.parent.mkdir()
        original = b'# ' + installer.MARKER + b'\nolder version\n'
        first.write_bytes(original)
        second.write_bytes(b'personal hook\n')
        with self.assertRaises(SystemExit):
            self.run_action('install')
        self.assertEqual(first.read_bytes(), original)
        self.assertEqual(second.read_bytes(), b'personal hook\n')

    def test_uninstall_keeps_other_hooks_and_can_be_repeated(self):
        self.run_action('install')
        self.run_action('install')
        unrelated = next(iter(self.targets.values())) / 'personal.sh'
        unrelated.write_bytes(b'personal hook\n')
        self.run_action('uninstall')
        self.run_action('uninstall')
        self.assertEqual(unrelated.read_bytes(), b'personal hook\n')
        for name, folder in self.targets.items():
            self.assertFalse((folder / name).exists())


    def test_install_removes_only_our_legacy_selection_hook(self):
        (self.root / 'legacy').mkdir()
        name = next(iter(self.legacy))
        ours = self.legacy[name] / name
        ours.write_bytes(b'#!/bin/sh\n# ' + installer.MARKER + b'\nold watcher\n')
        personal = self.legacy[name] / 'personal.sh'
        personal.write_bytes(b'personal hook\n')
        self.run_action('install')
        self.assertFalse(ours.exists())
        self.assertEqual(personal.read_bytes(), b'personal hook\n')

    def test_unrelated_file_with_legacy_name_is_kept(self):
        (self.root / 'legacy').mkdir()
        name = next(iter(self.legacy))
        foreign = self.legacy[name] / name
        foreign.write_bytes(b'someone else\n')
        self.run_action('install')
        self.assertEqual(foreign.read_bytes(), b'someone else\n')

    def test_selection_hook_is_not_installed(self):
        self.assertNotIn('game-selected', [folder.name for folder in installer.TARGETS.values()])


if __name__ == '__main__':
    unittest.main()
