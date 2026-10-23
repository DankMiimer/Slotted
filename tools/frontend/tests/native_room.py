"""Run real native room/UI captures in an isolated Linux host fixture; no device access."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image,ImageChops
from tools.frontend.tests.room_fixture import make
from tools.frontend.prepare_build import sha

ROOT=Path(__file__).resolve().parents[3]

def run(build,source,output,tv='panasonic',width=720,script=None):
    build=Path(build).resolve();source=Path(source).resolve();output=Path(output).absolute()
    if width not in (640,720):raise ValueError('Use 640x480 or 720x480')
    if output.exists():raise FileExistsError('Use a fresh capture folder')
    receipt=json.loads((build/'host-build.json').read_text())
    binary=build/'frontend/emulationstation'
    if sha(binary)!=receipt['binarySha256']:raise ValueError('Host binary receipt differs')
    script=Path(script or ROOT/'tools/frontend/tests/room-regression-script.txt').resolve()
    output.mkdir(parents=True)
    fixture=make(output/'fixture',source,build/'frontend',tv)
    env=dict(os.environ,SDL_VIDEODRIVER='offscreen',EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',SDL_AUDIODRIVER='dummy',
        LD_LIBRARY_PATH=':'.join(receipt['runtimeDirectories']),HOME='/userdata',
        SLOT_TABLETOP_ASSETS=str(source/'assets/tabletop'),SLOT_ROOM_TEST_OUTPUT=str(output),SLOT_ROOM_TEST_SCRIPT=str(script))
    with (output/'stdout.log').open('wb') as log:
        result=subprocess.run(['sh',str(ROOT/'tools/frontend/tests/sandbox.sh'),str(output/'fixture'),
            str(binary),'--resolution',str(width),'480','--windowed','--no-splash'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    (output/'fixture.json').write_text(json.dumps(dict(**fixture,width=width,height=480,binarySha256=sha(binary),exit=result.returncode),indent=2)+'\n')
    result.check_returncode()
    frames=list(csv.DictReader((output/'frames.tsv').open(),delimiter='\t'))
    if not frames or any(row['glerror']!='0' for row in frames):raise ValueError('Native render reported an OpenGL error')
    shots=[]
    for line in script.read_text().splitlines():
        fields=line.split()
        if len(fields)==3 and fields[1]=='shot':
            name=fields[2]
            if not re.fullmatch(r'[a-z0-9-]+',name):raise ValueError('Use portable capture names')
            for kind,size in [('room',(width,480)),('ui',(640,480))]:
                path=output/(name+'-'+kind+'.bmp')
                with Image.open(path) as image:
                    if image.size!=size:raise ValueError('Capture dimensions differ: '+path.name)
                    image.save(path.with_suffix('.png'))
            shots.append(dict(name=name,frame=int(fields[0]),**{k:v for k,v in frames[-1].items() if k=='system'}))
    proof=dict(state='host-native-captured',tv=tv,retroCabinetFallback=tv=='retro',width=width,height=480,
        nativeAudioVideo=False,glErrors=0,frames=len(frames),shots=shots,
        scriptSha256=sha(script),binarySha256=sha(binary))
    (output/'capture.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof

def compare(actual,baseline,output):
    """Exact RGB comparison. No automatic baseline updates or broad image tolerances."""
    actual=Path(actual);baseline=Path(baseline);output=Path(output)
    if output.exists():raise FileExistsError('Use a fresh comparison folder')
    a=json.loads((actual/'capture.json').read_text());b=json.loads((baseline/'capture.json').read_text())
    if any(a[k]!=b[k] for k in ('tv','width','height','scriptSha256','nativeAudioVideo')):raise ValueError('Capture conditions differ')
    output.mkdir(parents=True);rows=[]
    for shot in a['shots']:
        for kind in ('room','ui'):
            name=shot['name']+'-'+kind+'.png'
            with Image.open(actual/name) as left,Image.open(baseline/name) as right:
                if left.size!=right.size:raise ValueError('Capture dimensions differ')
                difference=ImageChops.difference(left.convert('RGB'),right.convert('RGB'))
                r,g,b=difference.split();changed=ImageChops.lighter(ImageChops.lighter(r,g),b)
                count=changed.width*changed.height-changed.histogram()[0]
                rows.append(dict(file=name,changedPixels=count,bounds=difference.getbbox()))
                if count:difference.save(output/name)
    result=dict(passed=all(row['changedPixels']==0 for row in rows),comparison='exact-rgb-no-masks',images=rows)
    (output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path);p.add_argument('--source',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--tv',default='panasonic');p.add_argument('--width',type=int,default=720)
    p.add_argument('--script',type=Path);p.add_argument('--compare',type=Path);p.add_argument('--baseline',type=Path)
    a=p.parse_args()
    if a.compare:
        if not a.baseline:p.error('--compare requires --baseline')
        result=compare(a.compare,a.baseline,a.output)
    else:
        if not a.build or not a.source:p.error('Provide --build and --source')
        result=run(a.build,a.source,a.output,a.tv,a.width,a.script)
    print(json.dumps(result,indent=2))
    if result.get('passed') is False:raise SystemExit(1)
