#!/usr/bin/env python3
"""List shelf games whose label fell back to a logo/text and games without a preview video.

Run on the device: python3 missing_art.py [--json OUT]. Reads the baker's manifests
(media/slotcarts/.slotcart.json), each system's gamelist.xml and the ROM folders through
slotcart's own scanner, so it agrees with what the shelf shows. Changes nothing.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

THEME = Path('/userdata/themes/art-book-slot/_slot')
sys.path.insert(0, str(THEME))
from slotcart.library import SYSTEMS, CrcCache, scan  # noqa: E402

# Pico-8 carts carry their own label art.
SHELVES = [s for s in SYSTEMS if s != 'pico8']


def videos(system_dir):
    linked = {}
    try:
        root = ET.parse(system_dir / 'gamelist.xml').getroot()
    except (OSError, ET.ParseError):
        return linked
    for game in root.iter('game'):
        path = (game.findtext('path') or '').strip()
        video = (game.findtext('video') or '').strip()
        if path:
            rom = (system_dir / path).resolve()
            target = (system_dir / video).resolve() if video else None
            linked[str(rom)] = bool(target and target.exists())
    return linked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roms', default='/userdata/roms')
    parser.add_argument('--json')
    args = parser.parse_args()
    games = scan(args.roms, SHELVES, CrcCache(str(Path.home() / '.cache/slotcart')))
    report = {}
    for system in SHELVES:
        system_dir = Path(args.roms) / system
        members = [g for g in games if g.path.parent == system_dir or system_dir in g.path.parents]
        if not members:
            continue
        try:
            manifest = json.loads((system_dir / 'media/slotcarts/.slotcart.json').read_text())
        except (OSError, ValueError):
            manifest = {}
        kinds = Counter()
        fallback = []
        for g in members:
            entry = manifest.get(g.stem)
            kind = json.loads(entry)[4] if entry else 'unbaked'
            kinds[kind] += 1
            if kind in ('logo', 'text', 'unbaked'):
                fallback.append(str(g.path))
        linked = videos(system_dir)
        no_video = [str(g.path) for g in members if not linked.get(str(g.path.resolve()))]
        report[system] = {'games': len(members), 'label_sources': dict(kinds),
                          'fallback_labels': sorted(fallback), 'no_video': sorted(no_video)}
    summary = {s: {'games': r['games'], 'fallback_labels': len(r['fallback_labels']),
                   'no_video': len(r['no_video']), 'sources': r['label_sources']} for s, r in report.items()}
    print(json.dumps(summary, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
