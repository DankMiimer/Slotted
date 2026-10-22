"""Cart faces from pre-rendered shape assets, with Pillow alone.

Each shape folder (_slot/shapes/<name>/) holds masks built on the PC by tools/themebuild:
    mask.png        silhouette (L)
    shade.png       moulding shadow weights (L)
    light.png       moulding highlight weights (L)
    rim.png         lit edge of clear plastic (L)
    bevel-dark.png  upper-left bevel of the label well (L)
    bevel-lit.png   lower-right bevel of the label well (L)
    board.png       circuit board seen through clear plastic (RGBA)
    flecks.png      glitter specks (L)
    surface.png     optional plastic grain/diffuse light (L, 128 = neutral)
    accent.png      optional fixed-colour moulded part (RGBA)
    model.png       optional moulding of the cartridge's 3D model (L, 255 = plastic)
    shape.json      {"size": [w, h], "well": [x0, y0, x1, y1]}, optional "label" box
so the handheld needs neither numpy nor an SVG renderer.
"""
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

WELL = (0x2a, 0x2a, 0x2e)
VERSION = 1  # bump when the look changes, so baked carts get redone


class Shape:
    def __init__(self, folder):
        folder = Path(folder)
        spec = json.loads((folder / 'shape.json').read_text())
        self.name = folder.name
        self.size = tuple(spec['size'])
        self.well = tuple(spec['well'])
        # A 3D Game Pak's recess can sit inside the shelf's video well.
        self.label = tuple(spec.get('label', spec['well']))
        self.well_radius = spec.get('wellRadius', 0)
        self.disc = spec.get('disc', False)
        self.umd = spec.get('umd',False)

        def layer(name, mode='L'):
            return Image.open(folder / name).convert(mode)

        self.mask = layer('mask.png')
        if self.disc or self.umd:
            self.projection = spec['projection']
            self.print_mask = layer('print-mask.png')
            self.hub = layer('hub.png', 'RGBA')
            self.edge = layer('edge.png', 'RGBA')
            if self.disc:
                rim = folder/'disc-rim.png'
                self.disc_rim = layer('disc-rim.png','RGBA') if rim.exists() else None
            if self.umd: self.shell = layer('shell.png','RGBA')
            return
        self.shade = layer('shade.png')
        self.light = layer('light.png')
        self.rim = layer('rim.png')
        self.bevel_dark = layer('bevel-dark.png')
        self.bevel_lit = layer('bevel-lit.png')
        self.board = layer('board.png', 'RGBA')
        self.flecks = layer('flecks.png')
        self.surface = layer('surface.png') if spec.get('surface') else None
        self.accent = layer('accent.png', 'RGBA') if spec.get('accent') else None
        self.model = layer('model.png') if spec.get('model') else None
        self.fixed = layer('model-fixed.png','RGB') if spec.get('fixed') else None
        self.pico_sticker_crop=spec.get('picoStickerCrop')
        self.label_mask=layer('label-mask.png').crop(self.label) if spec.get('labelMask') else None

    @property
    def well_size(self):
        x0, y0, x1, y1 = self.well
        return x1 - x0, y1 - y0

    @property
    def label_size(self):
        x0, y0, x1, y1 = self.label
        return x1 - x0, y1 - y0


def scaled(img, k):
    return img.point(lambda v: max(0, min(255, int(v * k))))


def towards_white(img, k):
    return img.point(lambda v: int(v + (255 - v) * k))


def face(shape, shell, label=None):
    """A cart face in `shell` plastic, with `label` (any size, RGB/RGBA) filling the well."""
    if shape.disc:
        return disc_poster(shape, disc_texture(shape, label))
    if shape.umd:
        return disc_poster(shape,umd_texture(shape,label))
    size = shape.size
    plastic = Image.new('RGB', size, shell.colour)
    body = plastic
    if shell.finish in ('clear', 'glitter'):
        # The board behind the plastic, tinted by it, with the edges catching the light.
        behind = Image.composite(shape.board.convert('RGB'), plastic, shape.board.getchannel('A'))
        body = Image.blend(ImageChops.multiply(behind, plastic), plastic, 0.4)
        body = Image.composite(towards_white(plastic, 0.4), body, shape.rim)
        if shell.finish == 'glitter':
            body = Image.composite(Image.new('RGB', size, (255, 255, 255)), body, shape.flecks)

    if shape.surface is not None:
        body = ImageChops.add(body, shape.surface.convert('RGB'), offset=-128)
    body = Image.composite(scaled(body, 0.62), body, shape.shade)
    body = Image.composite(towards_white(body, 0.24), body, shape.light)
    body = Image.composite(scaled(body, 0.55), body, shape.bevel_dark)
    body = Image.composite(scaled(body, 1.45), body, shape.bevel_lit)
    if shape.model is not None:
        # The rendered 3D moulding: bands, recesses and contour, in this plastic.
        body = ImageChops.multiply(body, shape.model.convert('RGB'))
    if shape.fixed is not None:body=ImageChops.add(body,shape.fixed)

    x0, y0, x1, y1 = shape.label
    well_mask = shape.label_mask
    if well_mask is not None:
        body.paste(WELL,(x0,y0,x1,y1),well_mask)
    elif shape.well_radius:
        well_mask = Image.new('L', shape.label_size)
        ImageDraw.Draw(well_mask).rounded_rectangle((0, 0, x1-x0-1, y1-y0-1),
                                                   shape.well_radius, fill=255)
        body.paste(WELL, (x0, y0, x1, y1), well_mask)
    else:
        body.paste(WELL, (x0, y0, x1, y1))
    if label is not None:
        fitted = ImageOps.fit(label.convert('RGBA'), shape.label_size,
                             Image.Resampling.NEAREST if shape.name=='pico8' else Image.LANCZOS)
        alpha = fitted.getchannel('A')
        body.paste(fitted, (x0, y0), ImageChops.multiply(alpha, well_mask) if well_mask else alpha)

    out = body.convert('RGBA')
    if shape.accent is not None:
        out = Image.alpha_composite(out, shape.accent)
    out.putalpha(shape.mask)
    return out


def disc_texture(shape, label=None):
    """Opaque printed CD ring; only the physical bore and outside are transparent."""
    size=shape.print_mask.size
    base=Image.new('RGBA',size,(158,162,165,255))
    if label is not None:
        # Scan RGB remains useful beneath transparent pixels in public disc scans.
        base=label.convert('RGB').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
    base=Image.alpha_composite(base,shape.hub)
    if shape.disc_rim is not None:
        base=Image.alpha_composite(base,shape.disc_rim)
    base.putalpha(shape.print_mask)
    return base


def disc_poster(shape, flat):
    face=flat.transform(shape.edge.size,Image.Transform.PERSPECTIVE,shape.projection,
                        Image.Resampling.BICUBIC)
    return Image.alpha_composite(shape.edge,face).resize(shape.size,Image.Resampling.LANCZOS)


def umd_texture(shape,label=None):
    """Printed disc behind a closed, opaque UMD window and original plastic shell."""
    out=shape.shell.copy()
    if label is not None:
        # Only the circular print is accepted, never photographed shell plastic.
        printed=label.convert('RGB').resize((544,544),Image.Resampling.LANCZOS)
        sheet=Image.new('RGB',out.size);sheet.paste(printed,(52,52))
        out.paste(sheet,(0,0),shape.print_mask)
    return Image.alpha_composite(out,shape.hub)
