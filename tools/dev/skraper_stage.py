#!/usr/bin/env python3
"""Stage only the shelf games missing a label or a preview for one Skraper run.

Run on the device after missing_art.py --json REPORT:
    python3 skraper_stage.py REPORT STAGE
STAGE/<system>/ receives symbolic links to those ROMs (plus same-stem companions such
as .bin tracks), so Skraper scans a small set over the network share and writes its
media inside STAGE. No ROM folder or gamelist is touched; skraper_merge.py places
the results afterwards.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('stage', type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if args.stage.exists() and any(args.stage.iterdir()):
        raise SystemExit('Stage must be new or empty: %s' % args.stage)
    plan, listings = {}, {}

    def siblings(rom):
        # Literal prefix match: ROM names often contain glob characters such as [!].
        if rom.parent not in listings:
            listings[rom.parent] = [p for p in rom.parent.iterdir() if p.is_file()]
        return [p for p in listings[rom.parent] if p != rom and p.name.startswith(rom.stem)]

    for system, entry in report.items():
        roms = sorted(set(entry['fallback_labels']) | set(entry['no_video']))
        folder = args.stage / system
        folder.mkdir(parents=True, exist_ok=True)
        staged = {}
        for rom in map(Path, roms):
            if rom.name in staged:
                continue  # same file name in two subfolders: keep the first
            companions = [rom] + (siblings(rom) if rom.suffix.lower() in ('.cue', '.m3u', '.gdi') else [])
            for source in companions:
                link = folder / source.name
                if not link.exists():
                    link.symlink_to(source)
            staged[rom.name] = str(rom)
        plan[system] = staged
        print('%-10s %4d games' % (system, len(staged)))
    (args.stage / 'stage.json').write_text(json.dumps(plan, indent=1))


if __name__ == '__main__':
    main()
