"""Read image dimensions without decoding; prepared .png files may be JPEG."""
import json
from pathlib import Path
import struct


def dimensions(path):
    with Path(path).open('rb') as source:
        header = source.read(24)
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            width, height = struct.unpack('>II', header[16:24])
            return 'png', width, height
        if header[:2] != b'\xff\xd8':
            raise ValueError('Unsupported image signature: ' + str(path))
        source.seek(2)
        while True:
            marker = source.read(1)
            if not marker:
                raise ValueError('JPEG dimensions not found: ' + str(path))
            if marker != b'\xff':
                continue
            marker = source.read(1)
            while marker == b'\xff':
                marker = source.read(1)
            if not marker:
                break
            marker = marker[0]
            if marker in (0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
                continue
            size = struct.unpack('>H', source.read(2))[0]
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                height, width = struct.unpack('>HH', source.read(5)[1:5])
                return 'jpeg', width, height
            if size < 2:
                break
            source.seek(size - 2, 1)
    raise ValueError('Invalid image header: ' + str(path))


def inventory(root):
    root = Path(root)
    rows = []
    for folder in ('tabletop', 'consoles', 'local-models'):
        for path in sorted((root / folder).rglob('*.png')):
            kind, width, height = dimensions(path)
            rows.append(dict(path=path.relative_to(root).as_posix(), format=kind,
                width=width, height=height, rgbaBytes=width*height*4, fileBytes=path.stat().st_size))
    return rows


if __name__ == '__main__':
    import sys
    print(json.dumps(inventory(sys.argv[1]), indent=2))
