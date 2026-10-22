"""Tests for the cart baker's header, shell and label rules.

    python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'theme' / 'art-book-slot' / '_slot'))

from slotcart import labels, shells  # noqa: E402
from slotcart.library import clean_title  # noqa: E402


def gb_head(title, cgb=0x00, code=b''):
    head = bytearray(0x150)
    raw = title.encode('ascii') + code
    head[0x134:0x134 + len(raw)] = raw
    if cgb:
        head[0x143] = cgb
    return bytes(head)


def gba_head(title, code):
    head = bytearray(0x150)
    head[0xA0:0xA0 + len(title)] = title.encode('ascii')
    head[0xAC:0xB0] = code.encode('ascii')
    return bytes(head)


class Headers(unittest.TestCase):
    def test_gba_code(self):
        h = shells.read_header('gba', gba_head('POKEMON EMER', 'BPEE'))
        self.assertEqual((h.title, h.code), ('POKEMON EMER', 'BPEE'))
        self.assertEqual(shells.outline_for(h), 'gba')
        self.assertEqual(shells.default_shell(h), shells.GBA_CODES['BPE'])

    def test_gba_video_family(self):
        h = shells.read_header('gba', gba_head('SHREK', 'MSKE'))
        self.assertEqual(shells.default_shell(h), shells.GBA_VIDEO)

    def test_dmg_title(self):
        h = shells.read_header('gb', gb_head('POKEMON RED'))
        self.assertEqual((h.title, h.cgb), ('POKEMON RED', 0))
        self.assertEqual(shells.outline_for(h), 'gb')
        self.assertEqual(shells.default_shell(h), shells.GB_TITLES['POKEMON RED'])

    def test_title_running_into_code_area(self):
        # Pokemon Yellow is dual mode but its 14-letter title fills the manufacturer code bytes.
        h = shells.read_header('gb', gb_head('POKEMON YELLOW', cgb=0x80))
        self.assertEqual(h.title, 'POKEMON YELLOW')
        self.assertEqual(h.code, '')
        self.assertEqual(shells.default_shell(h), shells.GB_TITLES['POKEMON YELLOW'])

    def test_manufacturer_code(self):
        h = shells.read_header('gb', gb_head('PM_CRYSTAL\0', cgb=0xC0, code=b'BYTE'))
        self.assertEqual((h.title, h.code), ('PM_CRYSTAL', 'BYTE'))
        self.assertEqual(shells.outline_for(h), 'gbc')
        self.assertEqual(shells.default_shell(h).finish, 'glitter')

    def test_colour_only_and_dual_defaults(self):
        only = shells.read_header('gb', gb_head('SOME GAME', cgb=0xC0))
        dual = shells.read_header('gb', gb_head('OTHER GAME', cgb=0x80))
        self.assertEqual((shells.outline_for(only), shells.default_shell(only)), ('gbc', shells.CGB_CLEAR))
        self.assertEqual((shells.outline_for(dual), shells.default_shell(dual)), ('gb', shells.DUAL_BLACK))

    def test_title_bytes_in_flag_position_are_not_a_flag(self):
        # Old carts use 0x143 for the 16th title letter; only 0x80 and 0xC0 mean colour.
        h = shells.read_header('gb', gb_head('ABCDEFGHIJKLMNOE'))
        self.assertEqual(h.cgb, 0)


class Overrides(unittest.TestCase):
    def test_parse_and_choose(self):
        text = ('; comment\n'
                'Tetris (World) = rounded ec94b4 clear\n'
                'Broken = notched zzzzzz solid\n'
                'Auto Game = auto\n')
        table = shells.parse_overrides(text)
        self.assertEqual(set(table), {'Tetris (World)'})
        h = shells.read_header('gb', gb_head('TETRIS'))
        outline, shell = shells.choose(h, 'Tetris (World)', table)
        self.assertEqual((outline, shell), ('gbc', shells.Shell((0xec, 0x94, 0xb4), 'clear')))

    def test_outline_override_ignored_for_gba(self):
        table = shells.parse_overrides('Game = rounded 112233 solid')
        h = shells.read_header('gba', gba_head('GAME', 'AGME'))
        self.assertEqual(shells.choose(h, 'Game', table)[0], 'gba')


class Labels(unittest.TestCase):
    def test_clean_title(self):
        self.assertEqual(clean_title('Legend of Zelda, The - Link\'s Awakening (USA) [!]'),
                         "Legend of Zelda, The Link's Awakening")

    def test_paper_colour_is_stable_and_muted(self):
        class G:
            title = 'Tetris'
        a, b = labels.paper_colour(G), labels.paper_colour(G)
        self.assertEqual(a, b)
        self.assertTrue(max(a) <= round(0.74 * 255))

    def test_ink_contrasts(self):
        self.assertEqual(labels.ink_for((240, 240, 240)), (0x1a, 0x18, 0x16))
        self.assertEqual(labels.ink_for((20, 20, 20)), (0xf4, 0xf1, 0xea))


if __name__ == '__main__':
    unittest.main()
