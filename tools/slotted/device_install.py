"""Device-side Slotted install (launched detached over SSH by tools/slotted/install.py).

Installs /userdata/themes/Slotted next to art-book-slot, never replacing it:
  1. stop the frontend and take a verified snapshot (session_data.py);
  2. stage Slotted: copy the runtime assets (_slot/) from the existing Slotted install, or from
     art-book-slot on first install / resync, so authored layouts and local-only models carry over;
     then add Slotted's own files from payload.tar and verify every one against the manifest;
  3. swap the staged folder in (the previous Slotted is kept in the job folder);
  4. create themesettings/Slotted.cfg from art-book-slot.cfg (only the slot-* theme options), once;
  5. optionally select Slotted as the theme, start the frontend and audit.
Any failure restores the snapshot, puts the previous Slotted back and restarts the frontend.
"""
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import time

try:
    from slot_theme import SLOTTED, LEGACY
except ModuleNotFoundError:
    from tools.slot_theme import SLOTTED, LEGACY
DEVICE_LOCK = Path('/userdata/system/slot-dev/editor-upload.lock')
MIGRATED = ('slot-tv-model', 'slot-model-style', 'slot-console-color', 'slot-snes-cartridge-model',
            'slot-gba-sp-model', 'slot-video', 'slot-wallpaper', 'slot-state')


class Layout:
    def __init__(self, root='/userdata'):
        self.root = Path(root)
        self.themes = self.root / 'themes'
        self.target = self.themes / SLOTTED
        self.legacy = self.themes / LEGACY
        self.settings = self.root / 'system/configs/emulationstation/themesettings'


def checked_members(archive, manifest, staging):
    members = archive.getmembers()
    names = [m.name for m in members]
    if len(set(names)) != len(names) or set(names) != set(manifest):
        raise ValueError('Archive and manifest differ')
    for member in members:
        key = PurePosixPath(member.name)
        if (not member.isfile() or key.is_absolute() or '..' in key.parts or '\\' in member.name
                or key.parts[0] == '_slot' or not (staging / member.name).resolve().is_relative_to(staging.resolve())):
            raise ValueError('Unsafe package member: ' + member.name)
    return members


def digest(path):
    import hashlib
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest()


def stage(layout, payload, manifest, session, resync=False):
    """Builds the complete new Slotted folder beside the live one; returns its path."""
    staging = layout.themes / ('.Slotted-' + session)
    if staging.exists():
        raise FileExistsError('Staging folder already exists: ' + str(staging))
    source = layout.target / '_slot' if (layout.target / '_slot').is_dir() and not resync else layout.legacy / '_slot'
    if not source.is_dir():
        raise FileNotFoundError('No runtime assets to copy: ' + str(source))
    staging.mkdir(parents=True)
    shutil.copytree(source, staging / '_slot', symlinks=True)
    with tarfile.open(payload) as archive:
        for member in checked_members(archive, manifest, staging):
            target = staging / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    for name, entry in manifest.items():
        if digest(staging / name) != entry['sha256']:
            raise RuntimeError('Staged file does not match the manifest: ' + name)
    return staging, source


def swap(layout, staging, keep):
    """Moves the live Slotted (if any) to keep, then the staged folder into place."""
    previous = None
    if layout.target.exists():
        previous = keep
        layout.target.rename(previous)
    staging.rename(layout.target)
    return previous


def retain_failed(layout, path, keep):
    """Keep a failed derivative intact outside the theme search path; never delete assets."""
    if path.is_symlink() or path.resolve().parent != layout.themes.resolve():
        raise ValueError('Unexpected theme recovery path: ' + str(path))
    if keep.exists():
        raise FileExistsError('Keep the existing recovery copy: ' + str(keep))
    path.rename(keep)
    return keep


def undo_swap(layout, previous, keep=None):
    retained = None
    if layout.target.exists():
        keep = keep or ((previous.parent if previous else layout.root) / ('failed-Slotted-' + str(time.time_ns())))
        retained = retain_failed(layout, layout.target, keep)
    if previous and previous.exists():
        previous.rename(layout.target)
    return retained


def migrate_settings(layout):
    """Creates Slotted.cfg from art-book-slot.cfg once; ES records are name=value separated by CR."""
    target = layout.settings / (SLOTTED + '.cfg')
    if target.exists():
        return 'kept'
    source = layout.settings / (LEGACY + '.cfg')
    if not source.is_file():
        return 'none'
    records = source.read_bytes().decode('utf-8', 'replace').replace('\n', '\r').split('\r')
    keep = [r for r in records if any(r.startswith('subset.' + name + '=') for name in MIGRATED)]
    if not keep:
        return 'none'
    layout.settings.mkdir(parents=True, exist_ok=True)
    target.write_bytes(('\r'.join(keep) + '\r').encode('utf-8'))
    return 'created'


def check_audit(report, activate, migrated):
    allowed_data = set()
    if migrated == 'created':
        allowed_data.add('system/configs/emulationstation/themesettings/' + SLOTTED + '.cfg')
    if activate:
        allowed_data.add('system/configs/emulationstation/es_settings.cfg')
    data = {n.replace('\\', '/') for n in report['data']['changed'] + report['data']['new']}
    if not data <= allowed_data:
        raise RuntimeError('Unexpected user data changes: ' + ', '.join(sorted(data - allowed_data)))
    runtime = {n.replace('\\', '/') for n in report['runtime']['changed'] + report['runtime']['new']}
    stray = sorted(n for n in runtime if not n.startswith('themes/' + SLOTTED + '/'))
    if stray:
        raise RuntimeError('Unexpected runtime changes: ' + ', '.join(stray[:8]))


def _run(job):
    sys.path.insert(0, str(job))
    from session_data import Snapshot
    import esdev
    config = json.loads((job / 'request.json').read_text())
    manifest = json.loads((job / 'manifest.json').read_text())
    layout = Layout()
    snapshot = Snapshot('/userdata', config['session'])
    activate, resync = bool(config.get('activate')), bool(config.get('resyncSlot'))
    state = dict(stopped=False, backed_up=False, swapped=False, previous=None, staging=None)

    def status(kind, message, **extra):
        value = dict(state=kind, message=message, session=config['session'], **extra)
        (job / 'status.tmp').write_text(json.dumps(value, indent=2))
        (job / 'status.tmp').replace(job / 'status.json')

    try:
        if not layout.legacy.is_dir():
            raise RuntimeError('art-book-slot is not installed; Slotted copies its runtime assets.')
        if not esdev.es_pid() or json.loads(esdev.api('/runningGame')) != {'msg': 'NO GAME RUNNING'}:
            raise RuntimeError('Return to the frontend and close any running game first.')
        previous_theme = esdev.get('ThemeSet')
        status('running', 'Stopping the frontend and taking a verified snapshot…')
        state['stopped'] = True
        esdev.stop()
        if esdev.es_pid():
            raise RuntimeError('Frontend did not stop')
        counts = snapshot.backup()
        state['backed_up'] = True
        status('running', 'Copying the tabletop assets and Slotted files…', backup=counts)
        staging, source = stage(layout, job / 'payload.tar', manifest, config['session'], resync)
        state['staging'] = staging
        state['previous'] = swap(layout, staging, job / 'previous-Slotted')
        state['swapped'] = True
        state['staging'] = None
        migrated = migrate_settings(layout)
        if activate:
            esdev.set_('ThemeSet', SLOTTED)
        audit = snapshot.audit(True)
        check_audit(audit, activate, migrated)
        status('running', 'Starting the frontend…')
        esdev.start()
        esdev.wait(60)
        time.sleep(8)
        if not esdev.es_pid():
            raise RuntimeError('Frontend did not stay running')
        final = snapshot.audit(True)
        check_audit(final, activate, migrated)
        status('complete', 'Slotted installed%s. art-book-slot is unchanged.' % (' and selected' if activate else ''),
               backup=counts, audit=final, settings=migrated, assetsFrom=str(source),
               previousTheme=previous_theme, themeSet=esdev.get('ThemeSet'), files=len(manifest),
               previousSlotted=str(state['previous']) if state['previous'] else None,
               recovery=str(snapshot.directory))
    except BaseException as error:
        recovery = {}
        try:
            if state['stopped']:
                esdev.stop()
                if state['staging'] and Path(state['staging']).exists():
                    retain_failed(layout, Path(state['staging']), job / 'failed-staging')
                if state['swapped']:
                    recovery['retained'] = str(undo_swap(layout, state['previous'], job / 'failed-Slotted'))
                    recovery['slotted'] = 'previous restored' if state['previous'] else 'removed'
                if state['backed_up']:
                    recovery['restore'] = snapshot.restore(runtime=True)
                    recovery['audit'] = snapshot.audit(runtime=True)
                esdev.start()
                esdev.wait(60)
        except BaseException as rollback_error:
            recovery['error'] = str(rollback_error)
        status('failed', str(error).rstrip('.') + '.', recovery=recovery, snapshot=str(snapshot.directory))


def run(job):
    import fcntl
    with DEVICE_LOCK.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            (job / 'status.json').write_text(json.dumps(dict(state='failed', message='Another device transaction is running.')))
            return
        _run(job)


if __name__ == '__main__':
    run(Path(sys.argv[1]).resolve())
