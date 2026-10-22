#!/usr/bin/env python3
"""Install or remove only Art Book Slot's own launch hooks, without changing ES settings."""
import argparse
from pathlib import Path
import shutil

MARKER = b'Art Book Slot managed hook'
SCRIPTS = Path('/userdata/system/configs/emulationstation/scripts')
TARGETS = {
    'art-book-slot-insert.sh': SCRIPTS / 'game-start',
    'art-book-slot-game.sh': Path('/userdata/system/scripts'),
    'art-book-slot-watch.sh': SCRIPTS / 'start',
}
# Earlier versions watched every selection. ES forks for each script on each
# cursor move, so our copy there is removed; anyone else's file is left alone.
LEGACY = {'art-book-slot-watch.sh': SCRIPTS / 'game-selected'}


def owned(path):
    return path.is_file() and not path.is_symlink() and MARKER in path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'uninstall', 'status'))
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    if args.action == 'install' and not (source / 'slot-launch').is_file():
        parser.error('slot-launch is missing; build or download the ARM64 helper first')
    if args.action == 'install' and not (source / 'watch.py').is_file():
        parser.error('watch.py is missing; copy the complete launch folder first')
    # Preflight all destinations before writing anything.
    for name, folder in TARGETS.items():
        dest = folder / name
        if dest.is_symlink() or (dest.exists() and MARKER not in dest.read_bytes()):
            parser.error('refusing to replace an unrelated file: %s' % dest)
    if args.action in ('install', 'uninstall'):
        for name, folder in LEGACY.items():
            if owned(folder / name):
                (folder / name).unlink()
                print('removed legacy hook: ' + str(folder / name))
    for name, folder in TARGETS.items():
        dest = folder / name
        if args.action == 'install':
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, dest)
            dest.chmod(0o755)
        elif args.action == 'uninstall':
            dest.unlink(missing_ok=True)
        print(('active: ' if dest.exists() else 'inactive: ') + str(dest))
    if args.action == 'install':
        (source / 'slot-launch').chmod(0o755)
        import subprocess
        subprocess.run(['python3', str(source / 'watch.py'), 'ensure'], check=True)
        print('Use Art Book Slot with Game launch transition set to Instant.')
    elif args.action == 'uninstall':
        import subprocess
        subprocess.run(['python3', str(source / 'watch.py'), 'stop'], check=True)


if __name__ == '__main__':
    main()
