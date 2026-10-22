"""Bounded PS1 identification and original fallback disc prints."""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from . import labels

SERIAL = re.compile(rb'(S[CL][EUPS][SM])[_-](\d{3})\.(\d{2})', re.I)
LIMIT = 2*1024*1024


def serial(data):
    hit=SERIAL.search(data)
    return (hit[1]+b'-'+hit[2]+hit[3]).decode('ascii').upper() if hit else ''


def identify(path, identities):
    """Never hash/read an entire CD. CHD readers extract only the boot area."""
    with path.open('rb') as f:
        head=f.read(124 if path.suffix.lower()=='.chd' else LIMIT)
    if path.suffix.lower()=='.chd':
        if head[:8]!=b'MComprHD':return b''
        version=int.from_bytes(head[12:16],'big')
        digest=head[64:84].hex() if version==5 else ''
        if identities.get(digest):return identities[digest].encode()
        tool=shutil.which('chdman')
        if tool:
            try:
                with tempfile.TemporaryDirectory(prefix='slot-disc-') as temp:
                    raw=Path(temp)/'boot.raw'
                    subprocess.run([tool,'extractraw','-i',str(path),'-o',str(raw),'-ib',str(LIMIT)],
                                   timeout=20,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    value=serial(raw.read_bytes())
                    if value and digest:identities[digest]=value
                    return value.encode()
            except (OSError,subprocess.SubprocessError):pass
        return b''
    if path.suffix.lower()=='.cue':
        hit=re.search(r'^\s*FILE\s+"([^"]+)"',head.decode('utf8','replace'),re.M|re.I)
        if hit:
            target=(path.parent/hit[1]).resolve()
            if target.is_relative_to(path.parent.resolve()) and target.is_file():
                with target.open('rb') as f:head=f.read(LIMIT)
    return serial(head).encode()


def region(game):
    code=game.header.code
    if code.startswith(('SLUS','SCUS')):return ('North America',)
    if code.startswith(('SLES','SCES')):return ('Europe','United Kingdom','Germany','France','Spain','Italy','Australia')
    if code.startswith(('SLPS','SCPS','SLPM','SCPM')):return ('Japan',)
    tags=' '.join(re.findall(r'\(([^)]*)\)',game.stem)).lower()
    if re.search(r'\b(usa|canada|north america)\b',tags):return ('North America',)
    if re.search(r'\bjapan\b',tags):return ('Japan',)
    if re.search(r'\b(europe|world|australia)\b',tags):return ('Europe','United Kingdom','Australia')
    return ()  # An ambiguous filename never silently gets another region's print.


def number(stem):
    hit=re.search(r'\b(?:disc|disk|cd)\s*(\d+)\b',stem,re.I)
    return int(hit[1]) if hit else None


def fallback(kind,source,paper,disc=None,platform='psx'):
    im=Image.new('RGB',(648,648),paper);d=ImageDraw.Draw(im)
    label=(labels.logo_label if kind=='logo' else labels.text_label)((370,150),source,paper)
    im.paste(label,(139,80))
    font=ImageFont.truetype(str(labels.FONT),25)
    d.text((324,526),{'psp':'PSP','dreamcast':'DREAMCAST'}.get(platform,'PLAYSTATION'),font=font,fill=labels.ink_for(paper),anchor='mm')
    if platform=='psp':
        d.ellipse((212,212,436,436),fill=(231,236,238),outline=(185,194,196),width=3)
        d.text((324,313),'UMD',font=ImageFont.truetype(str(labels.FONT),53),fill=(115,126,160),anchor='mm')
        d.text((324,356),'UNIVERSAL MEDIA DISC',font=ImageFont.truetype(str(labels.FONT),12),fill=(127,138,148),anchor='mm')
    if disc:d.text((324,562),'DISC '+str(disc),font=font,fill=labels.ink_for(paper),anchor='mm')
    return im
