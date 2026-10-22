"""Retain an owned-file candidate package locally; never deploy or publish it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
from tools.frontend.apply import PIN
from tools.slot_theme import ROOT
from tools.slotted.install import package

MARKERS=(b'SLOTTED_ROOM1:SLOTHOME1,SLOTWORLD1',b'SLOTTED_ROOM_FEATURES1:motion,crt,controller-devicepath')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def build(candidate,output=None):
    candidate=Path(candidate).resolve();data=candidate.read_bytes()
    if len(data)<20 or data[:6]!=b'\x7fELF\x02\x01' or data[18:20]!=b'\xb7\x00':raise ValueError('Use a 64-bit AArch64 Linux frontend')
    if not all(marker in data for marker in MARKERS):raise ValueError('Candidate lacks the current room capabilities')
    digest=hashlib.sha256(data).hexdigest()
    output=Path(output or ROOT/'build/slotted/releases'/('room-'+time.strftime('%Y%m%d-%H%M%S')+'-'+digest[:10])).resolve()
    output.mkdir(parents=True,exist_ok=False)
    target=output/'frontend-candidate';shutil.copy2(candidate,target)
    if sha(target)!=digest:raise OSError('Candidate copy checksum mismatch')
    theme=package(output)
    owned={ROOT/'tools/frontend/apply.py',ROOT/'tools/frontend/SlotState.h',ROOT/'tools/slot_theme.py',
           ROOT/'tools/tabletop/install_transition_frontend.py',ROOT/'tools/frontend/persistence.py',
           ROOT/'docs/SLOTTED_THEME_PLAN.md',ROOT/'docs/TABLETOP_HANDOFF.md',ROOT/'CREDITS.md',ROOT/'LICENSE'}
    for folder,suffixes in [('tools/frontend/overlay',{'.h','.cpp','.c','.inc'}),('tools/slotlaunch',{'.h','.c'}),
                            ('tools/slotted',{'.py'}),('tools/tabletop/editor',{'.py','.js','.html','.css','.md','.ps1','.scene'})]:
        owned.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts)
    sources={}
    for source in sorted(owned):
        relative=source.relative_to(ROOT).as_posix();dest=output/'source'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest);sources[relative]=sha(source)
        if sha(dest)!=sources[relative]:raise OSError('Source copy checksum mismatch: '+relative)
    (output/'owned-source.json').write_text(json.dumps(sources,indent=2)+'\n')
    profile_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'scene-layouts').glob('*.json'))}
    receipt=dict(state='candidate-not-installed',sourcePin=PIN,frontendSha256=digest,themeFiles=len(theme),
                 sourceFiles=len(sources),capabilities=[m.decode() for m in MARKERS],authoredProfileHashes=profile_hashes,
                 runtimeAssets='Keep the current device runtime; no models, masters, archives or authored JSON are replaced by this package.')
    (output/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return output,receipt

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('candidate',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();output,receipt=build(args.candidate,args.output)
    print(json.dumps(dict(directory=str(output),**receipt),indent=2))
if __name__=='__main__':main()
