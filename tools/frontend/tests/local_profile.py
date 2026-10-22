"""Exercise local profile selection and safe fallback in the real GLES bridge."""
import os,shutil,struct,subprocess,sys,tempfile
from pathlib import Path

probe,assets=map(Path,sys.argv[1:])
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    for p in assets.iterdir():
        if p.name!='local-models':(root/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
    local=root/'local-models/consoles/gba';local.mkdir(parents=True)
    original=assets/'local-models/consoles/gba'
    for name in ('model.mesh','model.pose','paint.mask'):shutil.copy2(original/name,local/name)
    pose=(local/'model.pose').read_bytes();mesh=(local/'model.mesh').read_bytes()
    cases={'valid':(pose,mesh,1),'truncated':(pose[:-1],mesh,0),
           'bad-magic':(b'XXXXXXXX'+pose[8:],mesh,0),
           'nonfinite':(pose[:8]+struct.pack('<f',float('nan'))+pose[12:],mesh,0),
           'wrong-mesh':(pose,mesh[:20]+struct.pack('<f',1.25)+mesh[24:],0),
           'wrong-registration':(pose[:-8]+b'\0'*8,mesh,0)}
    for name,(registration,geometry,expected) in cases.items():
        (local/'model.pose').write_bytes(registration);(local/'model.mesh').write_bytes(geometry)
        env=dict(os.environ,SLOT_EXPECT_LOCAL=str(expected))
        run=subprocess.run([str(probe),str(root),str(root/'probe.bmp'),'gba','front'],env=env,capture_output=True,text=True)
        if run.returncode:raise AssertionError(name+'\n'+run.stdout+run.stderr)
        print('PASS',name,flush=True)
    (local/'model.pose').write_bytes(pose);(local/'model.mesh').write_bytes(mesh)
    for finish,colour in [('realistic','red'),('cel','blue')]:
        env=dict(os.environ,SLOT_EXPECT_LOCAL='1',SLOT_MODEL_STYLE=finish,SLOT_CONSOLE_COLOR=colour)
        run=subprocess.run([str(probe),str(root),str(root/'probe.bmp'),'gba','front'],env=env,capture_output=True,text=True)
        if run.returncode:raise AssertionError(finish+'/'+colour+'\n'+run.stdout+run.stderr)
        print('PASS',finish,colour,flush=True)
