"""Prepare isolated native-review tree and invoke real GLES tabletop probe.

Only build/ outputs; active theme models, layouts and live browser drafts are untouched.
Run in WSL so symlinks reference the shared source tree. MIT.
"""
import json
import os
from pathlib import Path
import subprocess
from .selected_cartridges import KEYS, PACKAGES, ROOT, SLOT


def main():
    out=ROOT/'build/cartridge-implementation-20261019'
    stage=out/'preview-root';stage.mkdir(exist_ok=True)
    for p in SLOT.iterdir():
        if p.name=='consoles':continue
        link=stage/p.name
        if not link.exists():link.symlink_to(p,target_is_directory=p.is_dir())
    consoles=stage/'consoles';consoles.mkdir(exist_ok=True)
    for p in (SLOT/'consoles').iterdir():
        dst=consoles/p.name
        if p.name not in KEYS:
            if not dst.exists():dst.symlink_to(p,target_is_directory=p.is_dir())
            continue
        dst.mkdir(exist_ok=True)
        for f in p.iterdir():
            if f.name.startswith('media') and not f.name.startswith('media-ea'):continue
            if not (dst/f.name).exists():(dst/f.name).symlink_to(f,target_is_directory=f.is_dir())
        reg=json.loads((ROOT/'build/selected-cartridges'/p.name/'registration.json').read_text())
        for f in (PACKAGES/p.name/reg['uid']).glob('media*'):
            link=dst/f.name
            if link.is_symlink():link.unlink()
            link.symlink_to(f)
    env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'build/native/desktop/usr/lib/x86_64-linux-gnu'),
        SDL_VIDEODRIVER='offscreen',EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',
        SLOT_SCENE_CARTRIDGES='12',SLOT_SCENE_SELECTED='0',SLOT_SCENE_ALLOW_CLIP='1')
    renders=out/'renders';renders.mkdir(exist_ok=True)
    logs=[]
    for key in KEYS:
        face=ROOT/'build/tabletop'/('faces-'+key)/'0.png'
        if not face.exists():face=SLOT/'shells'/(key+'.png')
        for view,yaw,pitch in [('front',0,0),('rear',180,0),('side',80,0),('top',0,75),('bottom',0,-75),('quarter',25,-20)]:
            frame=renders/(key+'-'+view+'.bmp')
            local=dict(env,SLOT_SCENE_CAMERA='4',SLOT_SCENE_INSPECT='1',
                       SLOT_SCENE_INSPECT_YAW=str(yaw),SLOT_SCENE_INSPECT_PITCH=str(pitch))
            r=subprocess.run([str(ROOT/'build/tabletop/probe'),str(stage),str(ROOT/'build/tabletop/assets'),
                str(frame),key,'pvm',*[str(face)]*12],env=local,capture_output=True,text=True)
            (renders/(key+'-'+view+'.log')).write_text(r.stdout+r.stderr)
            logs.append(dict(system=key,view=view,exit=r.returncode))
            print(key,view,r.returncode,flush=True)
            if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    (out/'review-results.json').write_text(json.dumps(logs,indent=2)+'\n')


if __name__=='__main__':main()
