"""Read-only audit of display pixel aspect for previews referenced by gamelists."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from prepare_video import probe


def audit(root):
    import xml.etree.ElementTree as E
    paths = set()
    for gamelist in Path(root).glob('*/gamelist.xml'):
        for video in E.parse(gamelist).iter('video'):
            if video.text:
                path = Path(video.text)
                paths.add((path if path.is_absolute() else gamelist.parent/path).resolve())
    def inspect(path):
        if not path.is_file():
            return 'missing',None
        try:
            width,height,sar = probe(path)
            return 'checked',dict(path=str(path),sar=str(sar),width=width,height=height) if sar!=1 else None
        except Exception as error:
            return 'failed',dict(path=str(path),error=str(error))
    report = dict(referenced=len(paths),checked=0,missing=0,failed=0,anamorphic=[],errors=[])
    with ThreadPoolExecutor(max_workers=3) as pool:
        for state,entry in pool.map(inspect,sorted(paths)):
            report[state]+=1
            if entry is not None:
                report['anamorphic' if state=='checked' else 'errors'].append(entry)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roms',type=Path)
    parser.add_argument('report',type=Path)
    options = parser.parse_args()
    result = audit(options.roms)
    options.report.write_text(json.dumps(result,indent=2))
    print(json.dumps({key:len(value) if isinstance(value,list) else value for key,value in result.items()}))
