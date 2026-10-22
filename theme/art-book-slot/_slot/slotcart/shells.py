"""Which outline and plastic a game's cart has.

Order: cart_shell.ini override, then the per-game table below, then the hardware default from the
ROM header (GB/GBC by the CGB flag, GBA charcoal). cart_shell.ini uses Cart Studio's format, one
`<rom stem> = <auto|notched|rounded> <rrggbb> <solid|clear|glitter>` per line, so a file written
for Slot works here too.
"""
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Shell:
    colour: tuple
    finish: str = 'solid'  # solid | clear | glitter


GBA_CHARCOAL = Shell((0x35, 0x35, 0x3a))
GBA_VIDEO = Shell((0xc6, 0xc6, 0xc9))
DMG_GREY = Shell((0x9a, 0x97, 0x8f))
DUAL_BLACK = Shell((0x33, 0x30, 0x31))
CGB_CLEAR = Shell((0x7c, 0x7a, 0x8a), 'clear')
SNES_GREY = Shell((0xb8, 0xb7, 0xb5))
SNES_US_GREY = Shell((0xac, 0xaa, 0xb6))
NES_GREY = Shell((0x95, 0x95, 0x98))
NES_GOLD = Shell((0xb2, 0x8c, 0x3e))
N64_GREY = Shell((0x9f, 0x9f, 0xa2))
N64_YELLOW = Shell((0xda, 0xb5, 0x20))
N64_GOLD = Shell((0xb2, 0x96, 0x4e), 'glitter')
N64_BLACK = Shell((0x27, 0x27, 0x2c))
N64_GREEN = Shell((0x1b, 0x85, 0x48))
N64_RED = Shell((0xb2, 0x2f, 0x30))
MD_BLACK = Shell((0x23, 0x23, 0x25))
NDS_GREY = Shell((0x3c, 0x3e, 0x42))
NDS_IR_BLACK = Shell((0x20, 0x21, 0x25))
PICO_GREY = Shell((0x5f,0x57,0x4f))

# North American front plastics checked against regional Cart - Front records.
# Other releases use the grey default unless the user supplies an override.
N64_US_SHELLS = {
    'donkey kong 64': N64_YELLOW,
    'pokemon stadium 2': N64_GOLD,
    'pokémon stadium 2': N64_GOLD,
    "army men - sarge's heroes 2": N64_GREEN,
    'battletanx - global assault': N64_GREEN,
    'rayman 2 - the great escape': Shell((0x26,0xb2,0x40)),
    'scooby-doo! - classic creep capers': N64_BLACK,
    "tony hawk's pro skater 2": N64_YELLOW,
    "tony hawk's pro skater 3": N64_BLACK,
    'turok 2 - seeds of evil': N64_BLACK,
    'turok 3 - shadow of oblivion': N64_BLACK,
    'spider-man': N64_RED,
    "legend of zelda, the - majora's mask": Shell((0xb2,0x94,0x35)),
    "the legend of zelda - majora's mask": Shell((0xb2,0x94,0x35)),
}


def hexrgb(s):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


# Carts that shipped in their own plastic, by game code (first three letters; region-free).
GBA_CODES = {
    'AXV': Shell(hexrgb('c2332e'), 'clear'),   # Pokémon Ruby
    'AXP': Shell(hexrgb('2f5cc0'), 'clear'),   # Pokémon Sapphire
    'BPE': Shell(hexrgb('249c60'), 'clear'),   # Pokémon Emerald
    'BPR': Shell(hexrgb('d85224'), 'clear'),   # Pokémon FireRed
    'BPG': Shell(hexrgb('63b044'), 'clear'),   # Pokémon LeafGreen
    'U3I': Shell(hexrgb('d9dbd8'), 'clear'),   # Boktai (solar sensor)
    'U32': Shell(hexrgb('d9dbd8'), 'clear'),   # Boktai 2
    'U33': Shell(hexrgb('d9dbd8'), 'clear'),   # Boktai 3
    'V49': Shell(hexrgb('a9513b')),            # Drill Dozer (rumble)
    'KYG': Shell(hexrgb('2f8f4e')),            # Yoshi Topsy-Turvy (tilt)
}
GB_CODES = {
    'AAU': Shell(hexrgb('b38b3a')),            # Pokémon Gold
    'AAX': Shell(hexrgb('a9aaa7')),            # Pokémon Silver
    'BYT': Shell(hexrgb('86b9bf'), 'glitter'), # Pokémon Crystal
    'KTN': Shell(hexrgb('ec94b4'), 'clear'),   # Kirby Tilt 'n' Tumble
}
GB_TITLES = {
    'POKEMON RED': Shell(hexrgb('c0282c')),
    'POKEMON BLUE': Shell(hexrgb('2b3a88')),
    'POKEMON YELLOW': Shell(hexrgb('e9a826')),
    'POKEMON GREEN': Shell(hexrgb('3f8f4a')),
}


@dataclass(frozen=True)
class Header:
    platform: str          # gb | gba | snes | nes | n64 | md
    title: str = ''
    code: str = ''         # GBA game code, or the GB manufacturer code when present
    cgb: int = 0           # GB 0x143: 0x80 dual mode, 0xC0 Game Boy Color only


def read_header(platform, head):
    if platform == 'nds':
        if len(head) < 0x12: return Header('nds')
        text = lambda b: b.split(b'\0')[0].decode('ascii', 'replace').strip()
        code = text(head[0x0c:0x10])
        if not re.fullmatch('[A-Z0-9]{4}', code): code = ''
        return Header('nds', text(head[:12]), code)
    if platform in ('psp','dreamcast','pico8'):
        return Header(platform)
    """`head` is the first 0x150 bytes of the ROM."""
    text = lambda b: b.split(b'\0')[0].decode('ascii', 'replace').strip()
    if platform == 'psx':
        return Header('psx', code=text(head))
    if platform == 'md':
        # Raw .md/.bin dumps have the domestic title at 0x120. Copier dumps
        # remain MD carts even without a readable header; filenames drive style.
        return Header('md', text(head[0x120:0x150]) if head[0x100:0x104] == b'SEGA' else '')
    if platform == 'n64':
        # N64 dumps occur in big-endian, byte-swapped and little-endian order.
        if head[:4] == b'\x37\x80\x40\x12':
            head = b''.join(head[i:i+2][::-1] for i in range(0, len(head)-1, 2))
        elif head[:4] == b'\x40\x12\x37\x80':
            head = b''.join(head[i:i+4][::-1] for i in range(0, len(head)-3, 4))
        return Header('n64', text(head[0x20:0x34]) if head[:4] == b'\x80\x37\x12\x40' else '')
    if platform in ('snes', 'nes'):
        return Header(platform)  # Console cart styles use the ROM filename in choose().
    if platform == 'gba':
        return Header('gba', text(head[0xA0:0xAC]), text(head[0xAC:0xB0]))
    if len(head) < 0x150:
        return Header('gb')
    cgb = head[0x143]
    if cgb in (0x80, 0xC0):
        title, code = text(head[0x134:0x13F]), text(head[0x13F:0x143])
        if not (len(code) == 4 and code.isalnum() and code.isupper()):
            title, code = text(head[0x134:0x143]), ''
    else:
        title, code = text(head[0x134:0x144]), ''
    return Header('gb', title, code, cgb if cgb in (0x80, 0xC0) else 0)


def outline_for(header):
    """gba, gb (notched: original and dual mode) or gbc (rounded: Game Boy Color only)."""
    if header.platform == 'gba':
        return 'gba'
    if header.platform in ('snes', 'nes', 'n64', 'md', 'psx', 'dreamcast', 'psp', 'nds', 'pico8'):
        return header.platform
    return 'gbc' if header.cgb == 0xC0 else 'gb'


def default_shell(header):
    if header.platform == 'pico8':
        return PICO_GREY
    if header.platform == 'nds':
        return NDS_IR_BLACK if header.code.startswith('I') else NDS_GREY
    if header.platform == 'md':
        return MD_BLACK
    if header.platform == 'n64':
        return N64_GREY
    if header.platform == 'nes':
        return NES_GREY
    if header.platform == 'snes':
        return SNES_GREY
    if header.platform == 'gba':
        if header.code.startswith('M'):  # Game Boy Advance Video
            return GBA_VIDEO
        return GBA_CODES.get(header.code[:3], GBA_CHARCOAL)
    if header.code[:3] in GB_CODES:
        return GB_CODES[header.code[:3]]
    if header.title in GB_TITLES:
        return GB_TITLES[header.title]
    return {0x80: DUAL_BLACK, 0xC0: CGB_CLEAR}.get(header.cgb, DMG_GREY)


def key(stem):
    return unicodedata.normalize('NFC', stem)


def parse_overrides(text):
    """cart_shell.ini -> {stem: (outline or None, Shell)}; 'auto' entries are skipped."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ';#[' or '=' not in line:
            continue
        stem, _, value = line.partition('=')
        words = value.split()
        if len(words) != 3 or words[0] not in ('auto', 'notched', 'rounded'):
            continue
        outline, colour, finish = words
        if len(colour) != 6 or finish not in ('solid', 'clear', 'glitter'):
            continue
        try:
            shell = Shell(hexrgb(colour), finish)
        except ValueError:
            continue
        out[key(stem.strip())] = ({'notched': 'gb', 'rounded': 'gbc'}.get(outline), shell)
    return out


def choose(header, stem, overrides):
    """(outline, Shell) for one game."""
    outline, shell = outline_for(header), default_shell(header)
    if header.platform == 'md':
        tags = ' '.join(re.findall(r'\(([^)]*)\)', stem))
        if re.search(r'\bJapan\b', tags, re.I) and not re.search(r'\b(?:USA|Europe|World)\b', tags, re.I):
            outline = 'md-jp'
        title = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', stem).replace('_', ' ').strip().lower()
        # Verified EA moulding for this library title, including its yellow grip.
        if title == 'blades of vengeance':
            outline = 'md-ea'
    if header.platform == 'snes':
        tags = ' '.join(re.findall(r'\(([^)]*)\)', stem))
        if re.search(r'\b(?:USA|Canada|North America)\b', tags, re.I):
            outline, shell = 'snes-us', SNES_US_GREY
    if header.platform == 'nes':
        title = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', stem).replace('_', ' ').strip().lower()
        # Both licensed Zelda games shipped in the standard Game Pak shape in gold.
        if title in ('legend of zelda, the', 'the legend of zelda', 'zelda ii - the adventure of link',
                     'zelda ii: the adventure of link'):
            shell = NES_GOLD
    if header.platform == 'n64':
        title = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', stem).replace('_', ' ').strip().lower()
        tags = ' '.join(re.findall(r'\(([^)]*)\)', stem))
        if re.search(r'\b(?:USA|Canada|North America)\b', tags, re.I):
            shell = N64_US_SHELLS.get(title,shell)
    if key(stem) in overrides:
        forced, shell = overrides[key(stem)]
        if forced and header.platform == 'gb':
            outline = forced
    return outline, shell
