"""Slotted's side-by-side install: staging, swap, settings migration and audit rules."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import sys
from unittest.mock import Mock, patch

from tools.slotted import device_install, install


def fake_device(root):
    legacy = root / 'themes/art-book-slot/_slot'
    (legacy / 'tabletop/layouts').mkdir(parents=True)
    (legacy / 'tabletop/layouts/gba-pvm.scene').write_text('SLOTLAYOUT1 legacy')
    (legacy / 'launch').mkdir()
    (legacy / 'launch/frontend-owned.sh').write_text('#!/bin/sh')
    settings = root / 'system/configs/emulationstation/themesettings'
    settings.mkdir(parents=True)
    (settings / 'art-book-slot.cfg').write_bytes(
        b'subset.slot-tv-model=pvm\rsubset.slot-gba=off\rsubset.slot-console-color=red\rsystemview=x\r')
    return device_install.Layout(root)


def payload(directory, files):
    manifest = {}
    with tarfile.open(directory / 'payload.tar', 'w') as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
            import hashlib
            manifest[name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    return directory / 'payload.tar', manifest


class SlottedInstall(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.layout = fake_device(self.root / 'userdata')
        self.job = self.root / 'job'
        self.job.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_package_excludes_runtime_assets(self):
        source = self.root / 'source'
        (source / '_slot').mkdir(parents=True)
        (source / '_slot/x.png').write_bytes(b'x')
        (source / '_tv').mkdir()
        (source / '_tv/gamelist.xml').write_text('<theme/>')
        (source / 'theme.xml').write_text('<theme/>')
        manifest = install.package(self.root / 'pkg', source)
        self.assertEqual(sorted(manifest), ['_tv/gamelist.xml', 'theme.xml'])

    def test_first_install_copies_legacy_assets_and_files(self):
        tar, manifest = payload(self.job, {'theme.xml': b'<theme/>', 'gb/theme.xml': b'<theme/>'})
        staging, source = device_install.stage(self.layout, tar, manifest, 's1')
        self.assertEqual(source, self.layout.legacy / '_slot')
        self.assertEqual((staging / '_slot/tabletop/layouts/gba-pvm.scene').read_text(), 'SLOTLAYOUT1 legacy')
        self.assertTrue((staging / 'gb/theme.xml').is_file())
        self.assertIsNone(device_install.swap(self.layout, staging, self.job / 'previous'))
        self.assertTrue((self.layout.target / 'theme.xml').is_file())
        self.assertTrue((self.layout.legacy / '_slot/launch/frontend-owned.sh').is_file())

    def test_update_keeps_slotted_layouts_unless_resync(self):
        tar, manifest = payload(self.job, {'theme.xml': b'<theme>2</theme>'})
        staging, _ = device_install.stage(self.layout, tar, manifest, 's1')
        device_install.swap(self.layout, staging, self.job / 'previous-1')
        (self.layout.target / '_slot/tabletop/layouts/gba-pvm.scene').write_text('SLOTLAYOUT1 uploaded to Slotted')
        staging, source = device_install.stage(self.layout, tar, manifest, 's2')
        self.assertEqual(source, self.layout.target / '_slot')
        self.assertIn('uploaded to Slotted', (staging / '_slot/tabletop/layouts/gba-pvm.scene').read_text())
        previous = device_install.swap(self.layout, staging, self.job / 'previous-2')
        self.assertTrue((previous / 'theme.xml').is_file())
        device_install.undo_swap(self.layout, previous)
        self.assertIn('uploaded to Slotted', (self.layout.target / '_slot/tabletop/layouts/gba-pvm.scene').read_text())
        staging, source = device_install.stage(self.layout, tar, manifest, 's3', resync=True)
        self.assertEqual(source, self.layout.legacy / '_slot')
        self.assertIn('legacy', (staging / '_slot/tabletop/layouts/gba-pvm.scene').read_text())

    def test_rejects_unsafe_or_mismatched_payload(self):
        for name in ('_slot/tabletop/layouts/x.scene', '../escape.xml'):
            tar, manifest = payload(self.job, {name: b'x'})
            with self.assertRaises(ValueError):
                device_install.stage(self.layout, tar, manifest, 'bad' + str(len(name)))
        tar, manifest = payload(self.job, {'theme.xml': b'<theme/>'})
        manifest['theme.xml']['sha256'] = '0' * 64
        with self.assertRaises(RuntimeError):
            device_install.stage(self.layout, tar, manifest, 'hash')

    def test_settings_migrate_once_and_only_slot_options(self):
        self.assertEqual(device_install.migrate_settings(self.layout), 'created')
        records = (self.layout.settings / 'Slotted.cfg').read_bytes().split(b'\r')
        self.assertEqual([r for r in records if r], [b'subset.slot-tv-model=pvm', b'subset.slot-console-color=red'])
        (self.layout.settings / 'Slotted.cfg').write_bytes(b'subset.slot-tv-model=oldtv\r')
        self.assertEqual(device_install.migrate_settings(self.layout), 'kept')
        self.assertEqual((self.layout.settings / 'Slotted.cfg').read_bytes(), b'subset.slot-tv-model=oldtv\r')

    def test_audit_allows_only_slotted_changes(self):
        clean = {'data': {'changed': [], 'new': ['system/configs/emulationstation/themesettings/Slotted.cfg']},
                 'runtime': {'changed': [], 'new': ['themes/Slotted/theme.xml']}}
        device_install.check_audit(clean, activate=False, migrated='created')
        with self.assertRaises(RuntimeError):
            device_install.check_audit(clean, activate=False, migrated='kept')
        activated = json.loads(json.dumps(clean))
        activated['data']['changed'] = ['system/configs/emulationstation/es_settings.cfg']
        device_install.check_audit(activated, activate=True, migrated='created')
        with self.assertRaises(RuntimeError):
            device_install.check_audit(activated, activate=False, migrated='created')
        stray = json.loads(json.dumps(clean))
        stray['runtime']['changed'] = ['themes/art-book-slot/theme.xml']
        with self.assertRaises(RuntimeError):
            device_install.check_audit(stray, activate=False, migrated='created')

    def test_rollback_keeps_failed_assets_and_rejects_an_external_target(self):
        self.layout.target.mkdir(parents=True)
        valuable = self.layout.target / 'local-model.mesh'
        valuable.write_bytes(b'full detail model')
        kept = device_install.undo_swap(self.layout, None, self.job / 'failed')
        self.assertFalse(self.layout.target.exists())
        self.assertEqual((kept / 'local-model.mesh').read_bytes(), b'full detail model')
        outside = self.root / 'outside'
        outside.mkdir()
        with self.assertRaises(ValueError):
            device_install.retain_failed(self.layout, outside, self.job / 'invalid')
        self.assertTrue(outside.is_dir())

    def test_install_respects_the_shared_device_transaction_lock(self):
        fake = Mock(LOCK_EX=2, LOCK_NB=4)
        fake.flock.side_effect = BlockingIOError
        with patch.dict(sys.modules, {'fcntl': fake}), patch.object(device_install, 'DEVICE_LOCK', self.job / 'lock'), \
                patch.object(device_install, '_run') as transaction:
            device_install.run(self.job)
        transaction.assert_not_called()
        self.assertEqual(json.loads((self.job / 'status.json').read_text())['state'], 'failed')

    def test_fresh_complete_runtime_does_not_need_legacy_theme(self):
        from test_slotted_standalone import runtime_files
        root=self.root/'fresh-userdata';layout=device_install.Layout(root)
        tar,manifest=payload(self.job,runtime_files())
        for entry in manifest.values():entry['mode']=0o644
        manifest['_slot/launch/slot-launch']['mode']=0o755
        staging,source=device_install.stage(layout,tar,manifest,'fresh',complete_runtime=True)
        self.assertIsNone(source)
        self.assertTrue((staging/'_slot/consoles/specs.json').is_file())
        self.assertFalse(layout.legacy.exists())
        device_install.swap(layout,staging,self.job/'old-fresh')
        authored=layout.target/'_slot/authored.json';authored.write_bytes(b'valuable layout')
        with self.assertRaisesRegex(ValueError,'refuses an existing'):
            device_install.stage(layout,tar,manifest,'update',complete_runtime=True)
        self.assertEqual(authored.read_bytes(),b'valuable layout')

    def test_bad_payload_is_rejected_before_staging_or_copying_user_assets(self):
        tar,manifest=payload(self.job,{'theme.xml':b'<theme/>'})
        manifest['theme.xml']['sha256']='0'*64
        with self.assertRaises(RuntimeError):device_install.stage(self.layout,tar,manifest,'bad-preflight')
        self.assertFalse((self.layout.themes/'.Slotted-bad-preflight').exists())

    def test_incomplete_dependency_record_is_refused_before_device_work(self):
        from tools.frontend.apply import PIN
        from tools.slotted.standalone import MARKERS
        data=bytearray(20);data[:6]=b'\x7fELF\x02\x01';data[18:20]=b'\xb7\x00'
        binary=self.job/'frontend';binary.write_bytes(bytes(data)+b''.join(MARKERS))
        config=dict(sourcePin=PIN,frontendSha256=device_install.digest(binary),runtimeLibraryHashes={})
        with self.assertRaisesRegex(ValueError,'dependency record is incomplete'):
            device_install.check_standalone(config,binary,self.job)

    def test_failed_swap_restores_previous_theme_before_returning_error(self):
        self.layout.target.mkdir(parents=True)
        (self.layout.target/'authored.scene').write_bytes(b'latest authored layout')
        staging=self.layout.themes/'.Slotted-swap-test';staging.mkdir()
        previous=self.job/'previous-swap'
        rename=Path.rename
        def fail_one(path,target):
            if path==staging:raise OSError('simulated rename failure')
            return rename(path,target)
        with patch.object(Path,'rename',fail_one),self.assertRaisesRegex(OSError,'simulated'):
            device_install.swap(self.layout,staging,previous)
        self.assertEqual((self.layout.target/'authored.scene').read_bytes(),b'latest authored layout')
        self.assertTrue(staging.exists())

    def test_mid_stage_failure_retains_owned_partial_path_for_rollback(self):
        tar,manifest=payload(self.job,{'theme.xml':b'<theme/>'})
        paths=[]
        with patch.object(device_install.shutil,'copytree',side_effect=OSError('simulated interrupted copy')):
            with self.assertRaisesRegex(OSError,'interrupted'):
                device_install.stage(self.layout,tar,manifest,'interrupted',on_created=paths.append)
        self.assertEqual(len(paths),1)
        self.assertTrue(paths[0].exists())
        retained=device_install.retain_failed(self.layout,paths[0],self.job/'retained-stage')
        self.assertTrue(retained.exists())
        self.assertTrue((self.layout.legacy/'_slot/launch/frontend-owned.sh').exists())


if __name__ == '__main__':
    unittest.main()
