"""Refresh PS1 physical rings from existing flat faces, preserving printed art.

Run beside the installed slotcart package (set PYTHONPATH to the theme's _slot).
Creates a verified complete backup before updating the flat face, native texture,
poster and cache revision. No scraping, metadata updates or ROM reads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from PIL import Image
from slotcart import render


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_write(image, path, format):
    temporary = path.with_name(path.name+'.slot-material-part')
    image.save(temporary,format)
    os.replace(temporary,path)


def refresh(media, shapes, backup):
    media, shapes, backup = map(Path,(media,shapes,backup))
    if backup.exists():
        raise FileExistsError('Keep the existing backup: ' + str(backup))
    if backup.resolve().is_relative_to(media.resolve()):
        raise ValueError('Backup must be outside the media directory')
    manifest_path = media/'.slotcart.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    revision = json.loads((shapes/'shape.json').read_text())['revision']
    shape = render.Shape(shapes)
    if shape.name != 'psx' or not shape.disc:
        raise ValueError('Requires the PS1 physical-surface profile')
    jobs = []
    for stem,key in manifest.items():
        if Path(stem).name != stem or stem in ('.','..'):
            raise ValueError('Unsafe cached stem')
        values = json.loads(key)
        if values[1] != 'psx':
            raise ValueError('Mixed non-PS1 cache')
        face = media/(stem+'.disc.png')
        if not face.is_file():
            raise FileNotFoundError('Missing original flat face: ' + str(face))
        with Image.open(face) as image:
            if image.size != shape.print_mask.size:
                raise ValueError('Unexpected flat face size: ' + str(face))
        jobs.append((stem,face,values))
    # Preserve every existing asset before the first write, including manual
    # prints and the old revision manifest. Verify each source and copied hash.
    backup.mkdir(parents=True)
    hashes = {}
    for path in media.iterdir():
        if path.is_file():
            hashes[path.name] = digest(path)
            copied = backup/path.name
            shutil.copy2(path,copied)
            if digest(copied) != hashes[path.name] or digest(path) != hashes[path.name]:
                raise RuntimeError('Asset changed during backup: ' + str(path))
    (backup/'backup-sha256.json').write_text(json.dumps(hashes,indent=2))
    for stem,face,values in jobs:
        with Image.open(backup/face.name) as previous:
            flat = render.disc_texture(shape,previous)
        image_write(flat,face,'PNG')
        image_write(flat.resize((512,512),Image.Resampling.LANCZOS),media/(stem+'.disc.tga'),'TGA')
        image_write(render.disc_poster(shape,flat),media/(stem+'.png'),'PNG')
        values[0] = [render.VERSION,revision]
        manifest[stem] = json.dumps(values)
    temporary = manifest_path.with_name(manifest_path.name+'.slot-material-part')
    temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=0),encoding='utf-8')
    os.replace(temporary,manifest_path)
    return dict(updated=len(jobs),revision=revision,backup=str(backup),preserved=len(hashes))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('media',type=Path)
    parser.add_argument('shapes',type=Path)
    parser.add_argument('backup',type=Path)
    options = parser.parse_args()
    if os.name == 'posix' and subprocess.run(['pidof','emulationstation'],capture_output=True).returncode == 0:
        parser.error('Stop EmulationStation before refreshing visible assets')
    print(json.dumps(refresh(options.media,options.shapes,options.backup)))
