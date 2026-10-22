"""Finds the games: ROM files, their CRC32 and header, and what ES has scraped for them.

Reading every ROM for its CRC is the slow part (about 40 s for 1,200 GB/GBC games on an
RG34XXSP), so results are cached by path, size and modification time.
"""
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from .shells import read_header

# ES system folder -> shelf kind. Hack and variant systems share the shelves.
SYSTEMS = {'gba': 'gba', 'gbah': 'gba', 'gb': 'gb', 'gbh': 'gb', 'gbc': 'gbc', 'gbch': 'gbc',
           'snes': 'snes', 'snesh': 'snes', 'nes': 'nes', 'nesh': 'nes', 'n64': 'n64', 'n64h': 'n64',
           'megadrive': 'md', 'genesis': 'md', 'psx': 'psx', 'dreamcast': 'dreamcast', 'psp': 'psp', 'nds': 'nds', 'pico8': 'pico8'}
EXTENSIONS = {'gba': ('.gba', '.agb'), 'gb': ('.gb', '.gbc', '.sgb'), 'gbc': ('.gbc', '.gb', '.sgb'),
              'snes': ('.sfc', '.smc'), 'nes': ('.nes', '.unf', '.unif'), 'n64': ('.z64', '.v64', '.n64'),
              'md': ('.md', '.bin', '.gen', '.smd'), 'dreamcast': ('.chd', '.gdi', '.cdi', '.cue', '.m3u'), 'psx': ('.chd', '.cue', '.bin', '.iso', '.img', '.pbp'),
              'psp': ('.iso', '.cso', '.pbp'), 'nds': ('.nds',), 'pico8': ('.png','.p8','.m3u')}
SKIP_DIRS = {'images', 'videos', 'media', 'manuals', 'downloaded_images', 'downloaded_videos'}
HEAD = 0x150


@dataclass
class Game:
    system: str        # ES system folder name, e.g. gbch
    kind: str          # gba | gb | gbc | snes | nes | n64 | md
    path: Path
    stem: str
    title: str
    marquee: str
    crc: str
    head: bytes

    @property
    def dir(self):
        return self.path.parent

    @property
    def header(self):
        return read_header('gb' if self.kind == 'gbc' else self.kind, self.head)


def clean_title(stem):
    """'Legend of Zelda, The (USA) [!]' -> 'Legend of Zelda, The'."""
    bare = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', stem).strip()
    return ' '.join(w for w in bare.split() if w != '-') or stem


def read_rom(path, exts):
    """(crc, head) of a ROM, looking inside a .zip for the first ROM entry."""
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(exts)]
            if not names:
                return None, b''
            data = z.read(names[0])
        return '%08X' % (zlib.crc32(data) & 0xffffffff), data[:HEAD]
    crc = 0
    with open(path, 'rb') as f:
        head = f.read(HEAD)
        crc = zlib.crc32(head, crc)
        for block in iter(lambda: f.read(1 << 20), b''):
            crc = zlib.crc32(block, crc)
    return '%08X' % (crc & 0xffffffff), head


def gamelist(system_dir):
    """{rom path: (name, marquee path)} from ES's gamelist.xml, if there is one."""
    out = {}
    path = system_dir / 'gamelist.xml'
    if not path.exists():
        return out
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return out
    for game in root.iter('game'):
        rel = (game.findtext('path') or '').strip()
        if not rel:
            continue
        marquee = (game.findtext('marquee') or '').strip()
        out[str((system_dir / rel).resolve())] = (
            (game.findtext('name') or '').strip(),
            str((system_dir / marquee).resolve()) if marquee else '')
    return out


class CrcCache:
    def __init__(self, cache_dir):
        self.path = Path(cache_dir) / 'roms.json'
        try:
            self.data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.data = {}
        self.identities_path=Path(cache_dir)/'psx-identities.json'
        try:self.identities=json.loads(self.identities_path.read_text())
        except (OSError,ValueError):self.identities={}

    def get(self, path, exts):
        if '.gdi' in exts:
            # Dreamcast labels use filenames/regions. Never hash a GD-ROM or
            # apply the PlayStation boot-sector/serial reader to its tracks.
            return '', b''
        if '.p8' in exts:
            # Artwork is already inside a local PNG/text cartridge. No CRC,
            # decompression or game-code evaluation is needed for its identity.
            return '',b''
        if exts == ('.nds',):
            # DS labels use titles/regions and the bounded game-code header.
            # Avoid hashing hundreds of megabytes just to draw a game card.
            if path.suffix.lower() == '.zip':
                with zipfile.ZipFile(path) as archive:
                    entries = [n for n in archive.namelist() if n.lower().endswith(exts)]
                    if not entries: return None, b''
                    with archive.open(entries[0]) as stream: return '', stream.read(HEAD)
            with path.open('rb') as stream: return '', stream.read(HEAD)
        if '.cso' in exts:
            # UMD identity comes from the region-tagged filename. Never CRC a
            # gigabyte ISO, decompress a CSO, or mistake a PBP for a handheld ROM.
            with path.open('rb') as f: return '', f.read(HEAD)
        if '.chd' in exts:
            from .discs import identify
            if path.stat().st_size==0:return None,b''
            return '',identify(path,self.identities)
        st = path.stat()
        key = str(path)
        hit = self.data.get(key)
        if hit and hit[0] == st.st_size and hit[1] == int(st.st_mtime):
            return hit[2], bytes.fromhex(hit[3])
        crc, head = read_rom(path, exts)
        self.data[key] = [st.st_size, int(st.st_mtime), crc, head.hex()]
        return crc, head

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.part')
        tmp.write_text(json.dumps(self.data))
        os.replace(tmp, self.path)
        tmp=self.identities_path.with_suffix('.part');tmp.write_text(json.dumps(self.identities))
        os.replace(tmp,self.identities_path)


def scan(roms_root, systems, cache):
    games = []
    for system in systems:
        kind = SYSTEMS[system]
        exts = EXTENSIONS[kind]
        system_dir = Path(roms_root) / system
        if not system_dir.is_dir():
            continue
        scraped = gamelist(system_dir)
        for dirpath, dirnames, filenames in os.walk(system_dir):
            dirnames[:] = sorted(d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith('.'))
            for name in sorted(filenames):
                path = Path(dirpath) / name
                if not name.lower().endswith(exts + (() if kind in ('psx','dreamcast','psp','pico8') else ('.zip',))):
                    continue
                crc, head = cache.get(path, exts)
                if crc is None:
                    continue
                title, marquee = scraped.get(str(path.resolve()), ('', ''))
                if kind == 'nes' and title == '#NONGAME':
                    # Scrapers use this for diagnostic/homebrew ROMs. A cartridge
                    # still needs its own title, rather than 21 identical labels.
                    title = clean_title(path.stem).replace('_', ' ')
                games.append(Game(system, kind, path, path.stem, title or clean_title(path.stem),
                                  marquee, crc, head))
    return games
