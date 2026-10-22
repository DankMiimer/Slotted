"""Read local cartridge artwork without changing or executing a PICO-8 ROM (MIT)."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

PALETTE=tuple(tuple(bytes.fromhex(c)) for c in (
    '000000','1d2b53','7e2553','008751','ab5236','5f574f','c2c3c7','fff1e8',
    'ff004d','ffa300','ffec27','00e436','29adff','83769c','ff77a8','ffccaa'))
FONT=Path(__file__).resolve().parents[1]/'fonts/RasterForge.ttf'
MAX_TEXT=4*1024*1024


def text_label(path):
    """Only the 128 by 128 standard-palette __label__ section; never Lua."""
    with Path(path).open('rb') as stream:raw=stream.read(MAX_TEXT+1)
    if len(raw)>MAX_TEXT:return None
    lines=raw.decode('utf8',errors='replace').splitlines()
    if not lines or not lines[0].startswith('pico-8 cartridge'):return None
    try:first=lines.index('__label__')+1
    except ValueError:return None
    rows=lines[first:first+128]
    if len(rows)!=128 or any(len(row)!=128 or any(c not in '0123456789abcdef' for c in row) for row in rows):return None
    label=Image.new('RGB',(128,128));label.putdata([PALETTE[int(c,16)] for row in rows for c in row])
    return label


def plan(game):
    path=game.path
    if path.suffix.lower()=='.png':
        try:
            with Image.open(path) as image:
                if image.format=='PNG' and image.size==(160,205):return ('pico-cart',str(path),None)
        except (OSError,ValueError,Image.DecompressionBombError):pass
    elif path.suffix.lower()=='.p8' and text_label(path) is not None:
        return ('pico-label',str(path),None)
    if path.name.lower()=='splore.png':return ('pico-browser','Splore',None)
    return None


def cartridge(shape,path,shell=None):
    with Image.open(path) as source:
        if source.format!='PNG' or source.size!=(160,205):raise ValueError('Expected a 160x205 PNG cartridge')
        # Low alpha bits may encode the game. They are data, not translucent
        # plastic. Preserve RGB artwork and credits, replacing display alpha.
        if getattr(shape,'pico_sticker_crop',None):
            from . import render,shells
            return render.face(shape,shell or shells.PICO_GREY,source.convert('RGB').crop(shape.pico_sticker_crop))
        face=source.convert('RGB').resize(shape.size,Image.Resampling.NEAREST).convert('RGBA')
    face.putalpha(shape.mask)
    return face


def browser_label(size):
    image=Image.new('RGB',(128,128),PALETTE[1]);draw=ImageDraw.Draw(image)
    for row in range(2):
        for col in range(3):
            x,y=13+35*col,14+38*row;colour=PALETTE[(12,8,10,11,14,9)[row*3+col]]
            draw.rectangle((x,y,x+25,y+29),fill=colour)
            draw.rectangle((x+4,y+5,x+21,y+21),fill=PALETTE[1])
    draw.text((64,103),'SPLORE',fill=PALETTE[7],font=ImageFont.truetype(str(FONT),16),anchor='mm')
    return image.resize(size,Image.Resampling.NEAREST)


def sticker(label,title):
    """A .p8 text cart has square art but no embedded credit panel: keep it whole."""
    image=Image.new('RGB',(128,172),PALETTE[1]);image.paste(label.convert('RGB').resize((128,128),Image.Resampling.NEAREST))
    draw=ImageDraw.Draw(image);font=ImageFont.truetype(str(FONT),8)
    words=title.split();lines=[];line=''
    for word in words:
        attempt=(line+' '+word).strip()
        if font.getlength(attempt)>120 and line:lines.append(line);line=word
        else:line=attempt
    if line:lines.append(line)
    for i,line in enumerate(lines[:3]):draw.text((4,136+i*10),line,font=font,fill=PALETTE[7])
    return image
