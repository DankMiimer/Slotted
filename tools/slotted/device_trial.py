"""Temporary standalone Slotted GUI trial. Restores the prior theme, binary and data."""
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import esdev
import device_install
from session_data import Snapshot, digest
from transition_frontend_trial import bind, start, OFFICIAL
import frontend_persistence

MODEL_SYSTEMS=frozenset(('snes','n64','nes','md','megadrive','genesis','psx','gb','gbc','gba','nds','psp','pico8'))

def validate_options(request):
    if request.get('motion') not in (None,'full','reduced') or request.get('tv') not in (None,'panasonic','pvm','oldtv','retro'):
        raise ValueError('Unsupported temporary theme preference')
    if 'allModels' in request and type(request['allModels']) is not bool:
        raise ValueError('Invalid model-visibility test option')
    if 'indexBatch' in request and (type(request['indexBatch']) is not int or request['indexBatch'] not in (0,3072,12288)):
        raise ValueError('Invalid index-batch test option')
    if 'screensaverMs' in request and (type(request['screensaverMs']) is not int or not 5000<=request['screensaverMs']<=120000):
        raise ValueError('Invalid temporary screensaver delay')
    if request.get('style') not in (None,'realistic','cel') or request.get('color') not in (None,'original','black','white','red','blue','purple','green','yellow'):
        raise ValueError('Unsupported temporary model appearance')

def show_modelled_systems(hidden):
    return ';'.join(name for name in (hidden or '').split(';') if name and name not in MODEL_SYSTEMS)

def rebind(path,attempts=4):
    """bind() for recovery. A candidate that exits mid-trial is restarted by Knulli's
    emulationstation-standalone wrapper, which kept the binary busy (trial ar: umount exit 32
    after a clean data/theme restore). Stop the frontend again and retry before giving up."""
    for attempt in range(attempts):
        esdev.stop()
        for _ in range(20):
            if not esdev.es_pid():break
            time.sleep(.5)
        try:
            bind(path);return attempt
        except subprocess.CalledProcessError:
            if attempt==attempts-1:raise
            time.sleep(2)

LOGS=Path('/tmp/slotted-trial-logs')

def tmpfs_logs(job):
    """Frontend trial logs live on tmpfs, linked from the job while it runs. Appending a row
    per frame on the SD card blocked the frontend's main thread for up to seconds (ext4
    journal / card latency, trial ao stall samples), which trials then measured as freezes."""
    logs=LOGS/job.name;logs.mkdir(parents=True,exist_ok=True)
    for name in ('frames.log','stream.tsv','room-frames.tsv'):
        (logs/name).touch();link=job/name
        if link.is_symlink() or link.exists():link.unlink()
        link.symlink_to(logs/name)
    return logs

def collect_logs(job):
    """After the trial frontend stops: replace the links with copies of every log, including
    the side logs the frontend writes next to them. Returns the number of files copied."""
    logs=LOGS/job.name
    if not logs.is_dir():return 0
    count=0
    for f in sorted(logs.iterdir()):
        target=job/f.name
        if target.is_symlink():target.unlink()
        shutil.copyfile(f,target);count+=1
    shutil.rmtree(logs)
    return count


def recover_channels(job, previous, root=Path('/userdata')):
    """Recover metadata from the first room trial, whose old snapshot omitted
    Ports/MPV. Both baseline and pre-recovery copies remain hash-verifiable.
    Call only with ES stopped, under the existing device lock."""
    if not re.fullmatch(r'slotted-ui-[a-zA-Z0-9_-]+',previous):raise ValueError('Invalid prior trial session')
    old=root/'system/slot-dev/slotted-trials'/previous
    if json.loads((old/'status.json').read_text())['state']!='complete':raise ValueError('Prior trial is not recovered')
    entries=json.loads((old/'extra-channel-backup.json').read_text());checked=[]
    for key,entry in entries.items():
        if key not in ('ports','mpv'):raise ValueError('Unexpected recovery scope')
        source=old/'extra-channel-backup'/(key+'.xml');target=root/'roms'/key/'gamelist.xml'
        if digest(source)!=entry['sha256']:raise ValueError('Channel baseline checksum mismatch')
        if digest(target)==entry['sha256']:continue
        parked=job/'before-channel-recovery'/(key+'.xml');parked.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(target,parked)
        if digest(parked)!=digest(target):raise ValueError('Channel recovery copy mismatch')
        checked.append((source,target,parked,entry['sha256']))
    try:
        for source,target,parked,sha in checked:
            shutil.copy2(source,target)
            if digest(target)!=sha:raise ValueError('Channel recovery failed')
    except BaseException:
        for source,target,parked,sha in checked:shutil.copy2(parked,target)
        raise
    return {target.relative_to(root).as_posix():dict(restored=sha,preserved=digest(parked)) for source,target,parked,sha in checked}


def run(job):
    request = json.loads((job / 'request.json').read_text())
    manifest = json.loads((job / 'manifest.json').read_text())
    snapshot = Snapshot('/userdata', request['session'])
    layout = device_install.Layout()
    report = {}
    prior = os.environ.copy()
    stopped = backed = swapped = rebound = False
    startup_backup=None;lock_held=False
    previous = None
    error = None
    def status(state, message):
        p = job / 'status.tmp'
        p.write_text(json.dumps(dict(state=state, message=message, **report), indent=2))
        p.replace(job / 'status.json')
    with Path('/userdata/system/slot-dev/editor-upload.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_held=True
            for name, sha in request['files'].items():
                if Path(name).name != name or digest(job / name) != sha:
                    raise ValueError('Trial payload mismatch: ' + name)
            validate_options(request)
            pid = esdev.es_pid()
            if not pid or json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                raise RuntimeError('Return to the frontend before the trial')
            for raw in Path('/proc/' + pid + '/environ').read_bytes().split(b'\0'):
                key, sep, value = raw.partition(b'=')
                if sep and key.startswith((b'SLOT_', b'SDL_')):
                    prior[key.decode()] = value.decode()
            report['prior_sha256'] = digest(OFFICIAL)
            report['candidate_sha256'] = digest(job / 'frontend')
            report['prior_theme'] = esdev.get('ThemeSet')
            shutil.copy2(OFFICIAL, job / 'previous-frontend')
            if digest(job / 'previous-frontend') != report['prior_sha256']:
                raise RuntimeError('Prior binary recovery copy mismatch')
            status('running', 'Snapshotting before a temporary side-by-side Slotted trial')
            stopped = True
            esdev.stop()
            if esdev.es_pid():
                raise RuntimeError('Frontend did not stop')
            if request.get('recoverChannelsFrom'):
                report['channel_recovery']=recover_channels(job,request['recoverChannelsFrom'])
            report['snapshot_counts'] = snapshot.backup()
            backed = True
            if request.get('uploadGate'):
                startup_backup=job/'startup-backup';report['startup_backup']=frontend_persistence.capture(startup_backup)
            staging, source = device_install.stage(layout, job / 'payload.tar', manifest, request['session'])
            # Prove every copied runtime file, including local-only models and authored layouts.
            assets = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()}
            copied = {p.relative_to(staging / '_slot').as_posix(): digest(p) for p in (staging / '_slot').rglob('*') if p.is_file()}
            if copied != assets:
                raise RuntimeError('Runtime asset copy differs from its source')
            report['verified_runtime_files'] = len(assets)
            (job / 'runtime-assets.json').write_text(json.dumps(assets, indent=2))
            previous = device_install.swap(layout, staging, job / 'previous-Slotted')
            swapped = True
            report['settings_migration'] = device_install.migrate_settings(layout)
            esdev.set_('ThemeSet', device_install.SLOTTED)
            report['trial_preferences']={}
            for key,setting in [('motion','subset.slotted-motion'),('tv','subset.slot-tv-model'),('style','subset.slot-model-style'),('color','subset.slot-console-color')]:
                if request.get(key):
                    report['trial_preferences'][setting]=dict(previous=esdev.get(setting),temporary=request[key])
                    esdev.set_(setting,request[key])
            if request.get('allModels'):
                hidden=esdev.get('HiddenSystems');visible=show_modelled_systems(hidden)
                report['trial_preferences']['HiddenSystems']=dict(previous=hidden,temporary=visible)
                esdev.set_('HiddenSystems',visible)
            if request.get('screensaverMs'):
                # Short idle delay so the checker can see the screensaver over the room and wake it.
                report['trial_preferences']['ScreenSaverTime']=dict(previous=esdev.get('ScreenSaverTime'),temporary=str(request['screensaverMs']))
                esdev.set_('ScreenSaverTime',str(request['screensaverMs']),'int')
            rebound = True
            bind(job / 'frontend')
            env = prior.copy()
            if 'indexBatch' in request:
                env['SLOT_SCENE_INDEX_BATCH']=str(request['indexBatch']);report['index_batch']=request['indexBatch']
            if request.get('startup','console')=='home':
                for key in ('SLOT_SCENE_PREVIEW_SYSTEM','SLOT_SCENE_PREVIEW_TV'):env.pop(key,None)
            else:env.update(SLOT_SCENE_PREVIEW_SYSTEM='nes', SLOT_SCENE_PREVIEW_TV='panasonic')
            logs = tmpfs_logs(job)
            env.update(SDL_NOMOUSE='1',
                       SLOT_SCENE_FRAMELOG=str(logs / 'frames.log'), SLOT_SCENE_STREAMLOG=str(logs / 'stream.tsv'),SLOT_SCENE_ROOMLOG=str(logs/'room-frames.tsv'))
            start(env)
            esdev.wait(45)
            time.sleep(6)
            report['trial_pid'] = esdev.es_pid()
            if digest(OFFICIAL) != report['candidate_sha256'] or esdev.get('ThemeSet') != device_install.SLOTTED:
                raise RuntimeError('Trial binary/theme did not activate')
            if request.get('uploadGate'):
                report['readyForUpload']=True
                fcntl.flock(lock,fcntl.LOCK_UN);lock_held=False
            status('ready', 'Slotted is running temporarily; waiting for bounded UI checks')
            deadline = time.monotonic() + (1800 if request.get('uploadGate') else 660)
            while not (job / 'finish.json').is_file():
                busy_upload=False
                if not esdev.es_pid() and request.get('uploadGate'):
                    try:
                        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN)
                    except BlockingIOError:busy_upload=True
                if time.monotonic() > deadline or (not esdev.es_pid() and not busy_upload):
                    raise RuntimeError('Trial timed out or frontend exited')
                time.sleep(.5)
            report['validation'] = json.loads((job / 'finish.json').read_text())
            while json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
                status('waiting-game', 'Waiting for the game to return before preservation audit')
                time.sleep(1)
            if not report['validation'].get('passed'):
                error = 'GUI checks did not pass'
        except BaseException as ex:
            error = str(ex)
        finally:
            if not lock_held and stopped:
                status('recovering','Waiting for any editor transaction before restoring the trial')
                fcntl.flock(lock,fcntl.LOCK_EX);lock_held=True
            if rebound and esdev.es_pid():
                try:
                    safe = json.loads(esdev.api('/runningGame')) == {'msg': 'NO GAME RUNNING'}
                except Exception:
                    safe = False
                if not safe:
                    status('failed', 'Game state is uncertain; retained trial and snapshot without stopping anything')
                    return
            try:
                if stopped:
                    esdev.stop()
                    if esdev.es_pid():
                        raise RuntimeError('Cannot recover while frontend is running')
                if swapped:
                    # Retain the entire tested theme; no asset or authored profile is deleted.
                    target = layout.target.resolve()
                    if target.parent != layout.themes.resolve():
                        raise RuntimeError('Unexpected Slotted path during recovery')
                    layout.target.rename(job / 'trial-Slotted')
                    if previous:
                        previous.rename(layout.target)
                if backed:
                    report['restore'] = snapshot.restore(runtime=True)
                    report['audit'] = snapshot.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):
                        raise RuntimeError('Trial preservation audit is not clean')
                if startup_backup:
                    frontend_persistence.restore(startup_backup);report['startup_restored']=True
                if rebound:
                    retries = rebind(job / 'previous-frontend')
                    if retries:report['rebind_retries'] = retries
                    if digest(OFFICIAL) != report['prior_sha256']:
                        raise RuntimeError('Prior frontend recovery hash mismatch')
            except BaseException as ex:
                error = (error + '; ' if error else '') + 'Recovery: ' + str(ex)
            if stopped:
                try:
                    start(prior)
                    esdev.wait(45)
                    report['final_pid'] = esdev.es_pid()
                    report['final_sha256'] = digest(OFFICIAL)
                    report['final_theme'] = esdev.get('ThemeSet')
                except BaseException as ex:
                    error = (error + '; ' if error else '') + 'Restart: ' + str(ex)
            try:
                report['logs_collected'] = collect_logs(job)
            except BaseException as ex:
                report['logs_error'] = str(ex)
            (job / 'report.json').write_text(json.dumps(report, indent=2))
            status('failed' if error else 'complete', error or 'Slotted trial passed; prior frontend, theme and user data restored')


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
