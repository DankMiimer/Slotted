"""Original physical cartridge/card media for the remaining cartridge systems (MIT).

Millimetres, x right, y up, z towards the label face. Each front silhouette and
label well is the project's own shelf drawing (tools/themebuild/assets), mapped
onto the published physical envelope, so the shelf face and the 3D shell share
one outline and one label crop. Thickness, edges, grips, seams, screws, rear
recesses and connector openings are original geometry from the reference card
in docs/MODEL_MEDIA.md. No photographs, scans, logos or downloaded meshes.
"""
import math
import re
import json
from pathlib import Path

from exemplars import rounded_rect
from snes import SPECS as SNES
from n64 import SPECS as N64

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'tools/themebuild/assets'

# Physical envelope (W, H, T mm), console folder and native units per mm.
# A variant shares its console's scale; EA's narrower body keeps md's scale.
MEDIA = {
    'gba': dict(svg='cart',size=(60,34.5,7.8),folder='gba',part='media',canvas=(360,212)),
    'snes':    dict(svg='snes-pal', size=(130, 86, 20), folder='snes', part='media', canvas=(360, 245)),
    'snes-us': dict(svg='snes-us', size=(136, 88, 20), folder='snes-us', part='media', canvas=(360, 245)),
    'nes':     dict(svg='nes', size=(120, 133, 19), folder='nes', part='media', canvas=(304, 337)),
    'n64':     dict(svg='n64', size=(116, 76.6, 18.5), folder='n64', part='media', canvas=(360, 241)),
    'md':      dict(svg='md', size=(109, 70, 17), folder='md', part='media', canvas=(360, 270)),
    'md-jp':   dict(svg='md-jp', size=(109, 70, 17), folder='md-jp', part='media', canvas=(360, 270)),
    'md-ea':   dict(svg='md-ea', size=(97, 89, 17), folder='md', part='media-ea', canvas=(360, 270)),
    'nds':     dict(svg='nds', size=(33, 35, 3.8), folder='nds', part='media', canvas=(312, 341)),
    'pico8':   dict(svg='pico8', size=(60, 76.875, 6), folder='pico8', part='media', canvas=(264, 338), svg_scale=1.65),
    'snes-tzakol':dict(svg='snes-pal',size=(130,88.56,20),folder='snes',part='media-tzakol',canvas=(360,245)),
    'snes-us-tzakol':dict(svg='snes-pal',size=(130,88.56,20),folder='snes-us',part='media-tzakol',canvas=(360,245)),
}
# SNES and N64 use their corrected consoles' uniform scales. Other seated width
# targets keep the existing slot mouths. DS's 3.8-mm card fits its 11-unit Slot-1 mouth.
SCALES = {'gba':224/82,'nes': 196/120,
          'md': 224/109, 'md-jp': 224/109, 'nds': 2.75, 'pico8': 2.2}
SCALES.update({name:s['scale'] for name,s in (SNES|N64).items()})
CONSOLE_VARIANTS = {'snes': ('snes',), 'snes-us': ('snes-us',), 'nes': ('nes',), 'n64': ('n64',),
                    'md': ('md', 'md-ea'), 'md-jp': ('md-jp',), 'nds': ('nds',), 'pico8': ('pico8',)}
# Plain plastic sample rectangles in each shelf canvas (x0, y0, x1, y1), used by
# the native helper to tint the shell with the baked cartridge's colour. Keep
# them off recess floors and, for clear shells, off the board behind them.
SAMPLES = {'snes': (110, 185, 250, 215), 'snes-us': (90, 115, 165, 134), 'nes': (180, 240, 280, 268),
           'gba':(8,70,40,180),
           'n64': (20, 50, 60, 160), 'md': (100, 234, 260, 244), 'md-jp': (100, 234, 260, 245),
           'md-ea': (120, 230, 290, 255), 'nds': (40, 306, 130, 328), 'pico8': (8, 60, 22, 240)}
SAMPLES.update({'snes-tzakol':(15,135,55,205),'snes-us-tzakol':(15,135,55,205)})
WELLS = {'snes': ((30, 12, 330, 120), 10), 'snes-us': ((70, 7, 290, 111), 10), 'nes': ((122, 4, 263, 230), 3),
         'n64': ((78, 26, 282, 220), 10), 'md': ((51, 22, 311, 232), 8), 'md-jp': ((50, 24, 311, 231), 10),
         'md-ea': ((96, 3, 303, 224), 2), 'nds': ((23, 17, 289, 302), 9)}
LABEL_DEPTH = {'nds': .2, 'pico8': .18}

def authored(variant):
    spec=MEDIA.get(variant,{})
    path=ROOT/'theme/art-book-slot/_slot/consoles'/spec.get('folder',variant)/(spec.get('part','media')+'-registration.json')
    return json.loads(path.read_text()) if path.exists() else None

def hero_path(variant):
    return ASSETS/'hero'/('snes-tzakol.json' if variant=='snes-us-tzakol' else variant+'.json')
# Mouldings standing proud of each face (grips, rails, ribs), mm per side.
PROUD = {'md': .7, 'md-jp': .95, 'md-ea': .6}
# Shelf/hero contract for the licensed handheld media (MODEL_GBC/GBA_SP). The 3D
# Game Pak is mapped onto the existing shelf body box; its recess becomes the
# shelf label rectangle. Label: centre x/y and half width/height in mm.
EXEMPLARS = {
    'gb': dict(canvas=(312, 337), body=(8, 0, 304, 337), size=(57, 65.5),
               label=(0, -4.8791, 20.92095, 18.7022), sample=(14, 150, 24, 280)),
    'gbc': dict(canvas=(312, 337), body=(8, 0, 304, 337), size=(57, 65.5),
                label=(0, -5, 20.9, 18.6), sample=(14, 150, 24, 280)),
    'gba': dict(canvas=(360, 212), body=(0, 0, 360, 212), size=(60, 34.5),
                label=(0, -2, 22.15, 11.5), sample=(8, 70, 40, 180)),
}


def exemplar_label(name):
    """Shelf pixel rectangle of the Game Pak recess at the hero pose.

    Once tools/consolebuild/hero-shells.sh has measured it in the native render
    (perspective included), the baked face and the native crop share that box.
    """
    import json
    measured = ASSETS/'hero'/(name+'.json')
    if measured.exists():
        return tuple(json.loads(measured.read_text())['label'])
    e = EXEMPLARS[name]; (x0, y0, x1, y1), (w, h) = e['body'], e['size']
    sx, sy = (x1-x0)/w, (y1-y0)/h; cx, cy = (x0+x1)/2, (y0+y1)/2
    lx, ly, lw, lh = e['label']
    return tuple(round(v) for v in (cx+(lx-lw)*sx, cy-(ly+lh)*sy, cx+(lx+lw)*sx, cy-(ly-lh)*sy))

# The reserved shell colours are replaced by the baked cart's plastic at runtime.
SHELL = (.50, .50, .50)
SHADE = (.36, .36, .36)
# NES front-loader tray top (presentation units before the console's 2.1 height
# stretch), from models.home(): the Game Pak rides just above it.
NES_TRAY_TOP = -25.5


def flatten(d, steps=10):
    """Absolute M/L/H/V/Q/Z SVG path to a polyline in canvas pixels."""
    tokens = re.findall(r'[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)', d)
    points = []; k = 0; cmd = None; x = y = 0.0

    def num():
        nonlocal k
        value = float(tokens[k]); k += 1
        return value
    while k < len(tokens):
        if tokens[k].isalpha():
            cmd = tokens[k]; k += 1
        if cmd == 'Z':
            continue
        if cmd in 'ML':
            x, y = num(), num(); points.append((x, y))
            if cmd == 'M':
                cmd = 'L'
        elif cmd == 'H':
            x = num(); points.append((x, y))
        elif cmd == 'V':
            y = num(); points.append((x, y))
        elif cmd == 'Q':
            cx, cy, ex, ey = num(), num(), num(), num()
            for i in range(1, steps + 1):
                t = i / steps
                points.append(((1-t)**2*x + 2*t*(1-t)*cx + t*t*ex, (1-t)**2*y + 2*t*(1-t)*cy + t*t*ey))
            x, y = ex, ey
        else:
            raise ValueError('Unsupported SVG command: ' + cmd)
    clean = []
    for p in points:
        if not clean or math.dist(p, clean[-1]) > 1e-6:
            clean.append(p)
    if math.dist(clean[0], clean[-1]) < 1e-6:
        clean.pop()
    return clean


class Frame:
    """Canvas pixels to physical millimetres for one shelf drawing."""

    def __init__(self, variant):
        spec = MEDIA[variant]; self.variant = variant
        registered=authored(variant)
        if registered:
            self.w,self.h,self.t=registered['size_mm']
            cw,ch=spec['canvas'];margin=8 if 'tzakol' in variant else 0;bh=(cw-2*margin)*self.h/self.w
            self.body=(margin,(ch-bh)/2,cw-margin,(ch+bh)/2)
            hero=hero_path(variant)
            if hero.exists():self.body=tuple(json.loads(hero.read_text()).get('body',self.body))
            self.sx=self.w/(self.body[2]-self.body[0]);self.sy=self.h/(self.body[3]-self.body[1])
            self.cx=(self.body[0]+self.body[2])/2;self.cy=(self.body[1]+self.body[3])/2
            self.outline=[(-self.w/2,-self.h/2),(self.w/2,-self.h/2),(self.w/2,self.h/2),(-self.w/2,self.h/2)]
            return
        text = (ASSETS / (spec['svg'] + '.svg')).read_text()
        d = re.search(r'<path[^>]* d="([^"]+)"', text).group(1)
        k = spec.get('svg_scale', 1)
        pixels = [(x*k, y*k) for x, y in flatten(d)]
        xs = [p[0] for p in pixels]; ys = [p[1] for p in pixels]
        self.body = (min(xs), min(ys), max(xs), max(ys))
        self.w, self.h, self.t = spec['size']
        self.sx = self.w / (self.body[2]-self.body[0]); self.sy = self.h / (self.body[3]-self.body[1])
        self.cx = (self.body[0]+self.body[2])/2; self.cy = (self.body[1]+self.body[3])/2
        self.outline = [self.p(x, y) for x, y in pixels]

    def p(self, x, y):
        return ((x-self.cx)*self.sx, (self.cy-y)*self.sy)

    def r(self, length):
        return length*(self.sx+self.sy)/2

    def rect(self, x0, y0, x1, y1, radius=0, steps=6):
        ax, ay = self.p(x0, y1); bx, by = self.p(x1, y0)
        w, h = bx-ax, by-ay; radius = min(self.r(radius), w/2-.01, h/2-.01)
        if radius <= .02:
            return [(bx, by), (ax, by), (ax, ay), (bx, ay)]
        return rounded_rect(w, h, (radius,)*4, ((ax+bx)/2, (ay+by)/2), steps)

    def centre(self, x0, y0, x1, y1):
        a = self.p(x0, y1); b = self.p(x1, y0)
        return ((a[0]+b[0])/2, (a[1]+b[1])/2, b[0]-a[0], b[1]-a[1])

    def label(self):
        registered=authored(self.variant)
        if registered:
            x,y,w,h,z=registered['label_mm']
            return (x,y,w*2,h*2),self.t/2-z+.03
        if self.variant == 'pico8':
            # Fantasy carts keep the ROM's complete PNG artwork, credits included.
            return self.centre(*self.body), 0.0
        (well, _) = WELLS[self.variant]
        return self.centre(*well), LABEL_DEPTH.get(self.variant, .5)


class Builder:
    def __init__(self, m, variant, name):
        self.m = m; self.f = Frame(variant); self.name = name
        f = self.f
        # Five-segment moulded radii keep the cel bands smooth on the edges.
        self.shell = m.contour_shell(name+' original shell', f.outline, f.t/2, f.t, m.M['mediashell'],
                                     min(2.0, f.t*.16), 5)
        self.shell['dimension_critical'] = True
        self.shaded = []

    # Subtractive mouldings; EXACT booleans keep thin walls watertight. A shaded
    # recess floor reads as moulding head-on, where cel bands are uniform.
    def front(self, label, profile, depth, shade=False):
        self.m.cut_profile(self.shell, label, profile, self.f.t/2+1, depth+1)
        if shade:
            self.shaded.append((profile, self.f.t/2-depth, 1))

    def rear(self, label, profile, depth, shade=False):
        self.m.cut_profile(self.shell, label, profile, -self.f.t/2+depth, depth+1)
        if shade:
            self.shaded.append((profile, -self.f.t/2+depth, -1))

    def cut(self, pos, size):
        import handhelds
        handhelds.physical_cut(self.m, self.shell, pos, size)

    def groove(self, cx, cy, w, h, depth, rear=False):
        side = -1 if rear else 1
        self.cut((cx, cy, side*self.f.t/2), (w, h, 2*depth))
        self.shaded.append(([(cx-w/2, cy-h/2), (cx+w/2, cy-h/2), (cx+w/2, cy+h/2), (cx-w/2, cy+h/2)],
                            side*(self.f.t/2-depth), side))

    def union(self, obj):
        """Merge an additive moulding into the shell so later cuts reach it."""
        bpy = self.m.bpy
        for target in (obj, self.shell):
            bpy.context.view_layer.objects.active = target
            for mod in list(target.modifiers):
                bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = self.shell.modifiers.new('Moulded union', 'BOOLEAN'); mod.operation = 'UNION'
        mod.object = obj; mod.solver = 'EXACT'
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(obj, do_unlink=True)

    def raised(self, label, profile, z0, z1, radius=.5):
        o = self.m.contour_shell(self.name+' '+label, profile, z1, z1-z0, self.m.M['mediashell'], radius, 3)
        self.union(o)

    def add(self, label, pos, size, colour='mediashell', radius=0):
        o = self.m.box(self.name+' '+label, pos, size, self.m.M[colour], radius)
        return o

    def well(self):
        f = self.f; depth = LABEL_DEPTH.get(f.variant, .5)
        if f.variant == 'pico8':
            # Shallow frame: the PNG cart image already shows its own label.
            box = (f.body[0]+6.6, f.body[1]+6.6, f.body[2]-6.6, f.body[3]-6.6); radius = 3
        else:
            box, radius = WELLS[f.variant]
        self.front('Label recess', f.rect(*box, radius), depth)
        cx, cy, w, h = f.centre(*box)
        plate = self.add('blank recessed label', (cx, cy, f.t/2-depth+.012), (w-.3, h-.3, .02), 'label')
        plate['outline'] = False

    def screws(self, points, surface=None, rear=False):
        """Recessed security screws, front or rear, on the local surface."""
        f = self.f; side = -1 if rear else 1; s = surface if surface is not None else side*f.t/2
        for x, y in points:
            px, py = x, y
            circle = self.m.arc_points(px, py, 2.45, 2.45, steps=20)[:-1]
            if rear:
                self.m.cut_profile(self.shell, 'Rear security screw socket', circle, s+1.4, 2.4)
            else:
                self.m.cut_profile(self.shell, 'Security screw socket', circle, s+1, 2.4)
            self.shaded.append((circle, s-side*1.4, side))
            self.m.cylinder(self.name+' security screw head', (px, py, s-side*1.25), 1.75, .5, self.m.M['metal'], 'front', 16)
            self.m.cylinder(self.name+' security screw socket', (px, py, s-side*.95), .62, .12, self.m.M['black'], 'front', 6)

    def connector(self, width, height, pins, pitch, wall=2.0, inset=1.4, board=1.2, gap=0):
        """Open lower edge with the board's edge fingers visible inside.

        `pins` per side may be grouped, e.g. (4, 23, 4) with `gap` pitches between.
        """
        f = self.f; bottom = -f.h/2
        self.cut((0, bottom+height/2-1, 0), (width, height+2, f.t-2*wall))
        self.add('dark connector cavity', (0, bottom+height-.25, 0), (width-.1, .5, f.t-2*wall-.1), 'black')
        y0 = bottom+inset; length = height-inset-.5
        self.add('edge connector board', (0, y0+length/2, 0), (width-3, length, board), 'pcb')
        groups = pins if isinstance(pins, tuple) else (pins,)
        slots = sum(groups)+gap*(len(groups)-1); positions = []; k = 0
        for g in groups:
            positions += [k+i for i in range(g)]; k += g+gap
        for side in (1, -1):
            for i in positions:
                x = (i-(slots-1)/2)*pitch
                finger = self.add('edge connector finger', (x, y0+length*.42, side*(board/2+.02)),
                                  (pitch*.58, length*.8, .04), 'gold')
                finger['outline'] = False

    def mark(self, cx, cy, width, rear=True):
        """Embossed oval Nintendo wordmark: our own paths, in the shaded plastic."""
        f = self.f; z = -f.t/2-.02 if rear else f.t/2+.02
        return self.mark_at(cx, cy, width, z, rear)

    def mark_at(self, cx, cy, width, z, rear=True):
        m = self.m; mat = m.M['mediashade']
        ring = m.ink_path('Embossed Nintendo oval', m.arc_points(cx, cy, width/2, width*.16, steps=40), z, mat, width*.022)
        m.nintendo_word((cx, cy, z), width*.72, mat, rear)
        return ring

    def rear_label(self, rect, depth=.3):
        self.rear('Rear label recess', rect, depth)

    def finish(self):
        import handhelds
        # Recolour the recess floors the booleans left: faces at the floor depth
        # facing out of their side, whose centre lies inside the recess outline.
        mesh = self.shell.data; mesh.materials.append(self.m.M['mediashade'])
        for polygon in mesh.polygons:
            c = polygon.center; x, y, z = c.x*100, c.z*100, -c.y*100; nz = -polygon.normal.y
            for profile, floor, side in self.shaded:
                if nz*side > .99 and abs(z-floor) < .02 and inside(profile, x, y):
                    polygon.material_index = 1; break
        handhelds.panel_normals(self.m, self.shell)
        # Planar faces and floors keep their exact normal: no smoothed gradient
        # leaks across a large panel from a bevel or boolean sliver at its edge.
        mesh.update(); normals = [tuple(n.vector) for n in mesh.corner_normals]
        for polygon in mesh.polygons:
            if abs(polygon.normal.y) > .999:
                for li in polygon.loop_indices:
                    normals[li] = tuple(polygon.normal)
        mesh.normals_split_custom_set(normals)


def inside(profile, x, y):
    hit = False
    for (ax, ay), (bx, by) in zip(profile, profile[1:]+profile[:1]):
        if (ay > y) != (by > y) and x < ax+(y-ay)*(bx-ax)/(by-ay):
            hit = not hit
    return hit


def snes(m, us=False):
    b = Builder(m, 'snes-us' if us else 'snes', 'SNES Game Pak' if not us else 'North American SNES Game Pak'); f = b.f
    if us:
        # The raised centre spine stands 2 mm proud of the ribbed side wings.
        step = 2.0
        for x0, x1 in ((-4, 65), (295, 364)):
            b.front('Grip wing', f.rect(x0, 7, x1, 250), step)
            # Stop short of the spine wall: a coplanar cutter leaves boolean slivers.
            g0, g1 = (x0, x1-1) if x0 < 0 else (x0+1, x1)
            for y in (49.5, 88.5, 127.5, 166.5, 205.5):
                b.groove(*f.centre(g0, y-1.5, g1, y+1.5), step+.8)
        b.screws([f.p(34, 224), f.p(326, 224)], f.t/2-step)
        # Small moulded boss under the label, then the broad lower finger recess
        # with its two vertical ridges.
        x, y = f.p(180, 123)
        m.cylinder(b.name+' moulded boss', (x, y, f.t/2+.05), 1.3, .5, m.M['mediashell'], 'front', 20)
        b.front('Lower finger recess', f.rect(78, 138, 282, 236, 6), 1.2, True)
        for x in (141.5, 222.5):
            cx, cy, w, h = f.centre(x-2.2, 140, x+2.2, 234)
            b.raised('finger recess ridge', rounded_rect(w, h, (.6,)*4, (cx, cy)), f.t/2-1.3, f.t/2-.35, .3)
        b.connector(98, 9, 23, 2.5)
        # Rear: full-width moulded bands, label recess, embossed oval and the
        # two lower slots that keep the shell out of a Super Famicom.
        for frac in (.15, .30, .46, .61, .76):
            cy = f.h/2-f.h*frac
            b.groove(0, cy, f.w+4, 1.1, .5, rear=True)
        b.rear_label(f.rect(77, 34, 283, 115, 4), .55)
        b.mark(0, f.h/2-f.h*.69, 29)
        for x in (-55.7, 55.7):
            b.rear('Lower lockout slot', rounded_rect(3.2, 13, (.6,)*4, (x, -f.h/2+5)), 3.0, True)
    else:
        # Five edge notches near the top of each side, as on the PAL/Japanese shell.
        for y in (18, 30, 42, 54, 66):
            for x0, x1 in ((-6, 12), (348, 366)):
                b.groove(*f.centre(x0, y-3, x1, y+3), .8)
            for x0, x1 in ((-6, 2.4), (357.6, 366)):
                cx, cy, w, h = f.centre(x0, y-3, x1, y+3)
                b.cut((cx, cy, 0), (w, h, f.t+2))
        for x in (59.5, 302.5):
            for y0, y1 in ((124, 243), (2, 9)):
                b.groove(*f.centre(x-.9, y0, x+.9, y1), .35)
        # Long finger slot with a raised middle third, as on the shell.
        b.front('Finger slot', f.rect(78, 148, 282, 171, 11.5), 1.2, True)
        cx, cy, w, h = f.centre(146, 150, 214, 169)
        b.raised('finger slot bridge', rounded_rect(w, h, (2.6,)*4, (cx, cy)), f.t/2-1.3, f.t/2-.5, .3)
        b.screws([f.p(23, 229), f.p(337, 229)])
        # Main and expansion contact groups on the board edge.
        b.connector(92, 9, (4, 23, 4), 2.5, gap=2)
        # Rear: framed label area, side seams and two moulded holes.
        b.rear_label(f.rect(80, 26, 280, 214, 4), .4)
        for x in (70, 290):
            b.groove(*f.centre(x-.9, 10, x+.9, 240), .3, rear=True)
        for x in (24, 336):
            px, py = f.p(x, 226)
            b.rear('Rear moulded hole', m.arc_points(px, py, 1.4, 1.4, steps=16)[:-1], 1.4, True)
    b.well(); b.finish()


def nes(m):
    b = Builder(m, 'nes', 'NES Game Pak'); f = b.f
    # Recessed ribbed grip strip on the left with its deeper upper pocket.
    b.front('Ribbed grip channel', f.rect(49, -4, 114, 300), 1.0, True)
    b.front('Upper grip pocket', f.rect(52, 4, 111, 44, 3), 2.2, True)
    for i in range(24):
        y = 8 + i*12.6
        cx, cy, w, h = f.centre(51, y-2.6, 112, y+2.6)
        z = f.t/2-1.75 if y < 44 else f.t/2-.55
        b.add('grip rib', (cx, cy, z), (w, h, .9), 'mediashell')
    b.front('Lower grip recess', f.rect(51, 305, 112, 334, 3), .6, True)
    b.front('Insertion arrow', [f.p(140, 249), f.p(154, 273), f.p(168, 249)], .4, True)
    b.groove(*f.centre(18, 276.5, 286, 279.5), .3)
    b.connector(100, 9, 36, 2.54)
    b.rear_label(f.rect(30, 70, 274, 262, 4), .4)
    # Rear finger ribs across the top of the Game Pak.
    for i in range(4):
        b.groove(*f.centre(14, 12+i*12.6-1.6, 290, 12+i*12.6+1.6), .5, rear=True)
    b.well(); b.finish()


def n64(m):
    b = Builder(m, 'n64', 'N64 Game Pak'); f = b.f
    # NUS-006 photographs (Evan-Amos front; rear of a NUS-EUR-1 Pak): two
    # parting lines frame side strips; the label recess fills the panel between.
    for x in (70.5, 289.5):
        b.groove(*f.centre(x-1.4, 14, x+1.4, 238), .45)
    # Short shoulder notches at the outer lower corners, matching the rear.
    b.front('Left shoulder notch', f.rect(-8, 214, 40, 250, 6), 1.2, True)
    b.front('Right shoulder notch', f.rect(320, 214, 368, 250, 6), 1.2, True)
    b.groove(*f.centre(8, 235.5, 352, 238.5), .4)
    # Rear: embossed oval under the crown, two screws at the tops of the parting
    # lines, the wide rear label recess and two open corner notches.
    surface = -f.t/2
    b.mark_at(0, f.h/2-9.6, 34, surface-.02)
    b.screws([(-37, f.h/2-8.8), (37, f.h/2-8.8)], surface, rear=True)
    b.rear_label(f.rect(47, 62, 313, 194, 5), .35)
    for x in (-49.5, 49.5):
        b.rear('Rear corner notch', rounded_rect(14, 11, (.8,)*4, (x, -f.h/2+3.5)), 2.0, True)
    b.connector(70, 8, 25, 2.5)
    b.well(); b.finish()


def mega_drive(m, variant):
    names = {'md': 'Sega cartridge', 'md-jp': 'Japanese Sega cartridge', 'md-ea': 'Electronic Arts cartridge'}
    b = Builder(m, variant, names[variant]); f = b.f
    if variant == 'md':
        # Broad rounded side grips stand slightly proud of the label face.
        # Slightly outset at the outer wall so the grip, not the shell, owns it.
        for x0, x1 in ((-.6, 46), (314, 360.6)):
            m.contour_shell(b.name+' rounded side grip', f.rect(x0, 18.5, x1, 251.5, 9), f.t/2+.7, f.t+1.4,
                            m.M['mediashell'], .9, 5)
        b.groove(*f.centre(8, 246, 352, 249), .35)
    elif variant == 'md-jp':
        for x0, x1 in ((3, 34), (326, 357)):
            m.contour_shell(b.name+' grip rail', f.rect(x0, 24, x1, 236, 8), f.t/2+.6, f.t+1.2, m.M['mediashell'], .7, 4)
        for x0, x1, spans in ((5, 17, ((67, 140), (153, 189))), (343, 355, ((67, 189),))):
            for y0, y1 in spans:
                y = y0+2
                while y < y1:
                    cx, cy, w, h = f.centre(x0, y-.7, x1, y+.7)
                    b.add('grip rib', (cx, cy, f.t/2+.7), (w, h, .5), 'mediashade')
                    y += 5
        b.groove(*f.centre(34, 246.5, 326, 249.5), .35)
    else:
        rail = m.contour_shell(b.name+' left shoulder rail', [f.p(x, y) for x, y in
                               ((42, 1), (94, 1), (94, 258), (45, 258), (48, 226), (48, 105), (34, 109), (34, 20))],
                               f.t/2+.6, f.t+1.2, m.M['mediashell'], .6, 4)
        grip = [f.p(x, y) for x, y in ((30, 22), (83, 24), (90, 30), (90, 97), (83, 104), (30, 110))]
        b.front('Grip recess', grip, 1.4, True)
        m.cut_profile(rail, 'Grip recess through rail', grip, f.t/2+1, 2.4)
        # EA's moulded yellow grip, seated in its recess; no manufacturer mark.
        m.contour_shell(b.name+' yellow grip', [f.p(x, y) for x, y in ((40, 25), (82, 28), (86, 33), (86, 93), (82, 99), (40, 105))],
                        f.t/2+.5, f.t/2+.5, m.M['yellow'], .4, 2)
        for x in (94, 306):
            b.groove(*f.centre(x-1, 0, x+1, 259), .45)
    b.connector(86, 8, 32, 2.54)
    b.rear_label(f.rect(70 if variant != 'md-ea' else 110, 40, 290 if variant != 'md-ea' else 300, 210, 6))
    b.well(); b.finish()


def nds(m):
    b = Builder(m, 'nds', 'DS Game Card'); f = b.f
    b.front('Insertion arrow', [f.p(143, 316), f.p(156, 329), f.p(169, 316)], .15, True)
    b.groove(*f.centre(10, 7, 301, 10), .15)
    # Seventeen contacts in a rear bay open to the connector (lower) edge.
    b.rear('Rear contact bay', f.rect(24, 258, 288, 345), .55)
    for i in range(17):
        x0 = 29+i*15
        cx, cy, w, h = f.centre(x0, 265, x0+10, 325)
        contact = b.add('gold contact', (cx, cy, -f.t/2+.55-.025), (w, h, .04), 'gold')
        contact['outline'] = False
    for i in range(16):
        x0 = 29+i*15+10.5
        cx, cy, w, h = f.centre(x0, 259, x0+4, 340)
        b.add('contact separator', (cx, cy, -f.t/2+.3), (w, h, .5), 'mediashade')
    # Embossed oval wordmark on the rear, as moulded on the card.
    b.mark(0, f.h/2-f.h*.26, 15.4)
    b.well(); b.finish()


def pico8(m):
    b = Builder(m, 'pico8', 'Fantasy cartridge'); f = b.f
    k = 1.65
    # Rear grip ridges and an open connector edge; invented hardware.
    for i in range(6):
        y = (150+i*7)*k
        cx, cy, w, h = f.centre(30*k, y-1.2, 130*k, y+1.2)
        b.add('rear grip ridge', (cx, cy, -f.t/2-.25), (w, h, .5), 'mediashade')
    b.connector(46, 6, 16, 2.54, wall=1.2, board=1.0)
    b.well(); b.finish()


BUILDERS = {'snes': lambda m: snes(m), 'snes-us': lambda m: snes(m, True), 'nes': nes, 'n64': n64,
            'md': lambda m: mega_drive(m, 'md'), 'md-jp': lambda m: mega_drive(m, 'md-jp'),
            'md-ea': lambda m: mega_drive(m, 'md-ea'), 'nds': nds, 'pico8': pico8}


def build(m, variant):
    before = set(m.bpy.context.scene.objects)
    BUILDERS[variant](m)
    m.uniform_group(before, SCALES[MEDIA[variant]['folder']])


def native_header():
    """Generated table for cartridge-console.h, from the same frames."""
    (ROOT/'tools/slotlaunch/media-specs.h').write_text(header_text(), encoding='utf8', newline='\n')


def header_text():
    lines = ['/* Generated by tools.consolebuild.media; original geometry, MIT. */',
             'static const MediaSpec media_specs[] = {']
    for variant, spec in MEDIA.items():
        f = Frame(variant); (cx, cy, w, h), depth = f.label()
        registered=authored(variant)
        well = (0, 0, *spec['canvas']) if variant == 'pico8' else WELLS.get(variant,((49,49,315,187),0))[0]
        sample=SAMPLES[variant]
        hero=hero_path(variant)
        if registered and hero.exists():
            measured=json.loads(hero.read_text());well=measured['label'];sample=measured.get('sample',sample)
        values = [f.w, f.h, f.t, SCALES[spec['folder']], cx, cy, w/2, h/2, f.t/2-depth+.03,0 if variant=='gba' else f.t/2]
        lines.append('    {"%s","%s","%s",{%s},{%s},{%s,%s},{%s},{%s}},' % (
            variant, spec['folder'], spec['part'], ','.join('%.9g' % v for v in values),
            ','.join(str(int(v)) for v in well), spec['canvas'][0], spec['canvas'][1],
            ','.join('%.6g' % v for v in f.body), ','.join(str(v) for v in sample)))
    lines += ['};', 'static const ExemplarShelf exemplar_shelf[] = {']
    for name, e in EXEMPLARS.items():
        lines.append('    {"%s",{%d,%d},{%s},{%s},{%s},{%s}},' % (
            name, *e['canvas'], ','.join('%.6g' % v for v in e['body']),
            ','.join(str(v) for v in exemplar_label(name)), ','.join('%.6g' % v for v in e['size']),
            ','.join(str(v) for v in e['sample'])))
    lines += ['};', 'static const double nes_tray_top = %s;' % NES_TRAY_TOP,
              'static const float media_shell[3] = {%sf,%sf,%sf};' % SHELL,
              'static const float media_shade[3] = {%sf,%sf,%sf};' % SHADE, '']
    return '\n'.join(lines)


def slot_cavity(m, housings, centre, size):
    """Physical cartridge cavity through every listed housing (fit correction)."""
    import handhelds
    for obj in housings:
        handhelds.physical_cut(m, obj, centre, size)


def opening(console):
    """Slot opening depth for the console's seated media thickness, 1 mm a side."""
    if console in SNES|N64:return (SNES|N64)[console]['opening'][1]*SCALES[console]
    variants = CONSOLE_VARIANTS[console]
    thickness = max(MEDIA[v]['size'][2]+2*PROUD.get(v, 0) for v in variants)
    return thickness*SCALES[console] + 2*SCALES[console]


if __name__ == '__main__':
    native_header()
