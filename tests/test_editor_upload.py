"""Upload boundaries and real snapshot rollback, without touching a device."""
import hashlib
import ast
import base64
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request
import zlib

from tools.dev import session_data, esdev
from tools.tabletop.editor import upload
from tools.frontend import persistence

spec = importlib.util.spec_from_file_location('editor_device_upload', Path(upload.HERE) / 'device_upload.py')
device = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'fcntl': Mock(LOCK_EX=2, LOCK_NB=4), 'session_data': session_data, 'esdev': esdev}):
    spec.loader.exec_module(device)


def archive_bytes(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class UploadSafetyTests(unittest.TestCase):
    def test_archive_rejects_traversal_symlinks_duplicates_missing_and_corruption(self):
        good = '_slot/tabletop/layouts/gba-pvm.scene'
        expected = {good: dict(bytes=3, sha256=upload.digest(b'abc'))}
        for entries in ([(good, b'bad')], [(good, b'abc'), (good, b'abc')], [],
                        [('../escape', b'abc')], [('/absolute', b'abc')], [('saves/x', b'abc')]):
            with self.subTest(entries=entries), tarfile.open(fileobj=io.BytesIO(archive_bytes(entries))) as archive:
                with self.assertRaises(ValueError):
                    device.checked_members(archive, expected)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            member = tarfile.TarInfo(good)
            member.type, member.linkname = tarfile.SYMTYPE, '/userdata/saves/x'
            archive.addfile(member)
        with tarfile.open(fileobj=io.BytesIO(buffer.getvalue())) as archive:
            with self.assertRaises(ValueError):
                device.checked_members(archive, expected)

    def test_runtime_audit_rejects_unowned_files_and_any_user_data_change(self):
        value = dict(data=dict(changed=[], new=[]), runtime=dict(changed=[], new=['themes/art-book-slot/_slot/layout.scene']))
        device.check_audit(value, {'_slot/layout.scene': {}})
        with self.assertRaises(RuntimeError):
            device.check_audit(value, {})
        value['data']['changed'] = ['saves/game.srm']
        with self.assertRaises(RuntimeError):
            device.check_audit(value, {'_slot/layout.scene': {}})

    def test_duplicate_request_does_not_save_or_start_second_worker(self):
        jobs = upload.Uploads()
        jobs.current['state'] = 'running'
        save = Mock()
        with self.assertRaises(ValueError):
            jobs.start({}, '', save)
        save.assert_not_called()

    def test_completed_status_survives_editor_restart(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(upload, 'BUILD', Path(folder)):
            path = Path(folder) / 'editor-uploads/editor-20261018/status.json'
            path.parent.mkdir(parents=True)
            value = dict(state='complete', message='Uploaded', session='editor-20261018', sourceSha256='saved-sha')
            path.write_text(json.dumps(value))
            jobs = upload.Uploads()
            jobs.restore_status()
            self.assertEqual(jobs.status(), value)

    def transaction(self, fail=False, running_game=False, bad_hash=False, fail_readiness=False, preview=True, theme_name='art-book-slot'):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            theme = root / 'themes' / theme_name
            theme.mkdir(parents=True)
            live = theme / '_slot/tabletop/layouts/gba-pvm.scene'
            live.parent.mkdir(parents=True)
            live.write_bytes(b'old scene')
            save = root / 'saves/game.srm'
            save.parent.mkdir()
            save.write_bytes(b'valuable save')
            settings = root / 'system/configs/emulationstation/es_settings.cfg'
            settings.parent.mkdir(parents=True)
            settings.write_bytes(b'normal preferences')
            official = root / 'emulationstation'
            official.write_bytes(b'previous frontend')
            mounts = root / 'mounts'
            mounts.write_text('')
            job = root / 'job'
            job.mkdir()
            (job / 'frontend').write_bytes(b'preview frontend')
            key, data = '_slot/tabletop/layouts/gba-pvm.scene', b'authored new scene'
            expected = {key: dict(bytes=len(data), sha256=upload.digest(data))}
            (job / 'payload.tar').write_bytes(archive_bytes([(key, data)]))
            (job / 'manifest.json').write_text(json.dumps(expected))
            config = dict(session='test-upload', theme=theme_name, system='gba', tv='pvm', files=expected,
                          frontendSha256='bad' if bad_hash else upload.digest(b'preview frontend'), sourceSha256='source-sha')
            config['preview'] = preview
            (job / 'request.json').write_text(json.dumps(config))
            running, environment = [True], [{}]
            def stop(): running[0] = False
            def start(env):
                environment[0] = env
                running[0] = True
            def apply(*args, **kwargs):
                live.write_bytes(data)
                if fail: raise subprocess.CalledProcessError(1, 'apply')
            def bind(path): official.write_bytes(path.read_bytes())
            def env(pid): return [(k+'='+v).encode() for k,v in environment[0].items()]
            api = json.dumps({'path': 'running game'} if running_game else {'msg': 'NO GAME RUNNING'})
            snapshot = session_data.Snapshot(root, 'test-upload')
            with patch.object(device, 'THEME', theme), patch.object(device, 'OFFICIAL', official), \
                    patch.object(persistence, 'BASE', root / 'persistent'), \
                    patch.object(persistence, 'HOOK', root / 'boot/postshare.sh'), \
                    patch.object(persistence, 'OFFICIAL', official), patch.object(persistence, 'MOUNTS', mounts), \
                    patch.object(device, 'Snapshot', return_value=snapshot), \
                    patch.object(device, 'open', create=True, return_value=Mock()), \
                    patch.object(device.esdev, 'es_pid', side_effect=lambda:'123' if running[0] else None), \
                    patch.object(device.esdev, 'api', return_value=api), patch.object(device.esdev, 'get', return_value=theme_name), \
                    patch.object(device.esdev, 'stop', side_effect=stop) as stopping, \
                    patch.object(device.esdev, 'wait', side_effect=[RuntimeError('not ready'), None] if fail_readiness else None), \
                    patch.object(device, 'start', side_effect=start), patch.object(device, 'process_environment', side_effect=env), \
                    patch.object(device, 'bind', side_effect=bind), patch.object(device.time, 'sleep'), \
                    patch.object(device.subprocess, 'run', side_effect=apply):
                device.run(job)
            status = json.loads((job / 'status.json').read_text())
            self.assertTrue(running[0])
            self.assertEqual(save.read_bytes(), b'valuable save')
            self.assertEqual(settings.read_bytes(), b'normal preferences')
            if running_game or bad_hash:
                self.assertEqual(status['state'], 'failed')
                stopping.assert_not_called()
                self.assertFalse(snapshot.directory.exists())
                self.assertEqual(live.read_bytes(), b'old scene')
            elif fail or fail_readiness:
                self.assertEqual(status['state'], 'failed')
                self.assertEqual(live.read_bytes(), b'old scene')
                self.assertEqual(official.read_bytes(), b'previous frontend')
                self.assertFalse(snapshot.audit(True)['runtime']['changed'])
                self.assertFalse((root / 'boot/postshare.sh').exists())
                self.assertFalse((root / 'persistent/active.json').exists())
            else:
                self.assertEqual(status['state'], 'complete', status)
                self.assertEqual(live.read_bytes(), data)
                self.assertEqual(official.read_bytes(), b'preview frontend')
                if preview:
                    self.assertEqual(environment[0]['SLOT_SCENE_PREVIEW_TV'], 'pvm')
                else:
                    self.assertNotIn('SLOT_SCENE_PREVIEW_SYSTEM', environment[0])
                    self.assertNotIn('SLOT_SCENE_PREVIEW_TV', environment[0])
                self.assertEqual(status['audit']['data']['changed'], [])
                self.assertEqual(status['persistence']['sha256'], config['frontendSha256'])
                self.assertTrue((root / 'boot/postshare.sh').is_file())
                self.assertEqual((root / 'persistent' / status['persistence']['binary']).read_bytes(), b'preview frontend')

    def test_upload_keeps_settings_saves_and_exact_scene(self): self.transaction()
    def test_binary_install_can_keep_normal_startup(self): self.transaction(preview=False)
    def test_partial_install_rolls_back_from_verified_snapshot(self): self.transaction(fail=True)
    def test_running_game_is_rejected_without_stopping(self): self.transaction(running_game=True)
    def test_frontend_hash_failure_never_stops_device(self): self.transaction(bad_hash=True)
    def test_startup_activation_is_rolled_back_if_preview_fails(self): self.transaction(fail_readiness=True)
    def test_slotted_upload_and_rollback_preserve_user_data(self):
        self.transaction(theme_name='Slotted')
        self.transaction(theme_name='Slotted', fail_readiness=True)


class FakeRemote:
    """The host worker's SSH boundary: answers the read-only preflight from `device`,
    records copies (keeping the tar) and reports `device_status` as the job's status."""
    target = 'device'

    def __init__(self, device, device_status=None, preflight_error=None, theme='art-book-slot'):
        self.device, self.device_status, self.preflight_error = device, device_status, preflight_error
        self.theme = theme
        self.copies, self.started, self.payload = [], False, None

    def python(self, source, timeout=90):
        compile(source, '<device>', 'exec')  # every generated device script is valid Python
        if 'ThemeSet' in source:
            self.preflight_source = source
            if self.preflight_error:
                raise subprocess.CalledProcessError(1, 'ssh', stderr=self.preflight_error.encode())
            encoded = source.split('base64.b64decode(')[1].split(')))')[0]
            keys = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(encoded))))
            self.checked_keys = keys
            return json.dumps(dict(theme=self.theme, files={key: self.device.get(key) for key in keys})).encode()
        if 'Popen' in source:
            self.started = True
            return b''
        return json.dumps(self.device_status).encode()

    def run(self, args, timeout=90):
        return b''

    def copy(self, source, target):
        self.copies.append(target.rsplit('/', 1)[-1])
        if target.endswith('/payload.tar'):
            self.payload = Path(source).read_bytes()


class BatchUploadTests(unittest.TestCase):
    """One transaction for several layouts (Phase 1 batch upload)."""

    def host(self, folder, remote, entries, open_target=('snes', 'panasonic')):
        """Run the host worker synchronously against a minimal project tree."""
        root, build = Path(folder) / 'project', Path(folder) / 'project/build/tabletop'
        slot = root / 'theme' / upload.THEME_NAME / '_slot'
        for name, data in (('assets/table/scene.json', b'table'), ('assets/table/top.mesh', b'top'),
                           ('assets/panasonic/scene.json', b'tv'), ('assets/panasonic/glass.texture', b'glass'),
                           ('assets/snes/power.control', b'power'), ('assets/snes-us/power.control', b'power-us')):
            (build / name).parent.mkdir(parents=True, exist_ok=True)
            (build / name).write_bytes(data)
        for name, data in (('consoles/snes/model.mesh', b'snes'), ('consoles/snes-us/model.mesh', b'snes-us'),
                           ('consoles/nes/model.mesh', b'nes'), ('MODEL_CREDITS.txt', b'credits')):
            (slot / name).parent.mkdir(parents=True, exist_ok=True)
            (slot / name).write_bytes(data)
        (build / 'editor-device').mkdir(parents=True)
        (build / 'editor-device/frontend.bin').write_bytes(b'frontend')
        (build / 'editor-device/frontend.json').write_text(json.dumps(dict(path='build/tabletop/editor-device/frontend.bin',
                                                                          sha256=upload.digest(b'frontend'))))
        (build / 'editor-device/frontend-Slotted.json').write_text(json.dumps(dict(path='build/tabletop/editor-device/frontend.bin',
            sha256=upload.digest(b'frontend'), themeRoot='active-theme-v1')))
        for name, source in upload.TOOLS:
            (root / source).parent.mkdir(parents=True, exist_ok=True)
            (root / source).write_text('# tool')
        jobs = upload.Uploads()
        with patch.object(upload, 'ROOT', root), patch.object(upload, 'BUILD', build), \
                patch.object(upload, 'Remote', return_value=remote), patch.object(upload.time, 'sleep'):
            result = jobs.start_batch(lambda: entries, open_target, background=False)
        return jobs, Path(result['evidence'])

    @staticmethod
    def entry(system, native):
        profile = dict(system=system, tv='panasonic', table=dict(model='table'))
        return dict(system=system, tv='panasonic', profile=profile, native=native, source=json.dumps(profile).encode())

    def test_combined_manifest_sends_each_shared_file_once(self):
        complete = dict(state='complete', message='Uploaded', progress={})
        with tempfile.TemporaryDirectory() as folder:
            remote = FakeRemote({}, complete)
            jobs, evidence = self.host(folder, remote, [self.entry('snes', 'SLOTLAYOUT1\nsnes\n'), self.entry('nes', 'SLOTLAYOUT1\nnes\n')])
            self.assertEqual(jobs.status()['state'], 'complete', jobs.status())
            request = json.loads((evidence / 'request.json').read_text())
            with tarfile.open(fileobj=io.BytesIO(remote.payload)) as archive:
                names = archive.getnames()
            # Table, TV and credits are shared by both layouts, yet appear once.
            self.assertEqual(len(names), len(set(names)))
            for shared in ('_slot/tabletop/table/scene.json', '_slot/tabletop/panasonic/glass.texture', '_slot/MODEL_CREDITS.txt'):
                self.assertEqual(names.count(shared), 1)
            self.assertIn('_slot/tabletop/layouts/snes-panasonic.scene', names)
            self.assertIn('_slot/tabletop/layouts/nes-panasonic.scene', names)
            self.assertIn('_slot/consoles/snes-us/model.mesh', names)
            self.assertEqual(set(names), set(request['files']))
            self.assertEqual(set(request['verify']), set(names))
            self.assertEqual(request['layouts'], ['snes-panasonic', 'nes-panasonic'])
            self.assertEqual((request['preview'], request['system'], request['tv'], request['theme']), (True, 'snes', 'panasonic', 'art-book-slot'))
            # One job: one payload, one device worker started.
            self.assertEqual(remote.copies.count('payload.tar'), 1)
            self.assertTrue(remote.started)
            self.assertEqual((evidence / 'layouts/nes-panasonic.scene').read_text(), 'SLOTLAYOUT1\nnes\n')
            progress = jobs.status()['progress']
            self.assertEqual(len(progress), len({item['name'] for item in progress}))

    def test_unchanged_files_are_verified_but_not_sent(self):
        same_layout = 'SLOTLAYOUT1\nsnes\n'
        device = {'_slot/tabletop/table/scene.json': upload.digest(b'table'), '_slot/tabletop/table/top.mesh': upload.digest(b'top'),
                  '_slot/tabletop/panasonic/glass.texture': upload.digest(b'stale glass'),
                  '_slot/tabletop/layouts/snes-panasonic.scene': upload.digest(same_layout.encode())}
        with tempfile.TemporaryDirectory() as folder:
            remote = FakeRemote(device, dict(state='complete', message='Uploaded', progress={}))
            jobs, evidence = self.host(folder, remote, [self.entry('snes', same_layout), self.entry('nes', 'SLOTLAYOUT1\nnes\n')], None)
            request = json.loads((evidence / 'request.json').read_text())
            with tarfile.open(fileobj=io.BytesIO(remote.payload)) as archive:
                names = set(archive.getnames())
            skipped = {'_slot/tabletop/table/scene.json', '_slot/tabletop/table/top.mesh', '_slot/tabletop/layouts/snes-panasonic.scene'}
            self.assertFalse(names & skipped)
            self.assertIn('_slot/tabletop/panasonic/glass.texture', names)  # differs on the device
            self.assertTrue(skipped <= set(request['verify']))  # still verified there afterwards
            self.assertEqual(names, set(request['files']))
            self.assertFalse(request['preview'])
            self.assertNotIn('system', request)
            states = {item['name']: item['state'] for item in jobs.status()['progress']}
            self.assertEqual({states[name] for name in skipped}, {'same'})
            self.assertEqual(states['_slot/tabletop/panasonic/glass.texture'], 'sent')
            self.assertEqual(upload.plan({'a': '1', 'b': '2'}, {'a': '1', 'b': '3'}), (['b'], ['a']))

    def test_full_home_preflight_fits_the_ssh_command_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            asset = Path(folder) / 'model.mesh'
            asset.write_bytes(b'full model')
            files = {'_slot/local-models/consoles/gba/realistic/colour-%03d/model.mesh' % i: asset for i in range(400)}
            remote = FakeRemote({}, dict(state='complete', message='Uploaded', progress={}))
            with patch.object(upload, 'combined_dependencies', return_value=files):
                jobs, evidence = self.host(folder, remote, [self.entry('snes', 'SLOTLAYOUT1\n')], None)
            self.assertEqual(jobs.status()['state'], 'complete', jobs.status())
            request = json.loads((evidence / 'request.json').read_text())
            self.assertGreater(len(json.dumps(list(request['verify']))), 24000)
            self.assertLess(len(remote.preflight_source), 6000)
            self.assertEqual(set(remote.checked_keys), set(request['verify']))

    def test_slotted_uses_shared_local_models_and_its_own_device_theme(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = FakeRemote({}, dict(state='complete', message='Uploaded', progress={}), theme='Slotted')
            jobs, evidence = self.host(folder, remote, [self.entry('snes', 'SLOTLAYOUT1\nsnes\n')], None)
            self.assertEqual(jobs.status()['state'], 'complete', jobs.status())
            request = json.loads((evidence / 'request.json').read_text())
            self.assertEqual(request['theme'], 'Slotted')
            self.assertIn('_slot/consoles/snes/model.mesh', request['files'])
            self.assertIn('slot_theme.py', remote.copies)
            device.check_request(dict(request, system=None, tv=None))
            report = dict(data=dict(changed=[], new=[]), runtime=dict(changed=['themes/Slotted/_slot/consoles/snes/model.mesh'], new=[]))
            device.check_audit(report, request['files'], 'Slotted')
            with self.assertRaises(RuntimeError):
                device.check_audit(report, request['files'], 'art-book-slot')

    def test_failed_preflight_writes_nothing_to_the_device(self):
        with tempfile.TemporaryDirectory() as folder:
            remote = FakeRemote({}, preflight_error='Close the running game and return to the frontend before uploading.')
            jobs, _ = self.host(folder, remote, [self.entry('snes', 'SLOTLAYOUT1\n'), self.entry('nes', 'SLOTLAYOUT1\n')])
            self.assertEqual(jobs.status()['state'], 'failed')
            self.assertIn('running game', jobs.status()['message'])
            self.assertEqual(remote.copies, [])
            self.assertFalse(remote.started)

    def test_concurrent_requests_run_one_upload_and_save_once(self):
        jobs, release, prepared, outcomes = upload.Uploads(), threading.Event(), [], []
        gate = threading.Barrier(2)
        def prepare():
            prepared.append(1)
            return [self.entry('snes', 'SLOTLAYOUT1\n')]
        def attempt():
            gate.wait()
            try:
                outcomes.append(jobs.start_batch(prepare, None)['state'])
            except ValueError as error:
                outcomes.append(str(error))
        with tempfile.TemporaryDirectory() as folder, patch.object(upload, 'BUILD', Path(folder)), \
                patch.object(upload.Uploads, 'worker', side_effect=lambda *args: release.wait(5)):
            threads = [threading.Thread(target=attempt) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
            release.set()
        self.assertEqual(sorted(outcomes), ['An upload is already running; wait for it to finish.', 'running'])
        self.assertEqual(len(prepared), 1)
        with self.assertRaises(ValueError):
            jobs.start_batch(prepare, None, fail_at='anywhere')

    def test_device_lock_refuses_a_second_transaction_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder)
            (job / 'request.json').write_text(json.dumps(dict(session='second', system='gba', tv='pvm', files={})))
            flock = Mock(side_effect=BlockingIOError)
            with patch.object(device, 'open', create=True, return_value=Mock()), patch.object(device.fcntl, 'flock', flock), \
                    patch.object(device.esdev, 'stop') as stopping, patch.object(device, 'Snapshot') as snapshot:
                device.run(job)
            status = json.loads((job / 'status.json').read_text())
            self.assertEqual(status['state'], 'failed')
            self.assertIn('Another device upload', status['message'])
            stopping.assert_not_called()
            snapshot.return_value.backup.assert_not_called()

    def test_request_checks_refuse_other_themes_names_and_paths(self):
        good = dict(system='gba', tv='pvm', files={'_slot/a': dict(sha256='1', bytes=1)}, verify={'_slot/a': '1', '_slot/b': '2'})
        self.assertEqual(device.check_request(good), good['verify'])
        for change in (dict(theme='slotted'), dict(layouts=['gba-pvm', 'dc-pvm']), dict(verify={'_slot/a': '1', '../x': '2'}),
                       dict(verify={'_slot/b': '2'}), dict(failAt='later'), dict(system='dreamcast')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                device.check_request(dict(good, **change))
        self.assertEqual(device.check_request(dict(good, preview=False, system=None, tv=None)), good['verify'])

    def batch(self, failure=None):
        """Device transaction for two layouts sharing their TV. failure: None, 'partial'
        (the install stops after writing one file), 'corrupt' (one file installs wrongly)
        or a forced failure point."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            theme = root / 'themes/art-book-slot'
            old = {'_slot/tabletop/layouts/gba-pvm.scene': b'old gba', '_slot/tabletop/pvm/glass.texture': b'old glass',
                   '_slot/tabletop/pvm/scene.json': b'same pvm'}
            new = {'_slot/tabletop/layouts/gba-pvm.scene': b'new gba', '_slot/tabletop/layouts/gb-pvm.scene': b'brand new gb',
                   '_slot/tabletop/pvm/glass.texture': b'new glass', '_slot/consoles/gb/model.mesh': b'gb model'}
            for name, data in old.items():
                (theme / name).parent.mkdir(parents=True, exist_ok=True)
                (theme / name).write_bytes(data)
            (root / 'saves').mkdir()
            (root / 'saves/game.srm').write_bytes(b'valuable save')
            official = root / 'emulationstation'
            official.write_bytes(b'previous frontend')
            (root / 'mounts').write_text('')
            job = root / 'job'
            job.mkdir()
            (job / 'frontend').write_bytes(b'preview frontend')
            expected = {name: dict(bytes=len(data), sha256=upload.digest(data)) for name, data in new.items()}
            verify = {name: entry['sha256'] for name, entry in expected.items()}
            verify['_slot/tabletop/pvm/scene.json'] = upload.digest(b'same pvm')
            (job / 'payload.tar').write_bytes(archive_bytes(list(new.items())))
            (job / 'manifest.json').write_text(json.dumps(expected))
            config = dict(session='batch-test', theme='art-book-slot', layouts=['gba-pvm', 'gb-pvm'], preview=False,
                          files=expected, verify=verify, frontendSha256=upload.digest(b'preview frontend'))
            if failure in device.FAIL_POINTS:
                config['failAt'] = failure
            (job / 'request.json').write_text(json.dumps(config))
            running, starts, written = [True], [], []
            def stop(): running[0] = False
            def start(env):
                starts.append(env)
                running[0] = True
            def apply(*args, **kwargs):
                for name, data in new.items():
                    (theme / name).parent.mkdir(parents=True, exist_ok=True)
                    (theme / name).write_bytes(b'corrupted' if failure == 'corrupt' and name.endswith('.texture') else data)
                    written.append(name)
                    if failure == 'partial':
                        raise subprocess.CalledProcessError(1, 'apply_increment.py')
            snapshot = session_data.Snapshot(root, 'batch-test')
            with patch.object(device, 'THEME', theme), patch.object(device, 'OFFICIAL', official), \
                    patch.object(persistence, 'BASE', root / 'persistent'), \
                    patch.object(persistence, 'HOOK', root / 'boot/postshare.sh'), \
                    patch.object(persistence, 'OFFICIAL', official), patch.object(persistence, 'MOUNTS', root / 'mounts'), \
                    patch.object(device, 'Snapshot', return_value=snapshot), \
                    patch.object(device, 'open', create=True, return_value=Mock()), \
                    patch.object(device.esdev, 'es_pid', side_effect=lambda: '123' if running[0] else None), \
                    patch.object(device.esdev, 'api', return_value=json.dumps({'msg': 'NO GAME RUNNING'})), \
                    patch.object(device.esdev, 'get', return_value='art-book-slot'), \
                    patch.object(device.esdev, 'stop', side_effect=stop), patch.object(device.esdev, 'wait'), \
                    patch.object(device, 'start', side_effect=start), patch.object(device, 'process_environment', return_value=[]), \
                    patch.object(device, 'bind', side_effect=lambda path: official.write_bytes(path.read_bytes())), \
                    patch.object(device.time, 'sleep'), patch.object(device.subprocess, 'run', side_effect=apply):
                device.run(job)
            status = json.loads((job / 'status.json').read_text())
            self.assertTrue(running[0])
            self.assertEqual((root / 'saves/game.srm').read_bytes(), b'valuable save')
            live = {name: (theme / name).read_bytes() for name in set(old) | set(new) if (theme / name).is_file()}
            return status, live, old, new, written, official.read_bytes(), starts, root

    def test_batch_installs_and_verifies_every_file_once(self):
        status, live, old, new, written, frontend, starts, root = self.batch()
        self.assertEqual(status['state'], 'complete', status)
        self.assertEqual(written, list(new))  # one apply for both layouts
        self.assertEqual(live, {**old, **new})
        self.assertEqual(set(status['progress'].values()), {'verified'})
        self.assertEqual(len(status['progress']), 5)  # four sent + one already identical
        self.assertEqual(len(starts), 1)  # one frontend restart
        self.assertEqual(frontend, b'preview frontend')
        self.assertIn('2 layouts', status['message'])
        self.assertEqual(status['audit']['data']['changed'], [])

    def assert_rolled_back(self, failure, restarts):
        status, live, old, new, written, frontend, starts, root = self.batch(failure)
        self.assertEqual(status['state'], 'failed', status)
        self.assertEqual(live, old)  # every layout and model file back together; new files gone
        self.assertEqual(frontend, b'previous frontend')
        self.assertEqual(len(starts), restarts)
        self.assertFalse((root / 'boot/postshare.sh').exists())
        self.assertFalse((root / 'persistent/active.json').exists())
        rollback = status['recovery']['files']
        self.assertEqual(set(rollback), set(new))
        self.assertEqual(rollback['_slot/tabletop/layouts/gba-pvm.scene'], 'restored')
        self.assertEqual(rollback['_slot/tabletop/layouts/gb-pvm.scene'], 'removed')
        self.assertFalse(any(group['changed'] or group['new'] for group in status['recovery']['audit'].values()))
        self.assertIn('Rolled back all 4 changed files together; audit clean', status['message'])
        return status

    def test_partial_install_rolls_back_every_layout_together(self):
        status = self.assert_rolled_back('partial', 1)
        self.assertNotEqual(status['progress']['_slot/tabletop/layouts/gb-pvm.scene'], 'verified')

    def test_one_bad_file_rolls_back_the_files_that_verified(self):
        status = self.assert_rolled_back('corrupt', 1)
        self.assertIn('Verification failed: _slot/tabletop/pvm/glass.texture', status['message'])

    def test_forced_failure_after_install_rolls_back_everything(self):
        self.assert_rolled_back('installed', 1)

    def test_forced_failure_after_restart_rolls_back_everything(self):
        self.assert_rolled_back('started', 2)


class BatchEndpointTests(unittest.TestCase):
    """The editor server's batch dialog, import and export-and-upload endpoints."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location('scene_editor_batch', Path(upload.HERE) / 'server.py')
        self.editor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.editor)
        self.folder = tempfile.TemporaryDirectory()
        self.editor.ROOT, self.editor.ASSETS = Path(self.folder.name), Path(self.folder.name) / 'assets'
        self.editor.ASSETS.mkdir()

    def tearDown(self):
        self.folder.cleanup()

    def profile(self, system='snes', tv='panasonic', fov=40):
        return dict(version=1, system=system, tv=tv, viewport=dict(width=720, height=480),
                    camera=dict(position=[178.5, 547.4, 1358.3], target=[178.5, -26.4, 69.6], fov=fov),
                    objects={name: dict(position=[0, 0, 0], rotation=[0, 0, 0]) for name in self.editor.NAMES})

    def test_plan_rows_hash_what_upload_installs_and_refuse_a_stale_list(self):
        editor = self.editor
        editor.save_profile(self.profile())
        editor.save_profile(self.profile('gba', 'pvm'))
        native = editor.native_text(self.profile())
        device = dict(layouts={'snes-panasonic': dict(sha256=upload.digest(native.encode()), text=None)}, themeSet='art-book-slot')
        with patch.object(editor, 'device_layouts', return_value=device):
            plan = editor.upload_plan()
        rows = {row['key']: row for row in plan['layouts']}
        self.assertEqual(set(rows), {'snes-panasonic', 'gba-pvm'})
        self.assertEqual(rows['snes-panasonic']['sha256'], plan['device']['layouts']['snes-panasonic']['sha256'])
        self.assertNotIn('gba-pvm', plan['device']['layouts'])
        expect = {key: row['sha256'] for key, row in rows.items()}
        entries = editor.batch_entries(['gba-pvm', 'snes-panasonic'], expect)
        self.assertEqual([entry['native'] for entry in entries][1], native)
        editor.save_profile(self.profile(fov=41))  # saved again after the dialog read it
        with self.assertRaises(ValueError):
            editor.batch_entries(['snes-panasonic'], expect)
        for key in ('dreamcast-pvm', 'snes', 'snes-tv', '../x'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                editor.layout_pair(key)
        with patch.object(editor, 'device_layouts', side_effect=subprocess.CalledProcessError(255, 'ssh', stderr=b'No route')):
            self.assertIn('No route', editor.upload_plan()['device']['error'])

    def test_device_read_is_one_read_only_script(self):
        layouts = Path(self.folder.name) / 'device-layouts'
        layouts.mkdir()
        (layouts / 'gba-pvm.scene').write_bytes(b'SLOTLAYOUT1\n')
        calls = []
        class Remote:
            def python(self, source, timeout=90):
                calls.append(source)
                return subprocess.run([sys.executable, '-I', '-c', source], check=True, capture_output=True).stdout
        with patch.object(self.editor, 'DEVICE_LAYOUTS', str(layouts)), patch('tools.tabletop.device_probe.Remote', Remote):
            state = self.editor.device_layouts(texts=True)
            hashes = self.editor.device_layouts()
        self.assertEqual(len(calls), 2)  # one SSH call per read
        self.assertEqual(state['layouts'], {'gba-pvm': dict(sha256=upload.digest(b'SLOTLAYOUT1\n'), text='SLOTLAYOUT1\n')})
        self.assertIsNone(hashes['layouts']['gba-pvm']['text'])
        self.assertIn('statusError', state)  # no esdev on the host: reported, never fatal
        self.assertNotRegex(calls[0], r'write|unlink|mkdir|rename|replace\(|esdev\.(stop|set|start)')

    def test_import_lists_only_device_layouts_that_differ(self):
        editor = self.editor
        editor.save_profile(self.profile())
        editor.save_profile(self.profile('gb', 'pvm'))
        texts = {'snes-panasonic': editor.native_text(self.profile()), 'gb-pvm': editor.native_text(self.profile('gb', 'pvm', fov=50)),
                 'nes-oldtv': editor.native_text(self.profile('nes', 'oldtv')), 'home-pvm': 'SLOTHOME1\n', 'psx-pvm': 'broken'}
        device = dict(layouts={key: dict(sha256=upload.digest(text.encode()), text=text) for key, text in texts.items()}, themeSet='art-book-slot')
        with patch.object(self.editor, 'device_layouts', return_value=device):
            rows = {row['key']: row for row in editor.device_import()['layouts']}
        self.assertEqual({key: row['status'] for key, row in rows.items()},
                         {'snes-panasonic': 'same', 'gb-pvm': 'differs', 'nes-oldtv': 'not saved', 'home-pvm': 'unsupported', 'psx-pvm': 'unreadable'})
        self.assertIsNone(rows['snes-panasonic']['profile'])
        self.assertEqual(rows['gb-pvm']['profile']['camera']['fov'], 50)
        self.assertEqual(editor.native_text(rows['nes-oldtv']['profile']), texts['nes-oldtv'])

    def test_export_and_upload_while_busy_saves_nothing(self):
        editor = self.editor
        server = editor.ThreadingHTTPServer(('127.0.0.1', 0), editor.Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        url = 'http://127.0.0.1:' + str(server.server_port)
        def post(path, value):
            request = urllib.request.Request(url + path, data=json.dumps(value).encode(),
                                             headers={'Content-Type': 'application/json', 'Origin': url, 'X-Scene-Token': editor.TOKEN})
            return json.load(urllib.request.urlopen(request))
        try:
            with patch.object(editor.UPLOADS, 'current', dict(state='running', message='busy')):
                for path, body in (('/api/export', dict(group='tv', profile=self.profile(), upload=True, open='snes-panasonic')),
                                   ('/api/upload-batch', dict(layouts=['snes-panasonic'], open='normal', expect={}))):
                    with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as failure:
                        post(path, body)
                    self.assertEqual(failure.exception.code, 400)
                    self.assertIn('already running', json.load(failure.exception)['error'])
            self.assertFalse((editor.ROOT / 'scene-layouts').exists())
            with self.assertRaises(urllib.error.HTTPError) as failure:
                post('/api/upload-batch', dict(layouts=['snes-panasonic'], open='dreamcast-pvm', expect={}))
            self.assertEqual(failure.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == '__main__':
    unittest.main()
