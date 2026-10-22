"""Device-side private cartridge/GPU validation, never installs theme assets (MIT).

Run against a staged, hash-verified job directory. Uses the editor-upload lock,
a fresh standard snapshot and saved preview environment. All rendering output
and model alternatives remain private; the installed frontend binary is unchanged.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import time
sys.path.insert(0,'/userdata/system/slot-dev')
import esdev
from session_data import Snapshot,digest

SYSTEMS=('nds','gba','nes','gb','gbc','md')
THEME=Path('/userdata/themes/art-book-slot/_slot')


def run(job):
    config=json.loads((job/'request.json').read_text())
    systems=config.get('systems',SYSTEMS);aspects=config.get('aspects',('3:2','4:3'))
    variants=config.get('variants',('selected','previous'))
    if any(s not in SYSTEMS for s in systems) or any(a not in ('3:2','4:3') for a in aspects) or any(v not in ('selected','previous') for v in variants):
        raise ValueError('Invalid private validation selection')
    snap=Snapshot('/userdata',config['session']);stopped=False;backed=False;report={}
    environment=os.environ.copy();error=None
    def status(state,message,**extra):
        temp=job/'status.tmp';temp.write_text(json.dumps(dict(state=state,message=message,**extra),indent=2)+'\n');temp.replace(job/'status.json')
    lock=open('/userdata/system/slot-dev/editor-upload.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        status('busy','An editor upload is running; device left unchanged.');return
    try:
        for name,entry in config['files'].items():
            p=PurePosixPath(name);target=job/name
            if p.is_absolute() or '..' in p.parts or not target.resolve().is_relative_to(job):raise ValueError('Invalid private payload')
            if target.stat().st_size!=entry['bytes'] or digest(target)!=entry['sha256']:raise ValueError('Payload mismatch: '+name)
        pid=esdev.es_pid()
        if not pid or json.loads(esdev.api('/runningGame'))!={'msg':'NO GAME RUNNING'}:raise RuntimeError('A game may be running; device left unchanged.')
        saved={}
        for raw in Path('/proc/'+str(pid)+'/environ').read_bytes().split(b'\0'):
            name,sep,value=raw.partition(b'=')
            if sep and name.startswith((b'SLOT_',b'SDL_')):saved[name.decode()]=value.decode()
        environment.update(saved);report.update(preview_environment=saved,frontend_sha256=digest(Path('/usr/bin/emulationstation')))
        if json.loads(esdev.api('/runningGame'))!={'msg':'NO GAME RUNNING'}:raise RuntimeError('A game started; device left unchanged.')
        status('running','Taking a fresh verified device snapshot.')
        stopped=True;esdev.stop()
        if esdev.es_pid():raise RuntimeError('Frontend did not stop')
        report['snapshot_counts']=snap.backup();backed=True;report['snapshot']=str(snap.directory)
        prepared=job/'prepared';prepared.mkdir()
        for p in (THEME/'tabletop').iterdir():
            if p.name!='layouts':(prepared/p.name).symlink_to(p,target_is_directory=p.is_dir())
        layouts=prepared/'layouts';layouts.mkdir()
        for p in (snap.directory/'runtime/themes/art-book-slot/_slot/tabletop/layouts').glob('*.scene'):shutil.copy2(p,layouts/p.name)
        report['layouts']={p.name:digest(p) for p in layouts.iterdir()}
        for variant in ('selected','previous'):
            root=job/variant
            for p in THEME.iterdir():
                if p.name!='consoles':(root/p.name).symlink_to(p,target_is_directory=p.is_dir())
            consoles=root/'consoles'
            for p in (THEME/'consoles').iterdir():
                dest=consoles/p.name
                if p.name not in SYSTEMS:
                    dest.symlink_to(p,target_is_directory=p.is_dir());continue
                for source in p.iterdir():
                    if source.name.startswith('media') and not source.name.startswith('media-ea'):continue
                    (dest/source.name).symlink_to(source,target_is_directory=source.is_dir())
        binary=job/'probe-arm64';binary.chmod(0o755);report['probe_sha256']=digest(binary)
        results=[]
        for system in systems:
            tv='panasonic' if system in ('nes','md') else 'pvm'
            for aspect in aspects:
                for variant in variants:
                    status('running','Testing %s %s (%s)'%(system.upper(),aspect,variant),completed=len(results),snapshot=report['snapshot'])
                    dest=job/'results'/(system+'-'+aspect.replace(':','')+'-'+variant);dest.mkdir(parents=True)
                    env=dict(os.environ,SLOT_SCENE_ASPECT=aspect)
                    # Explicit A/B switches only affect this private probe process.
                    for name,value in config.get('probe_environment',{}).items():
                        if name!='SLOT_SCENE_CULL_CARTRIDGES' or value not in ('0','1'):raise ValueError('Unsupported probe switch')
                        if value=='1':env[name]=value
                        else:env.pop(name,None)
                    command=[str(binary),str(job/variant),str(prepared),str(dest),system,tv,str(job/'faces'/system)+'/',
                             'benchmark' if variant=='selected' else 'timing']
                    started=time.monotonic()
                    r=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
                    log=r.stdout.decode(errors='replace');(dest/'probe.log').write_text(log)
                    timing=re.search(r'gpu_scene_ms n=(\d+) p50=([\d.]+) p95=([\d.]+) max=([\d.]+)',log)
                    result=dict(system=system,tv=tv,aspect=aspect,variant=variant,exit=r.returncode,seconds=time.monotonic()-started)
                    if timing:result['gpu_ms']=dict(n=int(timing[1]),p50=float(timing[2]),p95=float(timing[3]),max=float(timing[4]))
                    results.append(result)
                    (job/'results.json').write_text(json.dumps(results,indent=2)+'\n')
                    if r.returncode or not timing:raise RuntimeError('Probe failed: %s %s %s; inspect private log'%(system,aspect,variant))
        report['results']=results
    except BaseException as ex:error=str(ex)
    finally:
        if backed:
            try:
                report['audit']=snap.audit(True)
                if any(v['changed'] or v['new'] for v in report['audit'].values()):
                    report['restore']=snap.restore(True);report['audit']=snap.audit(True)
                    if any(v['changed'] or v['new'] for v in report['audit'].values()):raise RuntimeError('Snapshot audit did not return clean')
            except BaseException as ex:error=(error+'; ' if error else '')+'Audit: '+str(ex)
        if stopped:
            status('running','Reopening the same frontend preview.')
            try:
                if not esdev.es_pid():
                    subprocess.Popen(['setsid',esdev.INIT,'start'],env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                esdev.wait(45)
                report['frontend_after_sha256']=digest(Path('/usr/bin/emulationstation'))
                if report['frontend_after_sha256']!=report['frontend_sha256']:raise RuntimeError('Frontend binary changed')
                report['frontend_ready']=bool(esdev.es_pid())
            except BaseException as ex:error=(error+'; ' if error else '')+'Restart: '+str(ex)
        (job/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        status('failed' if error else 'complete',error or 'Private validation complete; installed setup unchanged.',report=report)
        lock.close()


if __name__=='__main__':run(Path(sys.argv[1]).resolve())
