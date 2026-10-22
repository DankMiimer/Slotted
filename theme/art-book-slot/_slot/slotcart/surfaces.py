"""Publish baked variant identity for the selected video's shader.

The frontend reads marker existence through a supported FLOAT binding, not JSON.
Only one selected video player exists. This also migrates unchanged libraries
from the cache manifest, without re-rendering or scraping their printed labels.
"""
import argparse
import json
from pathlib import Path

SLOT = Path(__file__).resolve().parents[1]


def catalogue():
    path = SLOT/'video-profiles.json'
    return json.loads(path.read_text()) if path.exists() else {}


def write_variant(out, outline):
    out = Path(out)
    for name in catalogue():
        marker = out.with_name(out.stem+'.slot-profile-'+name)
        if name == outline:
            out.parent.mkdir(parents=True,exist_ok=True)
            marker.touch(exist_ok=True)
        else:
            marker.unlink(missing_ok=True)


def migrate(root):
    count = 0
    for manifest in Path(root).glob('**/media/slotcarts/.slotcart.json'):
        for stem,key in json.loads(manifest.read_text(encoding='utf-8')).items():
            if Path(stem).name != stem or stem in ('.','..'):
                raise ValueError('Unsafe cached stem')
            outline = json.loads(key)[1]
            write_variant(manifest.parent/(stem+'.png'),outline)
            count += outline in catalogue()
    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roms',type=Path,default=Path('/userdata/roms'))
    print('%d variant markers ready' % migrate(parser.parse_args().roms))
