"""Install a frozen, narrow cartridge manifest using the standard device audit. MIT.

Never deploys a frontend, console housing, layout, original GLB or launch hook.
The existing frontend and its complete SLOT_/SDL_ preview environment are kept.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import time
sys.path.insert(0, '/userdata/system/slot-dev')
import esdev
from session_data import Snapshot, digest

THEME = Path('/userdata/themes/art-book-slot')
SYSTEMS = ('nds', 'gba', 'nes', 'gb', 'gbc', 'md')
NAMES = ('media.mesh', 'media.texture', 'media.albedo.png', 'media-label.mesh',
         'media-label.texture', 'media-label.albedo.png', 'media-info.json', 'media-registration.json')
ALLOWED = {'_slot/consoles/'+key+'/'+name for key in SYSTEMS for name in NAMES} | {'_slot/MODEL_CREDITS.txt'}
STALE = {'_slot/consoles/gba/media.paint.mask'}


def run(job):
    config = json.loads((job/'request.json').read_text())
    expected, removals = config['files'], config.get('remove', {})
    if set(expected) != ALLOWED or not set(removals) <= STALE:
        raise ValueError('Not the exact six-cartridge runtime manifest')
    snapshot = Snapshot('/userdata', config['session'])
    report = {}; stopped = backed = installed = False; error = None
    environment = os.environ.copy()

    def status(state, message):
        p = job/'status.tmp'
        p.write_text(json.dumps(dict(state=state, message=message, report=report), indent=2)+'\n')
        p.replace(job/'status.json')

    def audit_owned():
        result = snapshot.audit(True)
        if result['data']['changed'] or result['data']['new']:
            raise RuntimeError('Unexpected user-data change')
        changes = set(result['runtime']['changed']+result['runtime']['new'])
        owned = {'themes/art-book-slot/'+name for name in set(expected) | set(removals)}
        if changes-owned:
            raise RuntimeError('Unexpected runtime change: '+repr(sorted(changes-owned)))
        for name, entry in expected.items():
            if digest(THEME/name) != entry['sha256']:
                raise RuntimeError('Installed checksum mismatch: '+name)
        return result

    lock = open('/userdata/system/slot-dev/editor-upload.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        status('busy', 'An editor upload is running; device left unchanged.')
        lock.close(); return
    try:
        # Validate the complete immutable payload before stopping the frontend.
        with tarfile.open(job/'payload.tar') as archive:
            members = archive.getmembers()
            if len(members) != len(expected) or {m.name for m in members} != set(expected):
                raise ValueError('Payload and manifest differ')
            for m in members:
                key = PurePosixPath(m.name); data = archive.extractfile(m).read() if m.isfile() else b''
                if not m.isfile() or key.is_absolute() or '..' in key.parts or not (THEME/m.name).resolve().is_relative_to(THEME.resolve()):
                    raise ValueError('Unsafe cartridge payload')
                if len(data) != expected[m.name]['bytes'] or hashlib.sha256(data).hexdigest() != expected[m.name]['sha256']:
                    raise ValueError('Payload checksum mismatch: '+m.name)
        pid = esdev.es_pid()
        if not pid or json.loads(esdev.api('/runningGame')) != {'msg':'NO GAME RUNNING'}:
            raise RuntimeError('A game may be running; device left unchanged')
        if esdev.get('ThemeSet') != 'art-book-slot':
            raise RuntimeError('Current theme is not art-book-slot')
        saved = {}
        for raw in Path('/proc/'+str(pid)+'/environ').read_bytes().split(b'\0'):
            name, sep, value = raw.partition(b'=')
            if sep and name.startswith((b'SLOT_', b'SDL_')):
                saved[name.decode()] = value.decode()
        environment.update(saved)
        report.update(preview_environment=saved, frontend_sha256=digest(Path('/usr/bin/emulationstation')))
        if report['frontend_sha256'] != config['frontendSha256']:
            raise RuntimeError('Frontend changed since validation')
        if json.loads(esdev.api('/runningGame')) != {'msg':'NO GAME RUNNING'}:
            raise RuntimeError('A game started; device left unchanged')
        status('running', 'Taking a fresh verified snapshot before cartridge installation.')
        stopped = True; esdev.stop()
        if esdev.es_pid():
            raise RuntimeError('Frontend did not stop')
        report['snapshot_counts'] = snapshot.backup(); backed = True
        report['snapshot'] = str(snapshot.directory)
        # Exact stale sidecar only: prove the recovery copy before unlinking it.
        for name, sha in removals.items():
            p = THEME/name; backup = snapshot.directory/'runtime/themes/art-book-slot'/name
            if not p.resolve().is_relative_to(THEME.resolve()) or digest(p) != sha or digest(backup) != sha:
                raise RuntimeError('Stale sidecar preservation mismatch: '+name)
        status('running', 'Installing only cartridge runtime files and credits.')
        installed = True
        with tarfile.open(job/'payload.tar') as archive:
            for m in archive.getmembers():
                target = THEME/m.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(m).read())
        for name in removals:
            (THEME/name).unlink()
        report['audit'] = audit_owned()
        report['restore_data'] = snapshot.restore()
        report['audit'] = audit_owned()
        report['installed'] = expected; report['removed_preserved_sidecars'] = removals
    except BaseException as ex:
        error = str(ex)
        if backed:
            try:
                report['rollback'] = snapshot.restore(runtime=installed)
                report['rollback_audit'] = snapshot.audit(runtime=installed)
            except BaseException as rollback:
                error += '; rollback: '+str(rollback)
    finally:
        if stopped:
            status('running', 'Reopening the same frontend preview.')
            try:
                subprocess.Popen(['setsid', esdev.INIT, 'start'], env=environment,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                esdev.wait(45)
                actual = Path('/proc/'+str(esdev.es_pid())+'/environ').read_bytes().split(b'\0')
                for name, value in report['preview_environment'].items():
                    if (name+'='+value).encode() not in actual:
                        raise RuntimeError('Preview environment mismatch: '+name)
                time.sleep(10)
                if json.loads(esdev.api('/runningGame')) != {'msg':'NO GAME RUNNING'}:
                    raise RuntimeError('Frontend preview did not stay ready')
                report['frontend_after_sha256'] = digest(Path('/usr/bin/emulationstation'))
                if report['frontend_after_sha256'] != report['frontend_sha256']:
                    raise RuntimeError('Frontend binary changed')
                if not error:
                    report['audit'] = audit_owned()
                report['frontend_ready'] = True
            except BaseException as ex:
                error = (error+'; ' if error else '')+'Restart verification: '+str(ex)
        (job/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        status('failed' if error else 'complete', error or 'Six selected cartridges installed; current preview and user data preserved.')
        lock.close()


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
