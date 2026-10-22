#!/usr/bin/env python3
"""Write a Skraper config for one staged Art Book Slot run, derived from an existing one.

    python make_run_config.py SOURCE_CONFIG TARGET_CONFIG STAGE_UNC [--media-root DIR]

Keeps the source's account and preferences untouched (credential fields are copied
as opaque values, never printed), keeps only the shelf systems, points each at
STAGE_UNC\\<system> and downloads only what the theme uses: media\\labels (support
texture), media\\wheels and media\\videos (normalized), inside the stage or below
--media-root. The gamelist Skraper writes stays there too, never in a ROM folder.
"""
import argparse
import copy
import json
from pathlib import Path
import sys

# The preset ships with the theme, next to the baker.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'theme/art-book-slot/_slot/skraper'))
from preset import SHELF_SYSTEMS, media_entries  # noqa: E402

GAMELIST_ES = 1          # GameList.ListType.EmulationStation
OVERWRITE_ONLY = 1       # GameList.Creation.OverwriteOnly (stage file only)
OVERRIDE_GAMELIST, OVERRIDE_ROMS, OVERRIDE_MEDIAS = 1, 2, 8


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('stage')
    parser.add_argument('--media-root', help='write downloads to MEDIA_ROOT\\<system> on this PC '
                        'instead of inside the network stage (saves a round trip over Wi-Fi)')
    args = parser.parse_args()
    config = json.loads(args.source.read_text(encoding='utf-8-sig'))
    systems = []
    for entry in config['Systems']:
        folder = entry['GamesAndRoms']['Path'].rstrip('\\/').split('\\')[-1].split('/')[-1]
        if folder not in SHELF_SYSTEMS:
            continue
        entry = copy.deepcopy(entry)
        entry['Overriden'] |= OVERRIDE_GAMELIST | OVERRIDE_ROMS | OVERRIDE_MEDIAS
        entry['GamesAndRoms']['Path'] = args.stage.rstrip('\\') + '\\' + folder
        root = args.media_root.rstrip('\\') + '\\' + folder if args.media_root else '%ROMROOTFOLDER%'
        gamelist = copy.deepcopy(config['AllSystems']['GameList'])
        gamelist.update(Type=GAMELIST_ES, Behavior=OVERWRITE_ONLY,
                        OutputFile=root + '\\gamelist.xml')
        entry['GameList'] = gamelist
        entry['Medias'] = media_entries(root)
        systems.append(entry)
        print('staged system', folder, entry['SystemId'])
    missing = set(SHELF_SYSTEMS) - {s['GamesAndRoms']['Path'].split('\\')[-1] for s in systems}
    if missing:
        print('not configured in the source, skipped:', ', '.join(sorted(missing)))
    config['Systems'] = systems
    args.target.write_text(json.dumps(config, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
