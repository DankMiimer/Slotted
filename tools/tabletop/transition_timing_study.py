"""Private paced switch-timing study against installed assets; never binds a frontend.

Runs each requested timing binary (n19 baseline and candidates) inside one fresh
snapshot/audit transaction, with the frontend stopped, then restarts it.
"""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, '/userdata/system/slot-dev')
import esdev
from session_data import Snapshot, digest


def run(job):
    config = json.loads((job/'request.json').read_text())
    snap = Snapshot('/userdata', config['session'])
    report = {}
    stopped = backed = False
    environment = os.environ.copy()
    error = None

    def status(state, message):
        p = job/'status.tmp'
        p.write_text(json.dumps(dict(state=state, message=message), indent=2))
        p.replace(job/'status.json')

    with Path('/userdata/system/slot-dev/editor-upload.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for name, sha in config['files'].items():
                if Path(name).name != name or digest(job/name) != sha:
                    raise ValueError('Private payload mismatch: '+name)
            if json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                raise RuntimeError('A game is running; device left unchanged')
            pid = esdev.es_pid()
            if not pid:
                raise RuntimeError('Frontend is not ready')
            for raw in Path('/proc/'+pid+'/environ').read_bytes().split(b'\0'):
                key, sep, value = raw.partition(b'=')
                if sep and key.startswith((b'SLOT_', b'SDL_')):
                    environment[key.decode()] = value.decode()
            report['frontend_before'] = digest(Path('/usr/bin/emulationstation'))
            report['environment'] = {k: v for k, v in environment.items() if k.startswith(('SLOT_', 'SDL_'))}
            status('running', 'Taking a fresh snapshot for the switch-timing study')
            stopped = True
            esdev.stop()
            if esdev.es_pid():
                raise RuntimeError('Frontend did not stop')
            report['snapshot_counts'] = snap.backup()
            backed = True
            root = Path('/userdata/themes/art-book-slot/_slot')
            report['layouts_before'] = {p.name: digest(p) for p in (root/'tabletop/layouts').glob('*.scene')}
            systems = sorted({step.split(':')[0] for run in config['runs'] for step in run['steps']} | {'snes'})
            for system in systems:
                folder = job/'faces'/system
                folder.mkdir(parents=True)
                found = sorted((Path('/userdata/roms')/system/'media/slotcarts').glob('*.png'))
                if system == 'psx':
                    faces = [p for p in found if p.name.endswith('.disc.png')][:12]
                else:
                    faces = [p for p in found if not p.name.endswith(('.back.png', '.disc.png', '.tzakol.png'))][:12]
                for i, path in enumerate(faces):
                    (folder/(str(i)+'.png')).symlink_to(path)
            report['runs'] = []
            for item in config['runs']:
                binary = job/item['binary']
                binary.chmod(0o755)
                output = job/item['name']
                output.mkdir()
                status('running', 'Timing '+item['name'])
                env = dict(os.environ, SDL_NOMOUSE='1', SLOT_SCENE_STREAMLOG=str(output/'stream.tsv'), **item.get('env', {}))
                command = [str(binary), str(root), str(root/'tabletop'), str(output), str(job/'faces')]+item['steps']
                result = subprocess.run(command, cwd=job, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=600)
                (output/'probe.log').write_bytes(result.stdout)
                report['runs'].append(dict(name=item['name'], binary=item['binary'], exit=result.returncode))
                if result.returncode:
                    raise RuntimeError('Timing run failed: '+item['name'])
        except BaseException as ex:
            error = str(ex)
        finally:
            if backed:
                try:
                    report['audit'] = snap.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):
                        report['restore'] = snap.restore(True)
                        report['audit'] = snap.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):
                        raise RuntimeError('Snapshot audit did not return clean')
                except BaseException as ex:
                    error = (error+'; ' if error else '')+'Audit: '+str(ex)
            if stopped:
                try:
                    if not esdev.es_pid():
                        subprocess.Popen(['setsid', esdev.INIT, 'start'], env=environment,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
                    esdev.wait(45)
                    report['frontend_after'] = digest(Path('/usr/bin/emulationstation'))
                    report['pid_after'] = esdev.es_pid()
                    report['runningGame'] = json.loads(esdev.api('/runningGame'))
                    report['layouts_after'] = {p.name: digest(p) for p in (Path('/userdata/themes/art-book-slot/_slot/tabletop/layouts')).glob('*.scene')}
                    if report['frontend_after'] != report['frontend_before'] or report['layouts_before'] != report['layouts_after']:
                        raise RuntimeError('Installed frontend/layout changed')
                except BaseException as ex:
                    error = (error+'; ' if error else '')+'Restart: '+str(ex)
            (job/'report.json').write_text(json.dumps(report, indent=2)+'\n')
            status('failed' if error else 'complete', error or 'Timing runs complete; installed frontend/data preserved')


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
