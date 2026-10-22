"""Compile/read-only-check navigation and world math against every saved profile.

Run with Python and g++ (for example inside WSL). All generated scene derivatives
and the test executable live in a temporary directory; source profiles are hashed
again after the check. Does not connect to or modify the device.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.tabletop.editor.server import native_text


def run():
    sources = sorted((ROOT / 'scene-layouts').glob('*.json'))
    originals = {path: path.read_bytes() for path in sources}
    with tempfile.TemporaryDirectory(prefix='slotted-world-') as temporary:
        folder = Path(temporary)
        scenes = []
        for path, raw in originals.items():
            value = json.loads(raw)
            # Future home/world/screen scenes have their own schemas.
            if value.get('system') is None:
                continue
            scene = folder / (path.stem + '.scene')
            scene.write_text(native_text(value), encoding='utf-8')
            scenes.append(scene)
        if not scenes:
            raise RuntimeError('No saved console profiles to check')
        executable = folder / 'world-navigation'
        subprocess.run(['g++', '-O2', '-std=c++14', '-Wall', '-Wextra',
                        '-I' + str(ROOT / 'tools/frontend/overlay/es-app/src/components'),
                        str(ROOT / 'tools/frontend/tests/world_navigation.cpp'),
                        '-o', str(executable)], check=True)
        subprocess.run([str(executable), *map(str, scenes)], check=True)
    for path, raw in originals.items():
        if hashlib.sha256(raw).digest() != hashlib.sha256(path.read_bytes()).digest():
            raise RuntimeError('Source profile changed during read-only check: ' + str(path))
    print('Saved profile SHA-256 checks unchanged; no device access.')


if __name__ == '__main__':
    run()
