#!/usr/bin/env python3
"""Hash-verified device test snapshots; preserve changed/new data before restoring."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

SYSTEMS = ('gb', 'gbc', 'gba', 'snes', 'nes', 'n64', 'megadrive', 'genesis',
           'psx', 'psp', 'nds', 'pico8', 'dreamcast', 'ports', 'mpv')
DATA = ('saves', 'system/configs/retroarch', 'system/configs/ppsspp',
        'system/configs/emulationstation/es_settings.cfg',
        'system/configs/emulationstation/themesettings/art-book-slot.cfg',
        'system/configs/emulationstation/themesettings/Slotted.cfg',
        'system/knulli.conf') + tuple('roms/%s/gamelist.xml' % s for s in SYSTEMS)
RUNTIME = ('themes/art-book-slot', 'themes/Slotted',
           'system/configs/emulationstation/scripts/start/art-book-slot-watch.sh',
           'system/configs/emulationstation/scripts/game-selected/art-book-slot-watch.sh',  # legacy
           'system/configs/emulationstation/scripts/game-start/art-book-slot-insert.sh',
           'system/scripts/art-book-slot-game.sh')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


class Snapshot:
    def __init__(self, root, name):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name):
            raise ValueError('Invalid session name')
        self.root = Path(root).resolve()
        self.directory = self.root / 'system/slot-dev/sessions' / name

    def checked(self, relative, base=None):
        base = self.root if base is None else base
        path = base / relative
        if not path.resolve().is_relative_to(base.resolve()):
            raise ValueError('Path escapes snapshot scope: ' + str(path))
        return path

    def inventory(self, roots):
        result = {}
        for relative in roots:
            path = self.checked(relative)
            candidates = path.rglob('*') if path.is_dir() else [path]
            for candidate in candidates:
                key = str(candidate.relative_to(self.root))
                self.checked(key)
                if candidate.is_file():
                    result[key] = digest(candidate)
        return result

    def backup(self):
        if self.directory.exists():
            raise FileExistsError('Keep the existing snapshot: ' + str(self.directory))
        self.directory.mkdir(parents=True)
        manifest = {'created': time.time(), 'data': self.inventory(DATA),
                    'runtime': self.inventory(RUNTIME)}
        for group in ('data', 'runtime'):
            for key, value in manifest[group].items():
                source = self.checked(key)
                target = self.checked(key, self.directory / group)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                if digest(target) != value or digest(source) != value:
                    raise RuntimeError('File changed during backup: ' + key)
        (self.directory / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        (self.directory / 'complete').touch()
        return {group: len(manifest[group]) for group in ('data', 'runtime')}

    def manifest(self):
        if not (self.directory / 'complete').is_file():
            raise ValueError('Snapshot is incomplete')
        return json.loads((self.directory / 'manifest.json').read_text())

    def audit(self, runtime=False):
        manifest = self.manifest()
        groups = ('data', 'runtime') if runtime else ('data',)
        report = {}
        for group in groups:
            current = self.inventory(DATA if group == 'data' else RUNTIME)
            expected = manifest[group]
            report[group] = {'files': len(expected),
                             'changed': [k for k, v in expected.items() if current.get(k) != v],
                             'new': sorted(current.keys() - expected.keys())}
        return report

    def restore(self, runtime=False):
        manifest = self.manifest()
        groups = ('data', 'runtime') if runtime else ('data',)
        # Validate the entire selected backup before modifying any live file.
        for group in groups:
            for key, value in manifest[group].items():
                if digest(self.checked(key, self.directory / group)) != value:
                    raise ValueError('Corrupt backup: ' + key)
        park = self.directory / ('preserved-%d' % time.time_ns())
        report = {'restored': 0, 'modified': 0, 'new': 0, 'preserved': str(park)}
        for group in groups:
            expected = manifest[group]
            current = self.inventory(DATA if group == 'data' else RUNTIME)
            for key, value in current.items():
                if expected.get(key) == value:
                    continue
                source = self.checked(key)
                target = self.checked(key, park / group)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                if digest(target) != value:
                    raise RuntimeError('Could not preserve: ' + key)
                if key not in expected:
                    source.unlink()
                    report['new'] += 1
                else:
                    report['modified'] += 1
            for key, value in expected.items():
                target = self.checked(key)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.checked(key, self.directory / group), target)
                if digest(target) != value:
                    raise RuntimeError('Restore verification failed: ' + key)
                report['restored'] += 1
        (self.directory / 'last-restore.json').write_text(json.dumps(report, indent=2))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'audit', 'restore'))
    parser.add_argument('name')
    parser.add_argument('--runtime', action='store_true', help='also restore/audit theme and owned hooks')
    args = parser.parse_args()
    if args.action in ('backup', 'restore') and subprocess.run(
            ['pidof', 'emulationstation'], capture_output=True).returncode == 0:
        parser.error('Stop EmulationStation first so settings and gamelists are flushed')
    snapshot = Snapshot('/userdata', args.name)
    if args.action == 'backup':
        report = snapshot.backup()
    elif args.action == 'restore':
        report = snapshot.restore(args.runtime)
    else:
        report = snapshot.audit(args.runtime)
    print(json.dumps(report, indent=2), flush=True)
    if args.action == 'audit' and any(v['changed'] or v['new'] for v in report.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
