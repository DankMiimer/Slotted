"""Temporary frontend trial, fresh audited session and unconditional prior-binary recovery."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0, '/userdata/system/slot-dev')
import esdev
from session_data import Snapshot, digest

OFFICIAL = Path('/usr/bin/emulationstation')


def bind(path):
    if ' /usr/bin/emulationstation ' in Path('/proc/mounts').read_text():
        subprocess.run(['umount', str(OFFICIAL)], check=True)
    path.chmod(0o755)
    subprocess.run(['mount', '--bind', str(path), str(OFFICIAL)], check=True)


def start(environment):
    subprocess.Popen(['setsid', esdev.INIT, 'start'], env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True)


def run(job):
    request = json.loads((job/'request.json').read_text())
    snap = Snapshot('/userdata', request['session'])
    report = {}
    stopped = backed = rebound = False
    prior = os.environ.copy()
    error = None

    def status(state, message):
        p = job/'status.tmp'
        p.write_text(json.dumps(dict(state=state, message=message, **report), indent=2)+'\n')
        p.replace(job/'status.json')

    with Path('/userdata/system/slot-dev/editor-upload.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for name, sha in request['files'].items():
                if Path(name).name != name or digest(job/name) != sha:
                    raise ValueError('Trial payload mismatch: '+name)
            if json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                raise RuntimeError('A game is running; trial not started')
            pid = esdev.es_pid()
            if not pid:
                raise RuntimeError('Frontend is not ready')
            for raw in Path('/proc/'+pid+'/environ').read_bytes().split(b'\0'):
                key, sep, value = raw.partition(b'=')
                if sep and key.startswith((b'SLOT_', b'SDL_')):
                    prior[key.decode()] = value.decode()
            report['prior_environment'] = {k:v for k,v in prior.items() if k.startswith(('SLOT_', 'SDL_'))}
            report['prior_sha256'] = digest(OFFICIAL)
            shutil.copy2(OFFICIAL, job/'previous-frontend')
            if digest(job/'previous-frontend') != report['prior_sha256']:
                raise RuntimeError('Prior binary recovery copy mismatch')
            report['candidate_sha256'] = digest(job/'frontend')
            status('running', 'Taking a fresh snapshot for a temporary frontend trial')
            stopped = True
            esdev.stop()
            if esdev.es_pid():
                raise RuntimeError('Frontend did not stop')
            report['snapshot_counts'] = snap.backup()
            report['snapshot'] = str(snap.directory)
            backed = True
            bind(job/'frontend')
            rebound = True
            env = prior.copy()
            env.update(SLOT_SCENE_PREVIEW_SYSTEM='nes', SLOT_SCENE_PREVIEW_TV='panasonic',
                SLOT_SCENE_FRAMELOG=str(job/'frames.log'), SLOT_SCENE_STREAMLOG=str(job/'stream.tsv'), SDL_NOMOUSE='1')
            start(env)
            esdev.wait(45)
            time.sleep(6)
            if digest(OFFICIAL) != report['candidate_sha256']:
                raise RuntimeError('Trial frontend hash mismatch')
            report['trial_pid'] = esdev.es_pid()
            status('ready', 'Candidate is running temporarily; waiting for bounded UI validation')
            deadline = time.monotonic()+540
            while not (job/'finish.json').is_file():
                if time.monotonic()>deadline:
                    raise RuntimeError('UI trial timed out; recovering prior frontend')
                if not esdev.es_pid():
                    raise RuntimeError('Candidate frontend exited unexpectedly')
                time.sleep(.5)
            report['validation'] = json.loads((job/'finish.json').read_text())
            # Never restore a snapshot or stop a live emulator. A normal launch
            # test must first return through the frontend's ordinary exit path.
            while json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                status('waiting-game', 'Waiting for the game to return before preservation audit')
                time.sleep(1)
            if not report['validation'].get('passed'):
                error = 'UI validation did not pass; candidate not installed'
        except BaseException as ex:
            error = str(ex)
        finally:
            safe_to_stop = True
            if rebound and esdev.es_pid():
                try:
                    safe_to_stop = json.loads(esdev.api('/runningGame')) == {'msg': 'NO GAME RUNNING'}
                except Exception:
                    safe_to_stop = False
            if not safe_to_stop:
                report['recovery_deferred'] = 'A game may be running or its state cannot be verified. Trial binary/snapshot retained; no stop or restore performed.'
                (job/'report.json').write_text(json.dumps(report, indent=2)+'\n')
                status('failed', (error+'; ' if error else '')+report['recovery_deferred'])
                return
            try:
                if stopped:
                    esdev.stop()
                    if esdev.es_pid():
                        raise RuntimeError('Cannot recover while frontend is running')
                if backed:
                    report['before_restore'] = snap.audit(True)
                    if report['before_restore']['runtime']['changed'] or report['before_restore']['runtime']['new']:
                        raise RuntimeError('Unexpected theme/runtime mutation; retained for review')
                    report['restore'] = snap.restore()
                    report['audit'] = snap.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):
                        raise RuntimeError('Trial preservation audit is not clean')
                if rebound:
                    original = job/'previous-frontend'
                    active = Path('/userdata/system/slot-dev/frontend/active.json')
                    if active.is_file():
                        selected = json.loads(active.read_text())
                        candidate = active.parent/selected.get('binary', '')
                        if candidate.is_file() and digest(candidate) == report['prior_sha256']:
                            original = candidate
                    bind(original)
                    if digest(OFFICIAL) != report['prior_sha256']:
                        raise RuntimeError('Prior frontend recovery hash mismatch')
            except BaseException as ex:
                error = (error+'; ' if error else '')+'Recovery: '+str(ex)
            if stopped:
                try:
                    start(prior)
                    esdev.wait(45)
                    report['final_pid'] = esdev.es_pid()
                    report['final_sha256'] = digest(OFFICIAL)
                except BaseException as ex:
                    error = (error+'; ' if error else '')+'Restart: '+str(ex)
            (job/'report.json').write_text(json.dumps(report, indent=2)+'\n')
            status('failed' if error else 'complete', error or 'UI trial complete; prior frontend and user data restored')


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
