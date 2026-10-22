"""Narrow recovery of channel metadata omitted by the first trial snapshot."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from tools.dev import esdev,session_data
from tools.slotted import device_install

spec=importlib.util.spec_from_file_location('slotted_trial_under_test',Path(device_install.__file__).with_name('device_trial.py'))
trial=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'fcntl':Mock(),'esdev':esdev,'session_data':session_data,'device_install':device_install,'transition_frontend_trial':Mock(),'frontend_persistence':Mock()}):spec.loader.exec_module(trial)

class ChannelRecovery(unittest.TestCase):
    def test_bounded_experimental_options_and_visibility(self):
        trial.validate_options({})
        trial.validate_options(dict(allModels=True,indexBatch=3072,motion='reduced',tv='pvm'))
        trial.validate_options(dict(screensaverMs=15000,style='cel',color='red'))
        for value in [dict(style='toon'),dict(color='pink')]:
            with self.assertRaises(ValueError):trial.validate_options(value)
        for value in [dict(allModels='yes'),dict(indexBatch=True),dict(indexBatch=-1),dict(indexBatch=2048),dict(tv='unknown'),dict(screensaverMs=1000),dict(screensaverMs='15000')]:
            with self.assertRaises(ValueError):trial.validate_options(value)
        self.assertEqual(trial.show_modelled_systems('ports;megadrive;mpv;genesis;snes;private-system'),'ports;mpv;private-system')
        self.assertEqual(trial.show_modelled_systems(None),'')

    def test_recovery_rebind_retries_after_a_wrapper_restart(self):
        import subprocess
        busy=subprocess.CalledProcessError(32,['umount'])
        with patch.object(trial,'bind',side_effect=[busy,busy,None]) as bind,patch.object(trial.esdev,'stop') as stop,patch.object(trial.esdev,'es_pid',return_value=None),patch.object(trial.time,'sleep'):
            self.assertEqual(trial.rebind(Path('previous-frontend')),2)
            self.assertEqual(bind.call_count,3);self.assertEqual(stop.call_count,3)
        with patch.object(trial,'bind',side_effect=busy),patch.object(trial.esdev,'stop'),patch.object(trial.esdev,'es_pid',return_value=None),patch.object(trial.time,'sleep'):
            with self.assertRaises(subprocess.CalledProcessError):trial.rebind(Path('previous-frontend'),attempts=2)

    def test_logs_on_tmpfs_are_linked_then_collected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);job=root/'job'/'slotted-ui-x';job.mkdir(parents=True)
            (job/'stream.tsv').write_text('stale')
            with patch.object(trial,'LOGS',root/'tmp'):
                logs=trial.tmpfs_logs(job)
                (logs/'room-frames.tsv').write_text('rows');(logs/'room-frames.tsv.stalls.txt').write_text('stack')
                self.assertTrue((job/'stream.tsv').is_symlink());self.assertEqual((job/'room-frames.tsv').read_text(),'rows')
                self.assertEqual(trial.collect_logs(job),4)
                self.assertFalse((job/'room-frames.tsv').is_symlink());self.assertEqual((job/'room-frames.tsv.stalls.txt').read_text(),'stack')
                self.assertFalse(logs.exists());self.assertEqual(trial.collect_logs(job),0)

    def test_verified_baseline_restores_and_keeps_changed_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);old=root/'system/slot-dev/slotted-trials/slotted-ui-old';old.mkdir(parents=True)
            (old/'status.json').write_text(json.dumps(dict(state='complete')))
            baseline=old/'extra-channel-backup/ports.xml';baseline.parent.mkdir();baseline.write_bytes(b'original user metadata')
            sha=hashlib.sha256(baseline.read_bytes()).hexdigest()
            (old/'extra-channel-backup.json').write_text(json.dumps(dict(ports=dict(sha256=sha))))
            live=root/'roms/ports/gamelist.xml';live.parent.mkdir(parents=True);live.write_bytes(b'test play count')
            job=root/'new-job';job.mkdir()
            result=trial.recover_channels(job,'slotted-ui-old',root)
            self.assertEqual(live.read_bytes(),baseline.read_bytes())
            self.assertEqual((job/'before-channel-recovery/ports.xml').read_bytes(),b'test play count')
            self.assertEqual(result['roms/ports/gamelist.xml']['restored'],sha)
            self.assertEqual(trial.recover_channels(job,'slotted-ui-old',root),{})
            live.write_bytes(b'valuable later copy');baseline.write_bytes(b'corrupt baseline')
            with self.assertRaises(ValueError):trial.recover_channels(job,'slotted-ui-old',root)
            self.assertEqual(live.read_bytes(),b'valuable later copy')
            with self.assertRaises(ValueError):trial.recover_channels(job,'../escape',root)

if __name__=='__main__':unittest.main()
