"""RETROvision branding for the prepared Panasonic, Sony PVM and Retro TVs.

The user's choice (24 Oct 2026): no Panasonic or Sony marks on the TV models; the Old
TV's own RETROvision print (pibanezl, CC BY 4.0) goes where they were. This edits
freshly prepared runtime folders (tools/tabletop/prepare_assets.py output); the creators'
source models are not changed by it.

    python -m tools.tabletop.tv_branding apply build/tabletop/assets [--tv pvm ...]
    python -m tools.tabletop.tv_branding check build/tabletop/assets

- panasonic: the separate raised "Logo.001" part is omitted; a 2-triangle plate 0.3 mm
  in front of the panel carries an 18 mm gold RETROvision on the panel's own texture.
- pvm: the raised SONY letters are flattened onto their backing and painted bezel grey
  with the backing; a white RETROvision is painted through the UVs; the TRINITRON badge
  and the brand words on the rear label are removed.
- retro: the small "Panasonic" print is cloned out and an olive RETROvision painted in.
`apply` refuses a folder that is not the expected unbranded model, or already branded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from PIL import Image, ImageFilter

TVS = ('panasonic', 'pvm', 'retro')
MARK = 'RETROvision branding (2026-10-24): '


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tiled(sample, size):
    """A texture sample repeated over size (w, h), keeping its grain."""
    w, h = size
    return np.tile(sample, (-(-h // sample.shape[0]), -(-w // sample.shape[1]), 1))[:h, :w]


def paint(pixels, mask, fill):
    """Feathered paste of fill where mask is set (both full-image arrays)."""
    alpha = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)), float)[..., None] / 255
    alpha = np.maximum(alpha, mask[..., None].astype(float))
    return (pixels * (1 - alpha) + fill * alpha).round().astype(np.uint8)


def box_mask(shape, boxes):
    mask = np.zeros(shape[:2], bool)
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = True
    return mask


def grow(mask, pixels):
    return np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * pixels + 1))) > 0


def triangles(path):
    raw = Path(path).read_bytes()
    _, nv, ni, _ = struct.unpack_from('<8sIII', raw)
    v = np.frombuffer(raw, '<f4', nv * 11, 20).reshape(nv, 11)
    return v[np.frombuffer(raw, '<u2', ni, 20 + nv * 44).reshape(-1, 3)]


def retrovision(oldtv_albedo):
    """The Old TV's RETROvision print as an alpha mask (ink=1), read the right way round
    (the atlas stores it mirrored) and smoothly upscaled 8x."""
    crop = np.asarray(Image.open(oldtv_albedo).convert('RGB').crop((46, 0, 140, 24))).astype(float).mean(2)
    plate, ink = np.median(crop), np.percentile(crop, 1)
    alpha = np.clip((plate - crop) / (plate - ink), 0, 1)
    rows, cols = np.nonzero(alpha > 0.35)
    alpha = alpha[max(rows.min() - 1, 0):rows.max() + 2, max(cols.min() - 1, 0):cols.max() + 2][:, ::-1]
    big = Image.fromarray((alpha * 255).astype(np.uint8)).resize((alpha.shape[1] * 8, alpha.shape[0] * 8), Image.LANCZOS)
    a = np.clip((np.asarray(big, float) / 255 - 0.3) / 0.4, 0, 1)
    return a * a * (3 - 2 * a)  # smoothstep: crisp edges without stair steps


def sample(alpha, s, t):
    """Bilinear alpha at decal coordinates s, t in [0, 1]; zero outside."""
    h, w = alpha.shape
    x, y = s * (w - 1), t * (h - 1)
    inside = (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1)
    x0, y0 = np.clip(np.floor(x).astype(int), 0, w - 2), np.clip(np.floor(y).astype(int), 0, h - 2)
    fx, fy = np.clip(x - x0, 0, 1), np.clip(y - y0, 0, 1)
    value = (alpha[y0, x0] * (1 - fx) * (1 - fy) + alpha[y0, x0 + 1] * fx * (1 - fy)
             + alpha[y0 + 1, x0] * (1 - fx) * fy + alpha[y0 + 1, x0 + 1] * fx * fy)
    return np.where(inside, value, 0)


def frame(centre, normal, width, height):
    n = np.array(normal, float) / np.linalg.norm(normal)
    right = np.array([1.0, 0, 0]) - n[0] * n
    right /= np.linalg.norm(right)
    return dict(centre=np.array(centre, float), normal=n, right=right, up=np.cross(n, right), width=width, height=height)


def project(folder, texture, decal, alpha, colour, tolerance=1.5):
    """Paint alpha into a model texture through its UVs: every front-facing texel whose
    surface point lies inside the decal rectangle (4x4 supersampled)."""
    path = folder / texture
    img = np.asarray(Image.open(path).convert('RGB')).astype(float)
    size = img.shape[0]
    coverage = np.zeros(img.shape[:2])
    offsets = (np.arange(4) + 0.5) / 4
    c, n, r, u = decal['centre'], decal['normal'], decal['right'], decal['up']
    for group in json.loads((folder / 'scene.json').read_text())['groups']:
        if group['texture'] != texture:
            continue
        for tri in triangles(folder / group['file']):
            P, UV = tri[:, :3].astype(float), tri[:, 9:11].astype(float) * size
            if np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) < 1e-6 or tri[:, 3:6].mean(0) @ n < 0.7:
                continue
            d = P - c
            if np.abs(d @ n).max() > tolerance:
                continue
            s, t = d @ r / decal['width'] + 0.5, 0.5 - d @ u / decal['height']
            if s.max() < 0 or s.min() > 1 or t.max() < 0 or t.min() > 1:
                continue
            x0, y0 = np.floor(UV.min(0)).astype(int)
            x1, y1 = np.ceil(UV.max(0)).astype(int)
            X, Y = np.meshgrid((np.arange(x0, x1)[:, None] + offsets).ravel(), (np.arange(y0, y1)[:, None] + offsets).ravel())
            v0, v1 = UV[1] - UV[0], UV[2] - UV[0]
            det = v0[0] * v1[1] - v1[0] * v0[1]
            if abs(det) < 1e-12:
                continue
            qx, qy = X - UV[0, 0], Y - UV[0, 1]
            b1, b2 = (qx * v1[1] - v1[0] * qy) / det, (v0[0] * qy - qx * v0[1]) / det
            b0 = 1 - b1 - b2
            inside = (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6)
            value = sample(alpha, b0 * s[0] + b1 * s[1] + b2 * s[2], b0 * t[0] + b1 * t[1] + b2 * t[2]) * inside
            per_texel = value.reshape(y1 - y0, 4, x1 - x0, 4).sum((1, 3)) / 16
            ty, tx = np.arange(y0, y1), np.arange(x0, x1)
            ok_y, ok_x = (ty >= 0) & (ty < size), (tx >= 0) & (tx < size)
            coverage[np.ix_(ty[ok_y], tx[ok_x])] += per_texel[np.ix_(ok_y, ok_x)]
    a = np.clip(coverage, 0, 1)[..., None]
    Image.fromarray((img * (1 - a) + np.array(colour, float) * a).round().astype(np.uint8)).save(path, optimize=True)
    return int((coverage > 0.02).sum())


def note(folder, text, groups=None):
    scene = json.loads((folder / 'scene.json').read_text())
    if groups:
        groups(scene)
    scene['changes'].append(MARK + text)
    (folder / 'scene.json').write_text(json.dumps(scene, indent=2) + '\n', newline='\n')


def panasonic(folder, alpha):
    lines = (folder / 'scene.txt').read_text().splitlines()
    head = lines[0].split()
    parts = [line for line in lines[3:] if not line.startswith('part-008.mesh ')]
    scene = json.loads((folder / 'scene.json').read_text())
    logo = [g for g in scene['groups'] if g['file'] == 'part-008.mesh' and g['object'] == 'Logo.001']
    if len(logo) != 1 or len(parts) != int(head[1]) - 1:
        raise ValueError('Not the unbranded Panasonic model (Logo.001 part-008 expected)')
    # The plate: an 18 mm logo on the panel texture right behind it (the panel texture is
    # ~1.2 texels/mm there, too coarse to print on), 0.3 mm in front of the stepped panel.
    front = triangles(folder / 'part-001.mesh')
    P = front[:, :, :3].astype(float)
    height, margin = 18.0, (1.08, 1.25)
    width = height * alpha.shape[1] / alpha.shape[0]
    half = np.array([width * margin[0], height * margin[1]]) / 2
    centre = np.array([-0.1, 82.3, 0.0])  # where Logo.001 stood
    behind = ((P[:, :, 0].min(1) < centre[0] + half[0]) & (P[:, :, 0].max(1) > centre[0] - half[0]) &
              (P[:, :, 1].min(1) < centre[1] + half[1]) & (P[:, :, 1].max(1) > centre[1] - half[1]) & (front[:, :, 5].mean(1) > 0.5))
    pts = P[behind].reshape(-1, 3)
    centroid = pts.mean(0)
    normal = np.linalg.svd(pts - centroid)[2][2]
    normal = normal if normal[2] > 0 else -normal
    centre[2] = centroid[2] - ((centre[:2] - centroid[:2]) @ normal[:2]) / normal[2]
    centre += normal * (((pts - centroid) @ normal).max() + 0.3)
    decal = frame(centre, normal, width * margin[0], height * margin[1])
    texture = np.asarray(Image.open(folder / 'albedo-01.png').convert('RGB')).astype(float)
    w, h = 512, 128
    s, t = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    point = decal['centre'] + (s - 0.5)[..., None] * decal['width'] * decal['right'] + (0.5 - t)[..., None] * decal['height'] * decal['up']
    panel = np.full((h, w, 3), np.nan)
    for tri in front[behind]:
        A, B, C = tri[:, :2].astype(float)
        det = (B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])
        if abs(det) < 1e-9:
            continue
        qx, qy = point[..., 0] - A[0], point[..., 1] - A[1]
        b1 = (qx * (C[1] - A[1]) - (C[0] - A[0]) * qy) / det
        b2 = ((B[0] - A[0]) * qy - qx * (B[1] - A[1])) / det
        b0 = 1 - b1 - b2
        inside = (b0 >= -1e-6) & (b1 >= -1e-6) & (b2 >= -1e-6) & np.isnan(panel[..., 0])
        uv = (b0[..., None] * tri[0, 9:11] + b1[..., None] * tri[1, 9:11] + b2[..., None] * tri[2, 9:11]) * texture.shape[0] - 0.5
        x0, y0 = np.clip(np.floor(uv[..., 0]).astype(int), 0, texture.shape[1] - 2), np.clip(np.floor(uv[..., 1]).astype(int), 0, texture.shape[0] - 2)
        fx, fy = np.clip(uv[..., 0] - x0, 0, 1)[..., None], np.clip(uv[..., 1] - y0, 0, 1)[..., None]
        colour = (texture[y0, x0] * (1 - fx) * (1 - fy) + texture[y0, x0 + 1] * fx * (1 - fy)
                  + texture[y0 + 1, x0] * (1 - fx) * fy + texture[y0 + 1, x0 + 1] * fx * fy)
        panel[inside] = colour[inside]
    if np.isnan(panel).any():
        raise ValueError('Logo plate extends past the Panasonic front panel')
    a = sample(alpha, (s - 0.5) * margin[0] + 0.5, (t - 0.5) * margin[1] + 0.5)[..., None]
    gold = np.array([200, 192, 153], float)  # the removed Logo.001 colour
    Image.fromarray((panel * (1 - a) + gold * a).round().astype(np.uint8)).save(folder / 'albedo-02.png', optimize=True)
    c, r, u, n = decal['centre'], decal['right'] * decal['width'] / 2, decal['up'] * decal['height'] / 2, decal['normal']
    corners = [(c - r + u, (0, 0)), (c + r + u, (1, 0)), (c - r - u, (0, 1)), (c + r - u, (1, 1))]
    vertices = b''.join(struct.pack('<11f', *p, *n, *front[behind][0, 0, 6:9], *uv) for p, uv in corners)
    authored = front[behind][0, :, :3].astype(float)  # match the panel's winding
    order = (0, 2, 3, 0, 3, 1) if np.cross(corners[2][0] - corners[0][0], corners[3][0] - corners[0][0]) @ n > 0 else (0, 3, 2, 0, 1, 3)
    if np.cross(authored[1] - authored[0], authored[2] - authored[0]) @ normal <= 0:
        order = order[::-1]
    (folder / 'part-009.mesh').write_bytes(struct.pack('<8sIII', b'SCTABL1\0', 4, 6, 0) + vertices + struct.pack('<6H', *order))
    (folder / 'part-008.mesh').unlink()
    (folder / 'scene.txt').write_text('\n'.join([head[0] + ' ' + str(len(parts) + 1)] + lines[1:3] + parts + ['part-009.mesh albedo-02.png 0']) + '\n',
                                      newline='\n')

    def groups(scene):
        scene['groups'] = [g for g in scene['groups'] if g['file'] != 'part-008.mesh']
        scene['groups'].append(dict(file='part-009.mesh', texture='albedo-02.png', glass=False, object='RETROvision plate',
                                    material='TVfront', triangles=2, vertices=4, sha256=sha(folder / 'part-009.mesh')))
        scene['retained_triangles'] += 2 - logo[0]['triangles']
    note(folder, 'Panasonic "Logo.001" part omitted; RETROvision plate (part-009, albedo-02) in its place', groups)
    return dict(removed='part-008.mesh (Logo.001)', plateMm=[round(width, 1), height])


def pvm(folder, alpha):
    path = folder / 'albedo-02.png'
    a = np.asarray(Image.open(path).convert('RGB')).astype(float)
    luma = a.mean(2)
    # Raised SONY letter faces (white UV islands) and the TRINITRON badge + RGB dots.
    bezel = tiled(a[3600:3920, 860:890], (a.shape[1], a.shape[0]))  # plain bezel beside the badge
    letters = np.zeros(a.shape[:2], bool)
    for x0, y0, x1, y1 in [(3790, 0, 3930, 170), (3805, 945, 3960, 1115), (3820, 2765, 3960, 2970), (3825, 3360, 3975, 3575)]:
        letters[y0:y1, x0:x1] = luma[y0:y1, x0:x1] > 110
    if letters.sum() < 30000:
        raise ValueError('Not the unbranded PVM texture (white SONY letter faces expected)')
    letters = grow(letters, 3)
    region = box_mask(a.shape, [(880, 3600, 940, 3930)])
    badge = grow(region & ((np.abs(luma - 76) > 5) | (a.max(2) - a.min(2) > 12)), 3) & region
    a = paint(a, letters | badge, bezel).astype(float)
    # Rear label words (boxes from the label's 1760,420 origin): SONY, TRINITRON, 2x SONY CORPORATION.
    for x0, y0, x1, y1 in [(36, 272, 64, 392), (62, 274, 87, 392), (229, 84, 253, 278), (225, 488, 251, 634)]:
        x0, y0, x1, y1 = x0 + 1760, y0 + 420, x1 + 1760, y1 + 420
        patch = a[y0 - 4:y1 + 4, x0 - 4:x1 + 4].reshape(-1, 3)
        a[y0:y1, x0:x1] = np.median(patch[patch.mean(1) < 70], 0)
    Image.fromarray(a.astype(np.uint8)).save(path, optimize=True)
    # The letters stand 1.26 mm proud of their backing (z 220.78), through holes in it:
    # pressing their faces flat fills the holes flush and the side walls collapse.
    mesh = folder / 'part-009.mesh'
    raw = bytearray(mesh.read_bytes())
    _, nv, ni, _ = struct.unpack_from('<8sIII', raw)
    v = np.frombuffer(raw, '<f4', nv * 11, 20).reshape(nv, 11).copy()
    ix = np.frombuffer(raw, '<u2', ni, 20 + nv * 44).reshape(-1, 3)
    p = v[ix][:, :, :3]
    raised = np.all((p >= [-26.9, 62.4, 214]) & (p <= [26.7, 75.1, 223]), axis=(1, 2)) & (p[:, :, 2].max(1) > 221.0)
    flat = np.unique(ix[raised])
    if raised.sum() != 1134 or np.isin(flat, ix[~raised]).any():
        raise ValueError('Unexpected PVM letter geometry')
    v[flat, 2], v[flat, 3:6] = 220.78, (0, 0, 1)
    raw[20:20 + nv * 44] = v.astype('<f4').tobytes()
    mesh.write_bytes(bytes(raw))

    def groups(scene):
        next(g for g in scene['groups'] if g['file'] == 'part-009.mesh')['sha256'] = sha(mesh)
    note(folder, 'SONY letters flattened onto their backing; SONY/TRINITRON marks removed from albedo-02; RETROvision painted in', groups)
    # Backing + flattened letters: bezel grey, then a white 8 mm RETROvision.
    project(folder, 'albedo-02.png', frame((-0.1, 68.75, 220.78), (0, 0, 1), 52, 11), np.ones((8, 8)), (77, 77, 75), 0.4)
    decal = frame((-0.1, 68.75, 220.78), (0, 0, 1), 8.0 * alpha.shape[1] / alpha.shape[0], 8.0)
    project(folder, 'albedo-02.png', decal, alpha, (240, 242, 241), 0.4)
    return dict(flattenedTriangles=int(raised.sum()), logoMm=[round(decal['width'], 1), 8.0])


def retro(folder, alpha):
    path = folder / 'albedo-00.png'
    a = np.asarray(Image.open(path).convert('RGB')).astype(float)
    luma = a.mean(2)
    text = grow(box_mask(a.shape, [(1682, 1032, 1702, 1126)]) & (luma > 45), 2) & box_mask(a.shape, [(1678, 1028, 1706, 1130)])
    if text.sum() < 400:
        raise ValueError('Not the unbranded Retro texture (Panasonic print expected)')
    Image.fromarray(paint(a, text, np.roll(a, -95, axis=0))).save(path, optimize=True)  # same dark strip 95 rows down
    decal = frame((1.35, 111.9, 218.53), (0.005, 0, 1), 6.5 * alpha.shape[1] / alpha.shape[0], 6.5)
    project(folder, 'albedo-00.png', decal, alpha, (141, 143, 90))  # olive like the print was
    note(folder, '"Panasonic" print on the front strip replaced by RETROvision in albedo-00')
    return dict(logoMm=[round(decal['width'], 1), 6.5])


def is_branded(folder):
    try:
        return any(change.startswith(MARK) for change in json.loads((Path(folder) / 'scene.json').read_text())['changes'])
    except (OSError, ValueError, KeyError):
        return False


def apply(assets, tvs=TVS, oldtv_albedo=None):
    """Brand prepared TV folders under assets/<tv> in place; returns a report."""
    assets = Path(assets)
    alpha = retrovision(oldtv_albedo or assets / 'oldtv/albedo-00.png')
    report = {}
    for tv in tvs:
        if is_branded(assets / tv):
            raise ValueError(tv + ' is already branded')
        report[tv] = dict(panasonic=panasonic, pvm=pvm, retro=retro)[tv](assets / tv, alpha)
    return report


def check(assets):
    """Problems that would show a Panasonic or Sony mark on the prepared TVs."""
    assets, problems = Path(assets), []
    for tv in TVS:
        if not is_branded(assets / tv):
            problems.append(tv + ': not RETROvision-branded')
    scene = (assets / 'panasonic/scene.txt').read_text()
    if 'part-008.mesh' in scene or 'part-009.mesh albedo-02.png' not in scene:
        problems.append('panasonic: Logo.001 still referenced or plate missing')
    p = triangles(assets / 'pvm/part-009.mesh')[:, :, :3]
    if (np.all((p >= [-26.9, 62.4, 214]) & (p <= [26.7, 75.1, 223]), axis=(1, 2)) & (p[:, :, 2].max(1) > 221.0)).any():
        problems.append('pvm: raised SONY letters present')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=('apply', 'check'))
    parser.add_argument('assets', type=Path, help='folder holding panasonic/, pvm/, retro/ and oldtv/')
    parser.add_argument('--tv', action='append', choices=TVS)
    args = parser.parse_args()
    if args.action == 'apply':
        print(json.dumps(apply(args.assets, args.tv or TVS), indent=2))
    else:
        problems = check(args.assets)
        print(json.dumps(dict(branded=not problems, problems=problems), indent=2))
        raise SystemExit(1 if problems else 0)


if __name__ == '__main__':
    main()
