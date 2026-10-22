"""Link downloaded shelf previews into ES gamelists, reversibly.

    python3 -m slotcart.previews link [--systems gb,snes] [--dry-run]
    python3 -m slotcart.previews restore JOURNAL

Skraper (with the Art Book Slot preset) or any other tool saves previews as
<rom dir>/media/videos/<rom name>.mp4. The shelf plays a game's gamelist <video>,
so `link` adds that element for games that have no working video and such a
file. Nothing else in the gamelist changes: names, play counts, favourites and
existing videos stay as they are. Games missing from a gamelist get a minimal
entry with only <path> and <video>, which ES then fills in as usual.

ES keeps gamelists in memory and writes them back, so stop it first
(/etc/init.d/S31emulationstation stop). Each run saves the touched gamelists and a
journal under /userdata/system/slotcart/previews/; `restore` removes only links
that are still exactly as this tool wrote them.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from .library import EXTENSIONS, SKIP_DIRS, SYSTEMS

JOURNALS = Path('/userdata/system/slotcart/previews')


def load(path):
    return ET.parse(path, ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))


def save(tree, path):
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.slot-previews-', suffix='.xml')
    os.close(handle)
    try:
        # No re-indenting: untouched entries keep their exact formatting.
        tree.write(temporary, encoding='utf-8', xml_declaration=True)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def rom_files(system_dir, kind):
    """The shelf scanner's ROMs, as (directory, stem) -> paths in extension preference."""
    exts = EXTENSIONS[kind] + (() if kind in ('psx', 'dreamcast', 'psp', 'pico8') else ('.zip',))
    groups = {}
    for dirpath, dirnames, filenames in os.walk(system_dir):
        dirnames[:] = sorted(d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith('.'))
        for name in filenames:
            if name.lower().endswith(exts):
                path = Path(dirpath) / name
                groups.setdefault((path.parent, path.stem), []).append(path)
    for paths in groups.values():
        paths.sort(key=lambda p: next(i for i, e in enumerate(exts) if p.name.lower().endswith(e)))
    return groups


def plan_system(system_dir):
    """(tree, [(game element or None, rom, clip)]) for games needing a link."""
    videos = system_dir / 'media' / 'videos'
    if not videos.is_dir():
        return None, []
    clips = {}
    for clip in videos.rglob('*.mp4'):
        clips[(clip.parent.relative_to(videos), clip.stem)] = clip
    gamelist = system_dir / 'gamelist.xml'
    tree = load(gamelist) if gamelist.exists() else ET.ElementTree(ET.Element('gameList'))
    entries = {}
    for game in tree.getroot().iter('game'):
        path = (game.findtext('path') or '').strip()
        if path:
            entries[(system_dir / path).resolve()] = game
    work = []
    for (folder, stem), paths in rom_files(system_dir, SYSTEMS[system_dir.name]).items():
        # Clips mirror the ROM's folder below the system: media/videos/<subdir>/<rom>.mp4,
        # and also accept a flat media/videos/<rom>.mp4 for ROMs in subfolders.
        sub = folder.relative_to(system_dir)
        clip = clips.get((sub, stem)) or clips.get((Path('.'), stem))
        if not clip:
            continue
        # One game per name (a .cue and its .bin are one disc): every ROM ES already
        # lists, otherwise the preferred format only.
        listed = [rom for rom in paths if rom.resolve() in entries]
        for rom in listed or paths[:1]:
            game = entries.get(rom.resolve())
            current = (game.findtext('video') or '').strip() if game is not None else ''
            if current and (system_dir / current).exists():
                continue  # a working video is never replaced
            work.append((game, rom, clip))
    return tree, work


def link(systems, dry_run=False, roms=Path('/userdata/roms')):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    journal_dir = JOURNALS / stamp
    record = {'created': stamp, 'changes': [], 'gamelists': {}}
    for system in systems:
        system_dir = roms / system
        tree, work = plan_system(system_dir)
        if not work:
            continue
        gamelist = system_dir / 'gamelist.xml'
        print('%-10s %4d previews to link' % (system, len(work)))
        if dry_run:
            continue
        journal_dir.mkdir(parents=True, exist_ok=True)
        if gamelist.exists():
            backup = journal_dir / (system + '-gamelist.xml')
            shutil.copy2(gamelist, backup)
            record['gamelists'][str(gamelist)] = str(backup)
        for game, rom, clip in work:
            path = './' + rom.relative_to(system_dir).as_posix()
            value = './' + clip.relative_to(system_dir).as_posix()
            added_game = game is None
            if added_game:
                game = ET.SubElement(tree.getroot(), 'game')
                ET.SubElement(game, 'path').text = path
            video = game.find('video')
            old = video.text if video is not None else None
            if video is None:
                video = ET.SubElement(game, 'video')
            video.text = value
            record['changes'].append({'gamelist': str(gamelist), 'rom': path, 'old': old,
                                      'new': value, 'added_game': added_game})
        save(tree, gamelist)
    if not dry_run and record['changes']:
        (journal_dir / 'journal.json').write_text(json.dumps(record, indent=1))
        print('journal:', journal_dir / 'journal.json')
    return len(record['changes'])


def restore(journal):
    record = json.loads(Path(journal).read_text())
    restored = skipped = 0
    for gamelist in {change['gamelist'] for change in record['changes']}:
        path = Path(gamelist)
        tree = load(path)
        root = tree.getroot()
        games = {(game.findtext('path') or '').strip(): game for game in root.iter('game')}
        for change in record['changes']:
            if change['gamelist'] != gamelist:
                continue
            game = games.get(change['rom'])
            video = game.find('video') if game is not None else None
            if video is None or video.text != change['new']:
                skipped += 1
                continue
            if change['added_game'] and len(game) == 2:
                root.remove(game)
            elif change['old'] is None:
                game.remove(video)
            else:
                video.text = change['old']
            restored += 1
        save(tree, path)
    print('restored %d links, skipped %d changed since' % (restored, skipped))


def es_running():
    return subprocess.run(['pidof', 'emulationstation'], capture_output=True).returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='slotcart.previews', description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='action', required=True)
    make = commands.add_parser('link')
    make.add_argument('--systems', default=','.join(SYSTEMS))
    make.add_argument('--roms', type=Path, default=Path('/userdata/roms'))
    make.add_argument('--dry-run', action='store_true')
    undo = commands.add_parser('restore')
    undo.add_argument('journal', type=Path)
    args = parser.parse_args(argv)
    if not getattr(args, 'dry_run', False) and es_running():
        sys.exit('Stop EmulationStation first: it would overwrite the gamelists on exit.')
    if args.action == 'link':
        systems = [s for s in args.systems.split(',') if s in SYSTEMS]
        print('linked', link(systems, args.dry_run, args.roms))
    else:
        restore(args.journal)


if __name__ == '__main__':
    main()
