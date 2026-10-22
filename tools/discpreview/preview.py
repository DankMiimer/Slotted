"""Socket-inspired PS1 study; original art and geometry, never installed on the device.

Run python -m tools.discpreview.preview. See tools/discpreview/README.md for references.
Pillow renders perspective planes and extruded rings at 2x the panel resolution;
the exported 60 fps movie is a design reference, not a device performance result.
"""
import argparse
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/shots/psx-study'
FONT = ROOT / 'third_party/open-sans/OpenSans-SemiBold.ttf'
S, W, H = 2, 720, 480
PHI = math.radians(35)
VIEW = np.array((0, math.sin(PHI), math.cos(PHI)))
FOCAL = 1200
SEGMENTS = 96
INSERT_SECONDS = .95
EJECT_SECONDS = .85


def ease(x):
    x = max(0, min(1, x))
    return x*x*x*(10+x*(-15+6*x))


def font(size):
    return ImageFont.truetype(str(FONT), round(size*S))


def project(points, origin=350):
    """One camera for the console, its rear hinge, the spindle and the disc."""
    p = np.asarray(points, dtype=float)
    k = FOCAL / (FOCAL - p @ VIEW)
    return np.column_stack((360+p[:, 0]*k,
                            origin+(p[:, 2]*math.sin(PHI)-p[:, 1]*math.cos(PHI))*k))


def polygon(im, points, colour, origin):
    ImageDraw.Draw(im).polygon([tuple(p*S) for p in project(points, origin)], fill=colour)


def plane(im, texture, centre, u, v, radius, origin):
    """Project a texture without stretching its label in screen space."""
    centre, u, v = map(np.asarray, (centre, u, v))
    points = [centre+u*x+v*y for x, y in
              ((-radius, -radius), (radius, -radius), (radius, radius), (-radius, radius))]
    q = project(points, origin)*S
    lo = np.maximum(np.floor(q.min(axis=0)), (0, 0)).astype(int)
    hi = np.minimum(np.ceil(q.max(axis=0)), (W*S, H*S)).astype(int)
    width, height = hi-lo
    if width < 1 or height < 1:
        return
    matrix, rhs = [], []
    tw, th = texture.size
    for (x, y), (a, b) in zip(q-lo, ((0, 0), (tw, 0), (tw, th), (0, th))):
        matrix.extend(((x, y, 1, 0, 0, 0, -a*x, -a*y),
                       (0, 0, 0, x, y, 1, -b*x, -b*y)))
        rhs.extend((a, b))
    if abs(np.linalg.det(matrix)) < 1e-7:
        return
    coefficients = np.linalg.solve(matrix, rhs)
    tex = texture.transform((width, height), Image.Transform.PERSPECTIVE,
                            coefficients, Image.Resampling.BICUBIC)
    im.alpha_composite(tex, tuple(lo))


def texture(title, colour):
    """A fictional full-face print with a restrained foil rim and an open bore."""
    n = 324*S
    y, x = np.mgrid[0:n, 0:n]
    dx, dy = (x+.5-n/2)/S, (y+.5-n/2)/S
    r, angle = np.hypot(dx, dy), np.arctan2(dy, dx)
    metal = 185+25*np.sin(angle*2+.4)+8*np.cos(angle*4)
    a = np.zeros((n, n, 4), dtype=np.uint8)
    for c, phase in enumerate((0, 2.1, 4.2)):
        a[:, :, c] = np.clip(metal+5*np.sin(angle*3+phase), 0, 255)
    a[:, :, 3] = np.where((r < 162) & (r > 20.25), 255, 0)
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    d.ellipse((4*S, 4*S, 320*S, 320*S), fill=colour)
    ink = tuple(min(255, round(c*1.55)) for c in colour)
    for shift in (-70, -20, 30, 80):
        d.line(((12+shift)*S, 312*S, (246+shift)*S, 14*S), fill=ink, width=13*S)
    mask = Image.fromarray(np.where(r < 158, 255, 0).astype(np.uint8))
    im = Image.composite(im, Image.fromarray(a), mask)
    d = ImageDraw.Draw(im)
    first, second = title.split(' ', 1)
    d.text((162*S, 72*S), first, font=font(25), fill=(245, 241, 229), anchor='mm')
    d.text((162*S, 105*S), second, font=font(25), fill=(245, 241, 229), anchor='mm')
    d.text((162*S, 246*S), 'ART BOOK SLOT', font=font(15), fill=(242, 238, 230), anchor='mm')
    d.text((162*S, 270*S), 'PS1  /  MOTION STUDY', font=font(9), fill=(199, 206, 210), anchor='mm')
    # The CD's 15/120 bore ratio stays fixed through every projection.
    for radius, col in ((39, (123, 126, 128)), (36, (204, 206, 202)),
                        (30, (110, 114, 116)), (28, (191, 196, 192)),
                        (22, (216, 219, 212)), (20.25, (0, 0, 0, 0))):
        d.ellipse(((162-radius)*S, (162-radius)*S,
                   (162+radius)*S, (162+radius)*S), fill=col)
    im.putalpha(Image.fromarray(a[:, :, 3]))
    return im


def underside():
    n = 324*S
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x+.5-n/2, y+.5-n/2)/S
    angle = np.arctan2(y-n/2, x-n/2)
    col = 19+5*np.sin(angle*2)+2*np.cos(angle*5)
    a = np.zeros((n, n, 4), dtype=np.uint8)
    for c in range(3):
        a[:, :, c] = col+c
    a[:, :, 3] = np.where((r < 162) & (r > 20.25), 255, 0)
    return Image.fromarray(a)


def scan_texture(path):
    """Accept a square local disc scan, preserving circular print and adding a bore.

    This intentionally does not accept box art or guess a crop. The production
    baker still needs source alignment and multi-disc identity validation.
    """
    with Image.open(path) as source:
        if not .97 <= source.width/source.height <= 1.03:
            raise ValueError(f'Disc scan must be square: {path}')
        im = source.convert('RGBA').resize((324*S, 324*S), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(im)
    # Reconstruct the physical hub over scans whose print fills the clamp area.
    for radius, col in ((45, (107, 112, 113)), (43, (191, 194, 188)),
                        (30, (115, 118, 120)), (28, (202, 206, 200)),
                        (22, (225, 227, 217)), (20.25, (0, 0, 0, 0))):
        d.ellipse(((162-radius)*S, (162-radius)*S,
                   (162+radius)*S, (162+radius)*S), fill=col)
    y, x = np.mgrid[0:324*S, 0:324*S]
    radius = np.hypot((x+.5)/S-162, (y+.5)/S-162)
    alpha = np.where((radius < 162) & (radius > 20.25), 255, 0).astype(np.uint8)
    im.putalpha(Image.fromarray(alpha))
    return im


def lid_texture(inside=False):
    im = Image.new('RGBA', (256*S, 256*S))
    d = ImageDraw.Draw(im)
    d.ellipse((S, S, 255*S, 255*S), fill=(59, 59, 62) if inside else (190, 187, 188))
    d.ellipse((3*S, 3*S, 253*S, 253*S), fill=(36, 36, 39) if inside else (196, 193, 194))
    d.arc((4*S, 4*S, 252*S, 252*S), 180, 310,
          fill=(79, 79, 84) if inside else (229, 225, 223), width=S)
    if inside:
        d.ellipse((57*S, 57*S, 199*S, 199*S), outline=(68, 68, 73), width=3*S)
        for degrees in range(0, 360, 45):
            a = math.radians(degrees)
            d.line((128*S+73*S*math.cos(a), 128*S+73*S*math.sin(a),
                    128*S+117*S*math.cos(a), 128*S+117*S*math.sin(a)),
                   fill=(60, 60, 65), width=2*S)
        d.ellipse((108*S, 108*S, 148*S, 148*S), fill=(63, 63, 67))
    else:
        d.text((128*S, 150*S), 'PS1', font=font(14), fill=(118, 116, 121), anchor='mm')
    return im


FACES = [texture('ORBIT RACER', (79, 48, 28)),
         texture('MIDNIGHT SIGNAL', (28, 46, 56)),
         texture('CRYSTAL HARBOR', (56, 40, 72))]
BACK = underside()
LID, UNDER = lid_texture(), lid_texture(True)


def ring(im, front, back, centre, u, v, radius, thickness, origin,
         brightness=1, inner=0, lid=False):
    """The label is one plane; the outer edge and bore wall have real depth."""
    centre, u, v = map(np.asarray, (centre, u, v))
    normal = -np.cross(u, v)
    rear = centre-normal*thickness
    angles = np.arange(SEGMENTS+1)*2*math.pi/SEGMENTS
    circle = np.outer(np.cos(angles), u)+np.outer(np.sin(angles), v)
    faces = []
    for rad in (radius, inner):
        if rad <= 0:
            continue
        for i in range(SEGMENTS):
            direction = (circle[i]+circle[i+1])/2
            if rad == inner:
                direction = -direction
            if direction @ VIEW <= 0:
                continue
            p = [centre+circle[i]*rad, centre+circle[i+1]*rad,
                 rear+circle[i+1]*rad, rear+circle[i]*rad]
            illumination = max(0, direction @ np.array((-.5, .6, .6)))
            tone = (116+42*illumination) if lid else (18+36*illumination) if rad==radius else (40+100*illumination)
            colour = tuple(round((tone+j)*brightness) for j in (0, 1, 3))
            faces.append((np.mean(p, axis=0) @ VIEW, p, colour))
    for _, p, colour in sorted(faces, key=lambda item: item[0]):
        polygon(im, p, colour, origin)
    tex = front if normal @ VIEW >= 0 else back
    if brightness != 1:
        channels = tex.split()
        tex = Image.merge('RGBA', tuple(c.point(lambda a: round(a*brightness))
                                        for c in channels[:3])+(channels[3],))
    plane(im, tex, centre if normal @ VIEW >= 0 else rear, u, v, radius, origin)


def circle(im, centre, radius, colour, origin):
    p = [(centre[0]+radius*math.cos(t), centre[1], centre[2]+radius*math.sin(t))
         for t in np.arange(97)*2*math.pi/96]
    polygon(im, p, colour, origin)


def deck(im, origin):
    # Original model: bevelled grey body, rear-hinged lid, drive well and controls.
    outline = [(-216, -150), (216, -150), (228, -132), (228, 132),
               (215, 150), (-215, 150), (-228, 132), (-228, -132)]
    for i in (2, 3, 4, 5, 6):
        a, b = outline[i], outline[(i+1) % 8]
        polygon(im, [(a[0], 0, a[1]), (b[0], 0, b[1]),
                     (b[0], -24, b[1]), (a[0], -24, a[1])], (133, 130, 135), origin)
    polygon(im, [(x, 0, z) for x, z in outline], (180, 177, 181), origin)
    d = ImageDraw.Draw(im)
    q = project([(x, .4, z) for x, z in outline], origin)*S
    d.line([tuple(p) for p in q[:4]], fill=(222, 219, 219), width=S)
    circle(im, (0, .4, 0), 128, (119, 116, 122), origin)
    circle(im, (0, .6, 0), 125, (47, 47, 51), origin)
    circle(im, (0, .8, 0), 113, (24, 24, 28), origin)
    circle(im, (0, 1, 0), 10, (94, 94, 102), origin)
    circle(im, (0, 3, 0), 5, (158, 157, 165), origin)
    for x, title in ((-176, 'POWER'), (176, 'OPEN')):
        circle(im, (x, 1, 75), 17, (132, 129, 139), origin)
        circle(im, (x-.6, 1.5, 73), 15, (163, 160, 169), origin)
        tx, ty = project([(x, 1, 105)], origin)[0]*S
        d.text((tx, ty), title, font=font(6), fill=(92, 89, 99), anchor='mm')
    circle(im, (-181, 1, -83), 12, (144, 141, 150), origin)
    for x in (*range(-149, -126, 4), *range(127, 150, 4)):
        p = project([(x, 1, -93), (x, 1, 52)], origin)*S
        d.line([tuple(a) for a in p], fill=(125, 122, 134), width=S)
    polygon(im, [(-186, 1, 127), (-180, 1, 127), (-180, 1, 131), (-186, 1, 131)],
            (106, 149, 102), origin)
    for x in (-69,69):
        polygon(im,[(x-60,-2,150.2),(x+60,-2,150.2),(x+60,-23,150.2),(x-60,-23,150.2)],(105,103,109),origin)
        polygon(im,[(x-49,-4,150.5),(x+49,-4,150.5),(x+49,-8,150.5),(x-49,-8,150.5)],(35,34,39),origin)
        polygon(im,[(x-36,-12,150.6),(x+36,-12,150.6),(x+41,-16,150.6),(x+36,-22,150.6),(x-36,-22,150.6),(x-41,-16,150.6)],(40,39,45),origin)
        for pin in range(9):
            px=x-28+7*pin
            polygon(im,[(px-1,-15,150.8),(px+1,-15,150.8),(px+1,-18,150.8),(px-1,-18,150.8)],(143,140,123),origin)


def draw_lid(im, origin, opening):
    angle = opening*math.radians(78)
    centre = (0, 128*math.sin(angle)+2, -128+128*math.cos(angle))
    ring(im, LID, UNDER, centre, (1, 0, 0), (0, math.sin(angle), math.cos(angle)),
         126, 3, origin, lid=True)


def disc_basis(tilt, yaw=0, roll=0):
    u, v = np.array((1., 0, 0)), np.array((0, -math.cos(tilt), math.sin(tilt)))
    matrix = np.array(((math.cos(yaw), 0, math.sin(yaw)), (0, 1, 0),
                       (-math.sin(yaw), 0, math.cos(yaw))))
    u, v = matrix@u, matrix@v
    return u*math.cos(roll)+v*math.sin(roll), -u*math.sin(roll)+v*math.cos(roll)


def frame(u=0, returning=False, gallery=0):
    im = Image.new('RGBA', (W*S, H*S), (0, 0, 0, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 422*S, W*S, H*S), fill=(35, 35, 41))
    d.text((24*S, 452*S), '100%', font=font(15), fill=(220, 220, 224), anchor='lm')
    d.text((696*S, 452*S), 'PLAYSTATION', font=font(12), fill=(220, 220, 224), anchor='rm')
    unfold = ease(u/.19)
    origin = 527+(350-527)*unfold
    opening = ease(u/.22)*(1-ease((u-.66)/.19))
    travel = ease((u-.12)/.44)
    lift = 8*math.sin(math.pi*ease(u/.24))*(1-travel)
    centre_y = 156+(2-156)*travel+lift
    diameter = 300+(240-300)*travel
    tilt = PHI+(math.pi/2-PHI)*travel
    yaw = math.radians(10)*(1-travel)
    spin = 0 if returning else math.radians(160)*ease((u-.57)/.14)**2
    roll = math.radians(-3)*(1-travel)+spin
    if gallery:
        for index in (0, 1, 2):
            distance = index-1+gallery
            size = 300*(1-.23*min(1, abs(distance)))
            basis = disc_basis(PHI, math.radians(10), math.radians(-3))
            centre = (distance*334, 156-22*min(1, abs(distance)), 0)
            ring(im, FACES[index], BACK, centre, *basis, size/2, 2.2, 350,
                 brightness=.55+.45*max(0, 1-abs(distance)), inner=size*.0625)
    else:
        for index, x in ((0, -334), (2, 334)):
            basis = disc_basis(PHI, math.radians(10), math.radians(-3))
            ring(im, FACES[index], BACK, (x, 134, 0), *basis, 115.5, 2.2, 350,
                 brightness=.55, inner=14.4375)
    deck(im, origin)
    draw_lid(im, origin, opening)
    if not gallery:
        if travel:
            rad = diameter/2*(.65+.34*travel)
            shadow = Image.new('RGBA', im.size)
            circle(shadow, (0, 1.1, 0), rad+5*(1-travel), (0, 0, 0, round(105*travel)), origin)
            im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur((8-7*travel)*S)))
        basis = disc_basis(tilt, yaw, roll)
        disc_origin = 350+(origin-350)*travel
        ring(im, FACES[1], BACK, (0, centre_y, 0), *basis, diameter/2, 2.2,
             disc_origin, inner=diameter*.0625)
        if travel > .98:
            circle(im, (0, 4.4, 0), 5, (116, 115, 124), origin)
        if u > .66:
            draw_lid(im, origin, opening)
    fade = ease((u-.86)/.13)
    if fade:
        im = Image.blend(im, Image.new('RGBA', im.size, (0, 0, 0, 255)), fade)
    return im.resize((W, H), Image.Resampling.LANCZOS).convert('RGB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', nargs=3, type=Path, metavar=('LEFT', 'CENTRE', 'RIGHT'),
                        help='Optional local square disc scans; artwork is never downloaded by this tool')
    parser.add_argument('--out-dir', type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out_dir
    if args.labels:
        FACES[:] = [scan_texture(path) for path in args.labels]
    out.mkdir(parents=True, exist_ok=True)
    idle = frame()
    black = frame(1)
    assert not np.asarray(black).any(), 'Final launch frame must be completely black'
    assert np.array_equal(np.asarray(idle), np.asarray(frame(0, returning=True))), 'Eject must restore the shelf exactly'
    command = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', '720x480', '-r', '60', '-i', '-', '-an', '-c:v', 'libx264',
               '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
               str(out/'disc-motion.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for _ in range(45):
            process.stdin.write(frame(gallery=1).tobytes())
        for i in range(19):
            process.stdin.write(frame(gallery=1-ease(i/18)).tobytes())
        for _ in range(50):
            process.stdin.write(idle.tobytes())
        insert_frames = round(INSERT_SECONDS*60)
        for i in range(insert_frames+1):
            process.stdin.write(frame(i/insert_frames).tobytes())
        for _ in range(30):
            process.stdin.write(black.tobytes())
        eject_frames = round(EJECT_SECONDS*60)
        for i in range(eject_frames+1):
            process.stdin.write(frame(1-i/eject_frames, returning=True).tobytes())
        for _ in range(70):
            process.stdin.write(idle.tobytes())
    finally:
        process.stdin.close()
        status = process.wait()
    if status:
        raise SystemExit('ffmpeg failed')
    gap = 12
    sheet = Image.new('RGB', (W*3+gap*2, H*2+gap), (65, 65, 65))
    for i, u in enumerate((0, .23, .43, .58, .79, 1)):
        sheet.paste(frame(u), ((i % 3)*(W+gap), (i//3)*(H+gap)))
    sheet.save(out/'poses.png')
    idle.save(out/'disc.png')
    FACES[1].resize((324, 324), Image.Resampling.LANCZOS).save(out/'label.png')
    print(out/'disc-motion.mp4')


if __name__ == '__main__':
    main()
