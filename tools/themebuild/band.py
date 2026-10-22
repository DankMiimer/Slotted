"""The cart slot along the bottom of the screen, as two layers.

band-back.png is everything a seated cart sits in front of (lip, recess, slit, scoop opening);
band-front.png is the housing that hides the rest of a seated cart, with the scoop's rim. On the
shelf nothing sits in between, so band.png is simply the two composited.
"""
from PIL import Image, ImageDraw

from .geometry import (BAND_H, BAY_W, BAY_Y, EDGE, HOUSING, LIP_H, MOUTH_W, OPENING, RECESS,
                       RECESS_H, RIM_W, SCOOP_D, SCOOP_POWER, SCOOP_W, SCOOP_Y, SLIT_H, SLIT_Y,
                       W)

SS = 4  # supersampling for the curve
CX = W / 2
BAY_X = (W - BAY_W) / 2
MOUTH_X = (W - MOUTH_W) / 2


def scoop_depth(x):
    """Depth of the finger scoop below the slit, x pixels from the centre."""
    t = min(abs(x) / (SCOOP_W / 2), 1.0)
    return SCOOP_D * (1.0 - t ** SCOOP_POWER)


def scoop(extra):
    half = SCOOP_W / 2
    steps = 240
    pts = [((CX - half) * SS, SCOOP_Y * SS)]
    for i in range(steps + 1):
        x = -half + SCOOP_W * i / steps
        pts.append(((CX + x) * SS, (SCOOP_Y + scoop_depth(x) + extra) * SS))
    pts.append(((CX + half) * SS, SCOOP_Y * SS))
    return pts


def rect(draw, x, y, w, h, colour):
    draw.rectangle([x * SS, y * SS, (x + w) * SS - 1, (y + h) * SS - 1], fill=colour + (255,))


def back():
    img = Image.new('RGBA', (W * SS, BAND_H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rect(d, BAY_X, 0, BAY_W, LIP_H, HOUSING)
    rect(d, MOUTH_X, 0, MOUTH_W, LIP_H, EDGE)
    rect(d, BAY_X, BAY_Y, BAY_W, RECESS_H, RECESS)
    rect(d, MOUTH_X, SLIT_Y, MOUTH_W, SLIT_H, OPENING)
    d.polygon(scoop(0), fill=OPENING + (255,))
    return img.resize((W, BAND_H), Image.LANCZOS)


def front():
    img = Image.new('RGBA', (W * SS, BAND_H * SS), HOUSING + (255,))
    d = ImageDraw.Draw(img)
    clear = (0, 0, 0, 0)
    d.rectangle([BAY_X * SS, 0, (BAY_X + BAY_W) * SS - 1, SCOOP_Y * SS - 1], fill=clear)
    d.polygon(scoop(RIM_W), fill=EDGE + (255,))
    d.polygon(scoop(0), fill=clear)
    return img.resize((W, BAND_H), Image.LANCZOS)


def nes_layers():
    """A continuous front-loader bezel, with a horizontal tray opening."""
    b = Image.new('RGBA', (W * SS, BAND_H * SS))
    d = ImageDraw.Draw(b)
    rect(d, 219, 3, 282, 55, (0x79, 0x79, 0x7c))
    rect(d, 232, 9, 256, 38, (0x19, 0x19, 0x1c))
    rect(d, 237, 13, 246, 28, (0x05, 0x05, 0x07))
    rect(d, 239, 40, 242, 2, (0x36, 0x36, 0x3a))
    f = Image.new('RGBA', b.size, HOUSING + (255,))
    d = ImageDraw.Draw(f)
    rect(d, 218, 2, 284, 56, (0x79, 0x79, 0x7c))
    rect(d, 218, 2, 284, 1, (0xac, 0xac, 0xae))
    rect(d, 218, 53, 284, 5, (0x46, 0x46, 0x49))
    d.rectangle((232*SS, 9*SS, 488*SS-1, 47*SS-1), fill=(0, 0, 0, 0))
    rect(d, 232, 9, 256, 2, (0x4c, 0x4c, 0x50))
    rect(d, 232, 45, 256, 2, (0x94, 0x94, 0x97))
    return b.resize((W, BAND_H), Image.LANCZOS), f.resize((W, BAND_H), Image.LANCZOS)


def n64_layers():
    """One continuous dark console deck with a narrow top-loading mouth."""
    b = Image.new('RGBA', (W*SS, BAND_H*SS), HOUSING+(255,))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((210*SS, 0, 510*SS-1, 57*SS), 12*SS, fill=(0x15,0x15,0x19))
    rect(d, 231, 7, 258, 20, (0x04,0x04,0x06))
    rect(d, 240, 9, 240, 1, (0x39,0x39,0x3e))
    f = Image.new('RGBA', b.size, HOUSING+(255,))
    d = ImageDraw.Draw(f)
    d.rounded_rectangle((210*SS, 0, 510*SS-1, 57*SS), 12*SS, fill=(0x28,0x28,0x2e))
    d.arc((210*SS, 0, 510*SS-1, 110*SS), 190, 350, fill=(0x51,0x51,0x5a), width=SS)
    d.rectangle((233*SS, 7*SS, 487*SS-1, 26*SS-1), fill=(0,0,0,0))
    rect(d, 231, 6, 258, 1, (0x59,0x59,0x62))
    rect(d, 231, 26, 258, 2, (0x12,0x12,0x17))
    return b.resize((W,BAND_H),Image.LANCZOS), f.resize((W,BAND_H),Image.LANCZOS)


def build(out):
    b, f = back(), front()
    b.save(out / 'band-back.png')
    f.save(out / 'band-front.png')
    Image.alpha_composite(b, f).save(out / 'band.png')
    # Keep one continuous housing. Overlaying SLOT2's separate port shoulders
    # left floating tabs and dots outside this opening.
    b.save(out / 'band-snes-back.png')
    f.save(out / 'band-snes-front.png')
    Image.alpha_composite(b, f).save(out / 'band-snes.png')
    b, f = nes_layers()
    b.save(out / 'band-nes-back.png')
    f.save(out / 'band-nes-front.png')
    Image.alpha_composite(b, f).save(out / 'band-nes.png')
    b, f = n64_layers()
    b.save(out / 'band-n64-back.png')
    f.save(out / 'band-n64-front.png')
    Image.alpha_composite(b, f).save(out / 'band-n64.png')
    b, f = md_layers()
    b.save(out / 'band-md-back.png')
    f.save(out / 'band-md-front.png')
    Image.alpha_composite(b, f).save(out / 'band-md.png')


def md_layers():
    """A continuous black deck with a long chamfered cartridge socket."""
    b = Image.new('RGBA', (W*SS, BAND_H*SS), HOUSING+(255,))
    d = ImageDraw.Draw(b)
    d.polygon([(208*SS,0),(512*SS,0),(525*SS,17*SS),(515*SS,49*SS),
               (205*SS,49*SS),(195*SS,17*SS)],fill=(0x12,0x12,0x15))
    rect(d, 231, 8, 258, 20, (0x03,0x03,0x05))
    f = Image.new('RGBA', b.size, HOUSING+(255,))
    d = ImageDraw.Draw(f)
    d.polygon([(208*SS,0),(512*SS,0),(525*SS,17*SS),(515*SS,49*SS),
               (205*SS,49*SS),(195*SS,17*SS)],fill=(0x1d,0x1d,0x21))
    d.line([(208*SS,SS),(512*SS,SS),(524*SS,17*SS)],fill=(0x4a,0x4a,0x52),width=SS)
    d.rectangle((233*SS,8*SS,487*SS-1,28*SS-1),fill=(0,0,0,0))
    rect(d,231,7,258,1,(0x63,0x63,0x6a))
    rect(d,231,28,258,2,(0x09,0x09,0x0c))
    return b.resize((W,BAND_H),Image.LANCZOS), f.resize((W,BAND_H),Image.LANCZOS)
