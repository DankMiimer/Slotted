"""Build the launch helper against a prepared, hash-recorded H700 workspace."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from tools.frontend.prepare_build import ROOT,aarch64,sha,verify_workspace

def build(workspace,output):
    workspace=Path(workspace).resolve();output=Path(output).absolute()
    if output.exists():raise FileExistsError('Keep the existing helper: '+str(output))
    verify_workspace(workspace)
    receipt=json.loads((workspace/'build-inputs.json').read_text())
    includes=Path(receipt['sdlHeaders']);libraries=Path(receipt['libraries'])
    for name in ('libSDL2_image-2.0.so.0','libSDL2-2.0.so.0'):
        aarch64(libraries/name)
        expected=next(r['sha256'] for r in receipt['inputs'] if r.get('name')==name)
        if sha(libraries/name)!=expected:raise ValueError('Prepared target library changed: '+name)
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['aarch64-linux-gnu-gcc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I'+str(includes),
        str(ROOT/'tools/slotlaunch/slot-launch.c'),'-L'+str(libraries),'-Wl,--allow-shlib-undefined',
        '-l:libSDL2_image-2.0.so.0','-l:libSDL2-2.0.so.0','-lm','-o',str(output)],check=True)
    subprocess.run(['aarch64-linux-gnu-strip',str(output)],check=True);aarch64(output)
    result=dict(sourcePin=receipt['sourcePin'],sha256=sha(output),buildInputsSha256=sha(workspace/'build-inputs.json'),
        sourceHashes={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'tools/slotlaunch').iterdir()) if p.suffix in ('.c','.h')},
        state='built-not-installed')
    output.with_suffix(output.suffix+'.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.workspace,a.output),indent=2))
if __name__=='__main__':main()
