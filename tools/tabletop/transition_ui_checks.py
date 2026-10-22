"""Small, idempotent UI checks inside the active temporary trial transaction."""
import argparse
import json
import os
import subprocess
from tools.tabletop.device_probe import Remote, ROOT

BASE = ROOT/os.environ.get('SLOT_TRANSITION_BUILD', 'build/system-switch-implementation-20261020')

PRELUDE = r'''
import hashlib,json,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,'/userdata/system/slot-dev')
import esdev
job=Path(JOB)
status=json.loads((job/'status.json').read_text())
assert status['state']=='ready','Trial is not ready'
assert hashlib.sha256(Path('/usr/bin/emulationstation').read_bytes()).hexdigest()==status['candidate_sha256'],'Different frontend is running'
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'},'A game is running'
screens=job/'screens';screens.mkdir(exist_ok=True)
def shot(name):subprocess.run(['knulli-screenshot',str(screens/(name+'.png'))],check=True,stdout=subprocess.DEVNULL)
def events():
    p=job/'stream.tsv'
    return [line.split('\t') for line in p.read_text().splitlines()] if p.is_file() else []
def latest():
    requests=[e for e in events() if e[1]=='request']
    return requests[-1] if requests else None
def settled(timeout=18):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        req=latest()
        if req and any(e[1] in ('settled','items') and e[2]==req[2] for e in events()):return req
        time.sleep(.15)
    raise RuntimeError('Latest system did not settle')
def memory():
    pid=esdev.es_pid()
    return {line.split(':')[0]:line.split(':')[1].strip() for line in Path('/proc/'+pid+'/status').read_text().splitlines() if line.startswith(('VmRSS:','VmHWM:','Threads:'))}
def go(system):
    # Standard non-tabletop system views do not render/advance a hidden native
    # flight. Wait for a NEW native request, rather than waiting on that hidden
    # scene while traversing ports/utilities between PICO-8 and NES.
    for i in range(20):
        previous=latest();esdev.press(['r2']);end=time.monotonic()+1
        while latest()==previous and time.monotonic()<end:time.sleep(.1)
        if latest()!=previous:
            req=settled()
            if req[3].startswith(system+'|'):return req
    raise RuntimeError('Requested tabletop system was not reached')
'''

STEPS = {
    'whimsy': r'''
go('gbc');time.sleep(.5);shot('gbc-upright-selected')
esdev.press(['right']);time.sleep(.12);shot('gbc-hover-moving')
time.sleep(1);shot('gbc-hover-settled')
def burst(prefix):
    start=time.monotonic();esdev.press(['r2'])
    for mark in (.15,.3,.45,.6,.8,1.,1.2,1.4,1.65,1.95,2.3,2.7):
        time.sleep(max(0,start+mark-time.monotonic()));shot(prefix+'-'+str(mark))
    return settled()
same=burst('same-tv-wave')
go('nes');changed=burst('changed-tv-wave')
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
result=dict(uprightHoverCaptured=True,sameTV=same,changedTV=changed,noGame=True,memory=memory())
''',
    'initial': "shot('initial')\nresult=dict(captured='initial.png',noGame=True)",
    'smoke': r'''
esdev.press(['hold:a:350']);time.sleep(2)
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'},'First A launched instead of inserting'
shot('inserted')
esdev.press(['up']);time.sleep(1.7);shot('ejected')
esdev.press(['r3']);time.sleep(.4);shot('carousel')
esdev.press(['b']);time.sleep(.4);shot('table-return')
esdev.press(['l3']);time.sleep(.7);shot('inspection')
esdev.press(['b']);time.sleep(.7);shot('inspection-return')
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
result=dict(firstAHeldInsertsOnly=True,ejection=True,r3CarouselAndB=True,inspectionAndB=True,noGame=True)
''',
    'next': r'''
esdev.press(['r2']);time.sleep(1)
shot('next-'+str(time.time_ns()))
result=dict(direction='next',noGame=json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'},events=(job/'stream.tsv').read_text().splitlines()[-8:])
''',
    'rapid': r'''
for i in range(16):esdev.press(['r2' if i%3 else 'l2'])
time.sleep(3);go('snes')
shot('rapid-final')
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
result=dict(rapidRequests=16,noGame=True,events=(job/'stream.tsv').read_text().splitlines()[-12:])
''',
    'walk': r'''
samples=[]
for i in range(22):
    assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
    previous=latest();esdev.press(['r2'])
    end=time.monotonic()+2
    while latest()==previous and time.monotonic()<end:time.sleep(.1)
    req=settled() if latest()!=previous else None
    time.sleep(1.2)
    sample=dict(index=i,request=req,memory=memory())
    samples.append(sample);(job/'walk-progress.json').write_text(json.dumps(samples,indent=2))
    if i<11:shot('walk-'+str(i))
result=dict(samples=samples,noGame=True)
''',
    'launch': r'''
import urllib.request
go('snes')
games=json.loads(esdev.api('/systems/snes/games',timeout=8))
choices=[g for g in games if Path(g['path']).is_file() and Path(g['path']).suffix.lower() in ('.sfc','.smc') and Path(g['path']).stat().st_size>32768]
assert choices,'No real SNES test game'
game=sorted(choices,key=lambda g:g['path'])[0];before=int(game.get('playcount','0') or '0')
(job/'launch-selection.json').write_text(json.dumps(game,indent=2))
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
request=urllib.request.Request('http://127.0.0.1:1234/launch',data=game['path'].encode(),headers={'Content-Type':'text/plain'},method='POST')
with urllib.request.urlopen(request,timeout=5) as response:response.read()
end=time.monotonic()+25;running={}
while time.monotonic()<end:
    running=json.loads(esdev.api('/runningGame'))
    if running.get('path')==game['path']:break
    assert running=={'msg':'NO GAME RUNNING'},'Unexpected game; leave it running'
    time.sleep(.25)
assert running.get('path')==game['path'],'Ordinary validated launch did not start'
time.sleep(3);shot('game-running');during=memory()
assert json.loads(esdev.api('/runningGame')).get('path')==game['path'],'Game changed; leave it running'
esdev.api('/emukill',timeout=5)
end=time.monotonic()+35
while time.monotonic()<end:
    if json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}:break
    time.sleep(.25)
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'},'Game did not return'
time.sleep(9);shot('game-return')
after=next(g for g in json.loads(esdev.api('/systems/snes/games',timeout=8)) if g['path']==game['path'])
assert int(after.get('playcount','0'))==before+1,'Launch ownership/playcount was not exactly once'
esdev.press(['r2']);time.sleep(.4);settled();shot('switch-after-return')
result=dict(path=game['path'],before=before,after=int(after['playcount']),exactlyOnce=True,returned=True,switchAfterReturn=True,duringMemory=during,afterMemory=memory())
'''
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=STEPS)
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    if args.tag and not args.tag.replace('-', '').isalnum():
        raise ValueError('Use a short alphanumeric tag')
    job = json.loads((BASE/'trial-job.json').read_text())['job']
    name = args.step+('-'+args.tag if args.tag else '')
    code = PRELUDE.replace('JOB', repr(job))
    code += '\nrecord=job/'+repr(name+'-checks.json')+'\n'
    code += "if record.is_file():\n    print(record.read_text());sys.exit(0)\n"
    code += "record.write_text(json.dumps(dict(state='running')))\n"
    code += STEPS[args.step]+'\n'
    code += "result['state']='complete';record.write_text(json.dumps(result,indent=2));print(json.dumps(result))\n"
    try:
        print(Remote().python(code, 420 if args.step=='walk' else 150).decode())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf8', 'replace')) from None


if __name__ == '__main__':
    main()
