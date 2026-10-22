"""Validate current cartridges in the backed-up device layouts, without edits.

Run in WSL. Private prepared files and outputs stay in build/; the user's saved
JSON, browser drafts and installed device theme are never written. MIT.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from .selected_cartridges import ROOT,SLOT,KEYS

OUT=ROOT/'build/cartridge-validation-20261019'


def prepare():
    prepared=OUT/'prepared';prepared.mkdir(exist_ok=True)
    for p in (ROOT/'build/tabletop/assets').iterdir():
        if p.name=='layouts':continue
        link=prepared/p.name
        if not link.exists():link.symlink_to(p,target_is_directory=p.is_dir())
    layouts=prepared/'layouts';layouts.mkdir(exist_ok=True)
    source=ROOT/'research/device-backups/theme-user-20261019-033049/device-layouts'
    for p in source.glob('*.scene'):shutil.copy2(p,layouts/p.name)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in layouts.glob('*.scene')}
    (OUT/'layout-fixtures.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for key in KEYS:
        faces=OUT/'faces'/key;faces.mkdir(parents=True,exist_ok=True)
        for i in range(12):
            original=ROOT/'build/tabletop'/('faces-'+key)/(str(i)+'.png')
            if not original.exists():original=ROOT/'build/tabletop'/('faces-'+key)/'0.png'
            if not original.exists():original=SLOT/'shells'/(key+'.png')
            shutil.copy2(original,faces/(str(i)+'.png'))
    return prepared


def main():
    ap=argparse.ArgumentParser();ap.add_argument('systems',nargs='*',choices=KEYS)
    ap.add_argument('--aspect',choices=('3:2','4:3','both'),default='both')
    args=ap.parse_args();OUT.mkdir(exist_ok=True)
    prepared=prepare();results=[]
    env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'),
        SDL_VIDEODRIVER='offscreen',EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1')
    for key in args.systems or KEYS:
        tv='panasonic' if key in ('nes','md') else 'pvm'
        for aspect in ('3:2','4:3') if args.aspect=='both' else (args.aspect,):
            dest=OUT/'host'/(key+'-'+aspect.replace(':',''));dest.mkdir(parents=True,exist_ok=True)
            command=[str(OUT/'probe-host'),str(SLOT),str(prepared),str(dest),key,tv,str(OUT/'faces'/key)+'/']
            r=subprocess.run(command,env=dict(env,SLOT_SCENE_ASPECT=aspect),capture_output=True,text=True)
            (dest/'probe.log').write_text(r.stdout+r.stderr)
            results.append(dict(system=key,tv=tv,aspect=aspect,exit=r.returncode))
            print(key,aspect,r.returncode,flush=True)
            if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    (OUT/'host-results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':main()
