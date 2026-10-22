"""Hash-pinned public asset substitutions; development originals stay untouched."""
import copy
import hashlib
import json
from pathlib import Path

CONFIG = 'release/asset-derivatives.json'


def load(root):
    path = Path(root) / CONFIG
    return json.loads(path.read_text(encoding='utf-8'))['files'] if path.exists() else []


def select(root, selected, config, safe_file, digest):
    """Use approved derivatives, or an already-corrected public checkout."""
    config = copy.deepcopy(config)
    if load(root) and CONFIG not in selected:
        raise ValueError('Derivative policy must be included in the publication allowlist')
    seen = set()
    for record in load(root):
        name = record['destination']
        if not record['source'].startswith('assets/publication-derivatives/'):
            raise ValueError('Derivative source must be under assets/publication-derivatives: ' + name)
        if name in seen or name not in selected:
            raise ValueError('Duplicate/unselected derivative destination: ' + name)
        seen.add(name)
        previous, asset = selected[name]
        current = digest(previous)
        if current == record['sha256']:
            source = previous
        elif current == record['originalSha256']:
            source = safe_file(root, record['source'])
            if digest(source) != record['sha256']:
                raise ValueError('Derivative hash differs: ' + name)
        else:
            raise ValueError('Unreviewed derivative input: ' + name)
        if asset:
            replacement = dict(asset, sha256=record['sha256'], bytes=source.stat().st_size)
            config['assets'] = [replacement if a['destination'] == name else a for a in config['assets']]
            asset = replacement
        selected[name] = source, asset
    return selected, config


def approved_albedo(root, name, rebuilt):
    """A public source import may not restore removed art or change other texels.

    Uses the shipped reviewed image; never needs an image-generation service.
    Development checkouts have no publication manifest and keep their originals.
    """
    root = Path(root)
    if not (root / 'PUBLICATION_MANIFEST.json').exists():
        return rebuilt
    record = next((r for r in load(root) if r['destination'] == name), None)
    if not record:
        return rebuilt
    path = root / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Reviewed public albedo missing or altered: ' + name)
    import numpy as np
    from PIL import Image
    approved = np.array(Image.open(path).convert('RGBA'))
    if approved.shape != rebuilt.shape or 'pixelBox' not in record:
        raise ValueError('Public albedo layout differs: ' + name)
    different = np.any(approved != rebuilt, axis=2)
    x0, y0, x1, y1 = record['pixelBox']
    different[y0:y1, x0:x1] = False
    if different.any():
        raise ValueError('Source rebuild changes unreviewed albedo pixels: ' + name)
    return approved
