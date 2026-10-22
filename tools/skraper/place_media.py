#!/usr/bin/env python3
"""Place staged Skraper downloads where Art Book Slot uses them, compactly.

    python place_media.py REPORT STAGE SHARE JOURNAL [--systems gb,snes] [--jobs N]

REPORT is missing_art.py's JSON (device paths), STAGE the staged Skraper output
(\\\\HOST\\share\\...\\skraper-stage), SHARE the device's userdata share root
(\\\\HOST\\share). Only games that need something receive it, and nothing that
already exists is replaced:

- a label (support texture) and wheel for games whose label fell back to a logo
  or text: <rom dir>/media/labels|wheels/<rom>.<ext>
- a preview for games without a working video: <rom dir>/media/videos/<rom>.mp4,
  re-encoded for the shelf: square pixels, no audio (previews are silent), H.264
  CRF 30, at most 240 px high for cartridges (about their native resolution),
  360 px for discs and 480 px for DS (two stacked screens). Typically 0.2-0.9 MB
  instead of 1-3 MB.

Every created file is journaled with its SHA-256 so it can be removed again.
Link videos into gamelists afterwards on the device: python3 -m slotcart.previews link.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import tempfile
import time

HEIGHT = {'psx': 360, 'psp': 360, 'nds': 480}
CARTRIDGE_HEIGHT = 240
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')


def device_to_share(path, share):
    relative = PureWindowsPath(path.removeprefix('/userdata/'))
    return Path(share) / relative


def digest(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest()


def encode(source, target, height):
    # Square pixels first (anamorphic clips are squeezed by the frontend), then a
    # uniform downscale: aspect is always preserved, never stretched.
    scale = ("scale='trunc(iw*sar/2)*2':ih,setsar=1,"
             "scale=-2:'min(%d,ih)':flags=lanczos,setsar=1" % height)
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix='.slot-encode-', suffix='.mp4')
    os.close(handle)
    try:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                        '-an', '-vf', scale, '-c:v', 'libx264', '-preset', 'slow', '-crf', '30',
                        '-profile:v', 'main', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        temporary], check=True)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def settled(path, seconds=120):
    """Skraper may still be writing a download during a run."""
    return path.exists() and time.time() - path.stat().st_mtime > seconds


def existing(folder, stem, extensions):
    return next((folder / (stem + ext) for ext in extensions if settled(folder / (stem + ext))), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('stage')
    parser.add_argument('share')
    parser.add_argument('journal', type=Path)
    parser.add_argument('--systems')
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    wanted = set(args.systems.split(',')) if args.systems else set(report)
    journal = json.loads(args.journal.read_text()) if args.journal.exists() else {'created': []}
    done = {entry['path'] for entry in journal['created']}
    images, videos = [], []
    for system in sorted(wanted & set(report)):
        stage = Path(args.stage) / system / 'media'
        for rom in report[system]['fallback_labels']:
            stem = PureWindowsPath(rom).stem if '\\' in rom else Path(rom).stem
            rom_dir = device_to_share(rom, args.share).parent
            for kind in ('labels', 'wheels'):
                source = existing(stage / kind, stem, IMAGE_EXTENSIONS)
                if source and not existing(rom_dir / 'media' / kind, stem, IMAGE_EXTENSIONS):
                    images.append((source, rom_dir / 'media' / kind / (stem + source.suffix.lower())))
        for rom in report[system]['no_video']:
            stem = Path(rom).stem
            rom_dir = device_to_share(rom, args.share).parent
            source = stage / 'videos' / (stem + '.mp4')
            target = rom_dir / 'media' / 'videos' / (stem + '.mp4')
            if settled(source) and not target.exists():
                videos.append((source, target, HEIGHT.get(system, CARTRIDGE_HEIGHT), system))

    def record(target, kind, system, source):
        journal['created'].append({'path': str(target), 'kind': kind, 'system': system,
                                   'source_bytes': source.stat().st_size,
                                   'bytes': target.stat().st_size, 'sha256': digest(target)})

    for source, target in images:
        if str(target) in done:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        record(target, target.parent.name, target.parents[2].name, source)
    print('images placed:', len(images))

    def work(item):
        source, target, height, system = item
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            encode(source, target, height)
            return item, None
        except (subprocess.CalledProcessError, OSError) as error:
            return item, str(error)

    failures = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for count, (item, error) in enumerate(pool.map(work, videos), 1):
            source, target, height, system = item
            if error:
                failures.append({'source': str(source), 'error': error})
            else:
                record(target, 'videos', system, source)
            if count % 50 == 0:
                print('videos %d/%d' % (count, len(videos)), flush=True)
                args.journal.write_text(json.dumps(journal, indent=1))
    journal['failures'] = journal.get('failures', []) + failures
    args.journal.write_text(json.dumps(journal, indent=1))
    made = [e for e in journal['created'] if e['kind'] == 'videos']
    before = sum(e['source_bytes'] for e in made)
    after = sum(e['bytes'] for e in made)
    print('videos placed: %d, failed: %d; %.0f MB downloaded -> %.0f MB on the device'
          % (len(made), len(failures), before / 1e6, after / 1e6))


if __name__ == '__main__':
    main()
