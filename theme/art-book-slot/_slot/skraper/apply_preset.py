#!/usr/bin/env python3
"""Add Art Book Slot's media to an existing Skraper setup (Skraper 1.x).

    python apply_preset.py PATH\\TO\\skraper.config.json [--dry-run]

Close Skraper first: it rewrites its config when it exits. For every shelf system
already set up in Skraper (Game Boy, GBC, GBA, SNES, NES, N64, Mega Drive/Genesis,
PlayStation, PSP, DS), the system's current media list is kept and three entries
are added once: support texture -> media\\labels, wheel -> media\\wheels and, unless
the system already downloads a video, normalized video -> media\\videos. Login, ROM
folders, gamelist options and every other system stay unchanged. A timestamped
backup is written next to the config.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import time

from preset import NORMALIZED_VIDEO, SHELF_SYSTEMS, is_theme_entry, media_entries

OVERRIDE_MEDIAS = 8
VIDEO = 3  # MediaType.Video


def ours(entry):
    """An entry this preset added before (theme media type into its media folder)."""
    return is_theme_entry(entry) and any(entry.get('OutputFolder') == m['OutputFolder']
                                         for m in media_entries())


def folder_name(system):
    return system['GamesAndRoms']['Path'].rstrip('\\/').replace('/', '\\').split('\\')[-1].lower()


def apply(config):
    changed = []
    for system in config['Systems']:
        name = folder_name(system)
        if name not in SHELF_SYSTEMS:
            continue
        # Start from what this system scrapes today, per-system or global.
        current = system['Medias'] if system['Overriden'] & OVERRIDE_MEDIAS else config['AllSystems']['Medias']
        # An existing video entry already feeds the gamelist <video> the shelf plays;
        # a second one would compete for that link, so keep the user's.
        theirs = [entry for entry in current if not ours(entry)]
        has_video = any(entry.get('Type') in (VIDEO, NORMALIZED_VIDEO) for entry in theirs)
        medias = [copy.deepcopy(entry) for entry in theirs
                  if not is_theme_entry(entry) or entry.get('Type') in (VIDEO, NORMALIZED_VIDEO)]
        additions = [entry for entry in media_entries()
                     if not (has_video and entry['Type'] == NORMALIZED_VIDEO)]
        system['Medias'] = medias + additions
        system['Overriden'] |= OVERRIDE_MEDIAS
        changed.append(name)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    changed = apply(config)
    if not changed:
        raise SystemExit('No shelf systems found. Add them in Skraper (point it at your roms folder) first.')
    print('Art Book Slot media added for:', ', '.join(changed))
    if args.dry_run:
        return
    backup = args.config.with_name(args.config.name + '.' + time.strftime('%Y%m%d-%H%M%S') + '.bak')
    shutil.copy2(args.config, backup)
    args.config.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print('Backup:', backup)


if __name__ == '__main__':
    main()
