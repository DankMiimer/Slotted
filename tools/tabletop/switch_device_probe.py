"""Private device loading/flight measurement; fresh snapshot, no installation."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, '/userdata/system/slot-dev')
import esdev
from session_data import Snapshot, digest

SYSTEMS = ('snes', 'nes', 'n64', 'md', 'psx', 'gb', 'gbc', 'gba', 'nds', 'psp', 'pico8')
THEME = Path('/userdata/themes/art-book-slot/_slot')


def run(job):
    config = json.loads((job / 'request.json').read_text())
    snapshot = Snapshot('/userdata', config['session'])
    report = {}
    stopped = backed = False
    error = None
    environment = os.environ.copy()

    def status(state, message):
        temp = job / 'status.tmp'
        temp.write_text(json.dumps(dict(state=state, message=message), indent=2))
        temp.replace(job / 'status.json')

    with (Path('/userdata/system/slot-dev/editor-upload.lock')).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for name, expected in config['files'].items():
                path = job / name
                if Path(name).name != name or digest(path) != expected:
                    raise ValueError('Private payload mismatch: ' + name)
            if json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                raise RuntimeError('A game is running; device left unchanged')
            pid = esdev.es_pid()
            if not pid:
                raise RuntimeError('Frontend is not ready')
            for raw in Path('/proc/' + pid + '/environ').read_bytes().split(b'\0'):
                name, sep, value = raw.partition(b'=')
                if sep and name.startswith((b'SLOT_', b'SDL_')):
                    environment[name.decode()] = value.decode()
            report['frontend_before'] = digest(Path('/usr/bin/emulationstation'))
            report['environment'] = {k: v for k, v in environment.items() if k.startswith(('SLOT_', 'SDL_'))}
            report['layouts_before'] = {p.name: digest(p) for p in (THEME / 'tabletop/layouts').glob('*.scene')}
            status('running', 'Taking a fresh snapshot before private loading tests')
            stopped = True
            esdev.stop()
            if esdev.es_pid():
                raise RuntimeError('Frontend did not stop')
            report['snapshot_counts'] = snapshot.backup()
            report['snapshot'] = str(snapshot.directory)
            backed = True
            requests = []
            for system in SYSTEMS:
                directory = 'megadrive' if system == 'md' else system
                folder = Path('/userdata/roms') / directory / 'media/slotcarts'
                faces = sorted(folder.glob('*.disc.png'))[:12] if system == 'psx' else [p for p in sorted(folder.glob('*.png')) if not p.name.endswith(('.back.png', '.tzakol.png', '.disc.png'))][:12]
                # Probe TSV uses numbered private symlinks so paths with spaces
                # never become tokens or change production art.
                dest = job / 'faces' / system
                dest.mkdir(parents=True)
                paths = []
                for index, face in enumerate(faces):
                    link = dest / (str(index) + '.png')
                    link.symlink_to(face)
                    paths.append(str(link))
                requests.append(' '.join([system, 'pvm' if system in ('gb', 'gbc', 'gba', 'nds', 'psp') else 'panasonic'] + paths))
            (job / 'requests.tsv').write_text('\n'.join(requests) + '\n')
            binary = job / 'switch-probe-arm64'
            binary.chmod(0o755)
            report['probeSha256'] = digest(binary)
            # Installed scene files are read in place. No synthesized/default
            # scene can replace the author's latest device layouts.
            for aspect in (() if config.get('streamOnly') else ('3:2', '4:3')):
                status('running', 'Measuring all eleven installed systems at ' + aspect)
                out = job / aspect.replace(':', '')
                out.mkdir()
                cmd = [str(binary), str(THEME), str(THEME / 'tabletop'), str(job / 'requests.tsv'), str(out), '2', aspect, 'capture']
                result = subprocess.run(cmd, cwd=job, env=dict(os.environ, SDL_NOMOUSE='1'),
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
                (out / 'probe.log').write_bytes(result.stdout)
                report[aspect] = dict(exit=result.returncode, rows=len((out / 'loads.tsv').read_text().splitlines())-1 if (out / 'loads.tsv').is_file() else 0)
                if result.returncode:
                    raise RuntimeError('Private probe failed at ' + aspect + '; inspect probe.log')
            status('running', 'Testing CPU decode and staged GPU uploads while the scene keeps drawing')
            out = job / 'streaming'
            out.mkdir()
            result = subprocess.run([str(binary), str(THEME), str(THEME / 'tabletop'), str(job / 'requests.tsv'), str(out), '1', '3:2'],
                cwd=job, env=dict(os.environ, SDL_NOMOUSE='1', SLOT_RESEARCH_STREAM='1'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
            (out / 'probe.log').write_bytes(result.stdout)
            report['streaming'] = dict(exit=result.returncode)
            if result.returncode:
                raise RuntimeError('Private streaming study failed; inspect probe.log')
        except BaseException as ex:
            error = str(ex)
        finally:
            if backed:
                try:
                    report['audit_before_restore'] = snapshot.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit_before_restore'].values()):
                        report['restore'] = snapshot.restore(True)
                    report['audit'] = snapshot.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):
                        raise RuntimeError('Snapshot audit did not return clean')
                except BaseException as ex:
                    error = (error + '; ' if error else '') + 'Audit: ' + str(ex)
            if stopped:
                try:
                    status('running', 'Reopening the retained frontend')
                    if not esdev.es_pid():
                        subprocess.Popen(['setsid', esdev.INIT, 'start'], env=environment,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
                    esdev.wait(45)
                    report['frontend_after'] = digest(Path('/usr/bin/emulationstation'))
                    report['layouts_after'] = {p.name: digest(p) for p in (THEME / 'tabletop/layouts').glob('*.scene')}
                    report['runningGame'] = json.loads(esdev.api('/runningGame'))
                    report['pid_after'] = esdev.es_pid()
                    if report['frontend_before'] != report['frontend_after'] or report['layouts_before'] != report['layouts_after']:
                        raise RuntimeError('Installed frontend/layout changed')
                except BaseException as ex:
                    error = (error + '; ' if error else '') + 'Restart: ' + str(ex)
            (job / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            status('failed' if error else 'complete', error or 'Private tests finished; installed frontend and user data preserved')


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
