"""Textured sidecar acceptance and safe fallback in the real GLES bridge.

    sh run_probe.sh python3 textured_fallback.py PROBE SLOT [MODEL] [PART]

Each damaged or stale sidecar/albedo must keep the legacy vertex-colour mesh
rendering (scene opens, visible pixels, GL error 0) and log the rejection.
"""
import io, os, struct, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

probe, assets = map(Path, sys.argv[1:3])
model = sys.argv[3] if len(sys.argv) > 3 else 'gbc'
part = sys.argv[4] if len(sys.argv)>4 else 'model'
log = Path('/tmp/art-book-slot-launch/animation.log')


def run(root, env=None):
    before = log.read_text() if log.exists() else ''
    result = subprocess.run([str(probe), str(root), str(root / 'probe.bmp'), model, 'front'],
                            env=dict(os.environ, **(env or {})), capture_output=True, text=True)
    if result.returncode or 'GL error 0' not in result.stdout:
        raise AssertionError(result.stdout + result.stderr)
    added = log.read_text()[len(before):]
    return added.count('validated UV/albedo'), 'invalid texture sidecar' in added


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for p in assets.iterdir():
        if p.name != 'consoles':
            (root / p.name).symlink_to(p.resolve(), target_is_directory=p.is_dir())
    for p in (assets / 'consoles').iterdir():
        target = root / 'consoles' / p.name
        if p.name != model:
            target.parent.mkdir(exist_ok=True)
            target.symlink_to(p.resolve(), target_is_directory=p.is_dir())
    folder = root / 'consoles' / model
    folder.mkdir(parents=True)
    source = assets / 'consoles' / model
    for p in source.iterdir():
        if p.name not in (part+'.texture', part+'.albedo.png'):
            (folder / p.name).symlink_to(p.resolve())
    texture = (source / (part+'.texture')).read_bytes()
    albedo = (source / (part+'.albedo.png')).read_bytes()
    image = Image.open(source / (part+'.albedo.png')).convert('RGBA')

    def png(changed):
        stream = io.BytesIO(); changed.save(stream, 'PNG'); return stream.getvalue()

    altered = image.copy(); altered.putpixel((5, 5), (1, 2, 3, 4))
    header = 8 + 4 * 4 + 8 * 3
    cases = {
        'valid': (texture, albedo, True),
        'missing-sidecar': (None, albedo, False),
        'truncated': (texture[:-1], albedo, False),
        'bad-magic': (b'SCTEX001' + texture[8:], albedo, False),
        'stale-vertex-hash': (texture[:24] + bytes([texture[24] ^ 1]) + texture[25:], albedo, False),
        'nonfinite-luma': (texture[:20] + struct.pack('<f', float('nan')) + texture[24:], albedo, False),
        'uv-out-of-range': (texture[:header] + struct.pack('<f', 1.5) + texture[header + 4:], albedo, False),
        'missing-albedo': (texture, None, False),
        'changed-albedo-pixel': (texture, png(altered), False),
        'resized-albedo': (texture, png(image.resize((image.width // 2, image.height // 2))), False),
    }
    baseline=0
    for name, (sidecar, picture, expected) in cases.items():
        for path, data in ((folder / (part+'.texture'), sidecar), (folder / (part+'.albedo.png'), picture)):
            if path.exists() or path.is_symlink():
                path.unlink()
            if data is not None:
                path.write_bytes(data)
        accepted, rejected = run(root)
        if name=='valid':baseline=accepted
        textured=accepted==baseline
        if textured != expected or (not expected and name != 'missing-sidecar' and not rejected):
            raise AssertionError(f'{name}: textured={textured} rejected={rejected}')
        print('PASS', name, 'textured' if textured else 'legacy vertex colours', flush=True)
    (folder / (part+'.texture')).write_bytes(texture); (folder / (part+'.albedo.png')).write_bytes(albedo)
    for finish, colour in (('realistic', 'red'), ('cel', 'blue'), ('realistic', 'original')):
        accepted, _ = run(root, dict(SLOT_MODEL_STYLE=finish, SLOT_CONSOLE_COLOR=colour))
        assert accepted==baseline and accepted>0, (finish, colour)
        print('PASS', finish, colour, flush=True)
