"""Required runtime files and scene references; no host or device side effects."""
import json
from pathlib import PurePosixPath

MODELS=('gb','gbc','gba','nds','psp','pico8','snes','snes-us','nes','n64','md','md-jp','psx','dreamcast')
SCENES=('table','wooden-table','tv-stand','panasonic','pvm','oldtv','retro')
REQUIRED=('theme.xml','_slot/consoles/specs.json','_slot/launch/slot-launch')+tuple(
    '_slot/tabletop/'+name+'/scene.txt' for name in SCENES)+tuple(
    '_slot/consoles/'+name+'/model.mesh' for name in MODELS)+tuple(
    '_slot/consoles/'+name+'/media.mesh' for name in MODELS if name not in ('psx','dreamcast'))

def validate(names,read):
    """Refuse missing models or referenced TV/table parts before any install writes."""
    names=set(names);missing=set(REQUIRED)-names
    if missing:raise ValueError('Incomplete standalone runtime: '+', '.join(sorted(missing)))
    specs=json.loads(read('_slot/consoles/specs.json'))
    if not set(MODELS)<=set(specs):raise ValueError('Standalone console registration is incomplete')
    for scene in SCENES:
        base='_slot/tabletop/'+scene+'/'
        rows=read(base+'scene.txt').decode('utf-8').splitlines()
        header=rows[0].split() if rows else []
        if len(header)!=2 or header[0]!='SCTABLETOP1' or int(header[1])<=0 or len(rows)!=3+int(header[1]):
            raise ValueError('Incomplete standalone scene: '+scene)
        for row in rows[3:]:
            fields=row.split()
            if len(fields)!=3:raise ValueError('Invalid standalone scene part: '+scene)
            for name in fields[:2]:
                if name=='-':continue
                path=PurePosixPath(name)
                if len(path.parts)!=1 or path.name!=name or any(c in name for c in ':\\'):
                    raise ValueError('Unsafe standalone scene reference: '+name)
                if base+name not in names:raise ValueError('Missing standalone scene part: '+base+name)
