"""Package only the presentation's owned runtime paths. Does not deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]
THEME=ROOT/'theme/art-book-slot'
OWNED=('theme.xml','_slot/shelf-common.xml','_slot/slot-interaction.xml','_slot/status.xml','_slot/MODEL_CREDITS.txt',
       '_slot/launch/common.sh','_slot/launch/frontend-owned.sh')


def package(output):
    files=[THEME/path for path in OWNED]
    files += sorted(path for path in (THEME/'_slot/stage').rglob('*')
                    if path.is_file() and path.suffix in ('.png','.json','.xml'))
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    report={}
    with tarfile.open(output,'w') as archive:
        for path in files:
            relative=path.relative_to(THEME).as_posix()
            report[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
            info=archive.gettarinfo(str(path),arcname=relative)
            info.uid=info.gid=0;info.uname=info.gname='root'
            info.mode=0o755 if path.suffix=='.sh' else 0o644
            with path.open('rb') as stream:archive.addfile(info,stream)
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Packaged',len(files),'owned files:',output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    package(parser.parse_args().output)
