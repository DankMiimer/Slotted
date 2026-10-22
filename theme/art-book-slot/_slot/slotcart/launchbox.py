"""Regional console label crops from LaunchBox's public metadata and Cart - Front images.

Only exact titles/alternate names are matched. Crops and their source records live in
the user's cache; no game art is part of the theme. Offline runs use the same index.
"""
import json
from io import BytesIO
import os
import re
import shutil
import struct
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections import defaultdict
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps

from .library import clean_title

METADATA = 'https://gamesdb.launchbox-app.com/Metadata.zip'
IMAGES = 'https://images.launchbox-app.com/'
PLATFORM = 'Super Nintendo Entertainment System'
PLATFORMS = {'snes': PLATFORM, 'nes': 'Nintendo Entertainment System', 'n64': 'Nintendo 64',
             'md': 'Sega Genesis', 'psx': 'Sony Playstation', 'dreamcast': 'Sega Dreamcast', 'psp': 'Sony PSP', 'nds': 'Nintendo DS'}
AGENT = 'Mozilla/5.0 ArtBookSlot/1'
MAX_AGE = 7*24*3600
CROP_VERSION = 2
NES_CROP_VERSION = 1
N64_CROP_VERSION = 1
MD_CROP_VERSION = 1
PSX_CROP_VERSION = 1
# Printed disc numbers visually checked against these public source scans.
# Metadata omits them; ambiguous multi-disc scans otherwise fall back to a logo.
DISC_NUMBERS = {
    'f472db1d-b441-4782-8d48-8a06e08ab93f.png': 1,
    'a07f1dab-fdf9-41bd-903f-18f20627e88b.png': 2,
    '03a2d77e-1dbf-4348-be24-aa43974afeaa.png': 3,
    '7e0b44f3-0c3c-45b8-9ab1-ed5e29f65c45.png': 4,
}


def title_key(title):
    # No-Intro moves the article after the main title, including before a subtitle.
    title = re.sub(r',\s*the\b', '', title, flags=re.IGNORECASE)
    words = re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', title).encode(
        'ascii', 'ignore').decode().lower())
    if words and words[0] == 'the':
        words = words[1:]
    if words and words[-1] == 'the':
        words = words[:-1]
    return ''.join(words)


def regions(stem, platform=None):
    tags = ' '.join(re.findall(r'\(([^)]*)\)', stem)).lower()
    if re.search(r'\b(usa|canada|north america)\b', tags):
        return ('North America',)
    if re.search(r'\bjapan\b', tags) and not (platform == 'md' and re.search(r'\b(europe|world)\b', tags)):
        return ('Japan',)
    return ('Europe', 'United Kingdom', 'Germany', 'France', 'Spain', 'Italy', 'Australia')


def index_from_archive(archive, platform=PLATFORM):
    """Stream the large XML, retaining one platform's titles and front cartridge records."""
    games, images = {}, []
    psx = platform in (PLATFORMS['psx'],PLATFORMS['dreamcast'],PLATFORMS['psp'])
    kinds = ('Disc', 'Disc - Front', 'Fanart - Disc') if psx else ('Cart - Front', 'Fanart - Cart - Front')
    image_fields = ('DatabaseID', 'FileName', 'Region', 'Type') + (('Disc',) if psx else ())
    with zipfile.ZipFile(archive) as z, z.open('Metadata.xml') as f:
        depth = 0
        for event, element in ET.iterparse(f, events=('start', 'end')):
            if event == 'start':
                depth += 1
                if depth == 1:
                    root = element
                continue
            if depth == 2:
                fields = {child.tag: child.text or '' for child in element}
                ident = fields.get('DatabaseID')
                if element.tag == 'Game' and fields.get('Platform') == platform:
                    games[ident] = [fields['Name']]
                elif element.tag == 'GameAlternateName' and ident in games:
                    games[ident].append(fields['AlternateName'])
                elif (element.tag == 'GameImage' and ident in games
                      and fields.get('Type') in kinds):
                    images.append({k: fields.get(k, '') for k in image_fields})
                root.clear()
            depth -= 1
    return {'games': games, 'images': images}


def image_bytes(data):
    """Discard invalid ancillary PNG metadata, preserving every image-data byte.

    Some public cartridge PNGs contain a colour-profile chunk with a bad checksum.
    PNG allows ancillary metadata to be ignored; damaged critical chunks still fail.
    """
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return data
    chunks, offset = [data[:8]], 8
    while offset+12 <= len(data):
        length = struct.unpack_from('>I',data,offset)[0]
        end = offset+12+length
        if end > len(data):
            raise ValueError('truncated cartridge PNG')
        kind = data[offset+4:offset+8]
        expected = struct.unpack_from('>I',data,end-4)[0]
        valid = zlib.crc32(data[offset+4:end-4]) & 0xffffffff == expected
        if valid:
            chunks.append(data[offset:end])
        elif kind not in (b'iCCP',b'tEXt',b'zTXt',b'iTXt',b'eXIf',b'pHYs',b'tIME'):
            # Ancillary chunks such as tRNS/fdAT also carry pixel information.
            raise ValueError('damaged cartridge PNG image data')
        offset = end
        if kind == b'IEND':
            return b''.join(chunks)
    raise ValueError('incomplete cartridge PNG')


def label_crop(image, region, platform='snes'):
    """Extract the printed well, excluding the photographed plastic and bevel.

    Fractions are calibrated against front-on regional Game Pak photographs.
    Reject tilted/portrait media rather than putting a whole cart on a label.
    """
    image = ImageOps.exif_transpose(image).convert('RGBA')
    if platform=='psp':
        bounds=image.getchannel('A').getbbox()
        if not bounds:raise ValueError('empty UMD scan')
        image=image.crop(bounds);w,h=image.size
        if not .90<=w/h<=1.08:raise ValueError('UMD scan must be front-on')
        # Public UMD front scans include the white casing. Extract only the
        # circular print; our own plastic is applied once, outside this crop.
        crop=image.crop((round(w*.055),round(h*.055),round(w*.958),round(h*.945)))
        return crop.resize((648,648),Image.Resampling.LANCZOS)
    if platform in ('psx','dreamcast'):
        if not .97<=image.width/image.height<=1.03:raise ValueError('disc scan must be square')
        return image.resize((648,648),Image.Resampling.LANCZOS)
    bounds = image.getchannel('A').getbbox()
    if not bounds:
        raise ValueError('empty cartridge image')
    image = image.crop(bounds)
    w, h = image.size
    if platform == 'nds':
        if not .85 <= w/h <= .97:
            raise ValueError('not a front-on DS game card')
        # Locate the pale branding strip: scan border widths vary, and a fixed
        # top inset clips Nintendo DS letters on some front-on photographs.
        left,right=round(w*.15),round(w*.85)
        candidates=[]
        for y in range(round(h*.04),round(h*.14)):
            bright=sum(min(image.getpixel((x,y))[:3])>145 and image.getpixel((x,y))[3]>240
                       for x in range(left,right))
            if bright/(right-left)>.70:candidates.append(y)
        top=next((y for y in candidates if y+1 in candidates),round(h*.094))
        box = (.073, top/h, .927, .885)
    elif platform == 'nes':
        if not .84 <= w/h <= .96:
            raise ValueError('not a front-on NES Game Pak')
        box = (.402, .006, .865, .684)
    elif platform == 'n64':
        if not 1.38 <= w/h <= 1.66:
            raise ValueError('not a front-on N64 Game Pak')
        box = (.260, .108, .742, .914)
    elif platform == 'md':
        if 1.0 <= w/h <= 1.23:
            # Tall Electronic Arts body: keep the entire printed label, including
            # its publisher strip, but omit the separate yellow plastic grip.
            box = (.213, .011, .923, .831)
        elif 1.43 <= w/h <= 1.68:
            box = (.129, .016, .858, .872) if region == 'Japan' else (.145, .012, .86, .910)
        else:
            raise ValueError('not a front-on Mega Drive cartridge')
    else:
        if not 1.34 <= w/h <= 1.68:
            raise ValueError('not a front-on SNES cartridge')
        box = (.19, .004, .815, .45) if region == 'North America' else (.085, .055, .93, .478)
    label = image.crop(tuple(round(v*n) for v, n in zip(box, (w, h, w, h))))
    # Rounded scan corners become the renderer's plastic; do not retain transparency
    # or include the outside edge of the source cartridge in the label.
    ground = Image.new('RGB', label.size, (15, 15, 17))
    ground.paste(label, mask=label.getchannel('A'))
    limit = (360, 720) if platform in ('nes', 'n64', 'nds') else (720, 360)
    return ImageOps.contain(ground, limit, Image.Resampling.LANCZOS)


class LaunchBox:
    def __init__(self, cache, offline=False, platform='snes'):
        self.platform = platform
        self.platform_name = PLATFORMS[platform]
        self.crop_version = {'nes': NES_CROP_VERSION, 'n64': N64_CROP_VERSION,
                             'md': MD_CROP_VERSION, 'psx': PSX_CROP_VERSION, 'psp': 1, 'nds': 2}.get(platform, CROP_VERSION)
        self.cache = Path(cache)/'launchbox'
        self.cache.mkdir(parents=True, exist_ok=True)
        self.offline = offline
        self.locks = defaultdict(Lock)
        self.index = self._load_index()
        self.names = {}
        for ident, names in self.index.get('games', {}).items():
            for name in names:
                self.names.setdefault(title_key(name), set()).add(ident)
        self.images = {}
        for image in self.index.get('images', []):
            self.images.setdefault(image['DatabaseID'], []).append(image)

    def _load_index(self):
        path = self.cache/(self.platform+'.json')
        fresh = path.exists() and time.time()-path.stat().st_mtime < MAX_AGE
        archive = self.cache/'Metadata.zip'
        if (not self.offline and not fresh) or (not path.exists() and archive.exists()):
            print('Refreshing LaunchBox cartridge metadata...')
            download = archive.with_suffix('.zip.part')
            try:
                archive_fresh = archive.exists() and time.time()-archive.stat().st_mtime < MAX_AGE
                if not self.offline and not archive_fresh:
                    request = urllib.request.Request(METADATA, headers={'User-Agent': AGENT})
                    with urllib.request.urlopen(request, timeout=60) as response, download.open('wb') as f:
                        shutil.copyfileobj(response, f)
                    # Validate this platform before replacing a usable cached archive.
                    index = index_from_archive(download, self.platform_name)
                    os.replace(download, archive)
                else:
                    index = index_from_archive(archive, self.platform_name)
                tmp = path.with_suffix('.part')
                tmp.write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')
                os.replace(tmp, path)
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as ex:
                print('LaunchBox metadata unavailable; using cached art:', ex)
            finally:
                download.unlink(missing_ok=True)
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def candidates(self, game):
        for name in (clean_title(game.stem), game.title):
            hits = self.names.get(title_key(name), set())
            if len(hits) != 1:
                continue
            images = self.images.get(next(iter(hits)), [])
            wanted=regions(game.stem,self.platform)
            kinds=('Cart - Front','Fanart - Cart - Front')
            if self.platform in ('psx','dreamcast','psp'):
                from . import discs
                wanted=discs.region(game);kinds=('Disc','Disc - Front','Fanart - Disc')
                number=discs.number(game.stem)
                if number:
                    images=[i for i in images if str(number)==(i.get('Disc') or str(DISC_NUMBERS.get(i['FileName'],'')))]
            return [dict(image, cropVersion=self.crop_version) for region in wanted
                    for kind in kinds for image in images
                    if image['Region'] == region and image.get('Type', 'Cart - Front') == kind
                    and (not self.offline or self.label_path(image).exists())]
        return []

    def label_path(self, image):
        prefix = self.platform+'-' if self.platform in ('nes', 'n64', 'md','psx','dreamcast','psp','nds') else ''
        return self.cache/'labels'/('%s%d-%s.png' % (prefix, self.crop_version, Path(image['FileName']).stem))

    def fetch(self, image):
        filename = image['FileName']
        # Metadata is external data, never a local path.
        if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(png|jpg|jpeg)', filename, re.IGNORECASE):
            return None
        # Regional revisions of one ROM often share an image. One download per
        # image prevents concurrent workers from replacing the same .part file.
        with self.locks[filename]:
            return self._fetch(image)

    def _fetch(self, image):
        filename = image['FileName']
        path = self.label_path(image)
        if path.exists():
            return path
        if self.offline:
            return None
        try:
            request = urllib.request.Request(IMAGES+filename, headers={'User-Agent': AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                with Image.open(BytesIO(image_bytes(response.read()))) as source:
                    label = label_crop(source, image['Region'], self.platform)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix('.part')
            label.save(tmp, 'PNG')
            os.replace(tmp, path)
            path.with_suffix('.json').write_text(json.dumps(dict(image, url=IMAGES+filename,
                                                               platform=self.platform, cropVersion=self.crop_version)))
            return path
        except (OSError, ValueError) as ex:
            print('Cart label unavailable:', filename, ex)
            return None
