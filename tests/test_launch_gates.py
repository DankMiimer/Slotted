"""Run with sh (or copy to the device with SLOT_GATE_SOURCE pointing at common.sh)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(os.environ.get('SLOT_GATE_SOURCE', str(
    Path(__file__).resolve().parents[1] / 'theme/art-book-slot/_slot/launch/common.sh')))


@unittest.skipUnless(shutil.which('sh'), 'requires a POSIX shell; also run on the device')
class LaunchGates(unittest.TestCase):
    def test_theme_system_view_and_subset_settings(self):
        cases = [
            ('defaults', 'gba', {}, '', True),
            ('gb', 'gb', {}, '', True),
            ('gbc', 'gbc', {}, '', True),
            ('hack alias', 'gbch', {}, 'subset.slot-gbc=off\r', False),
            ('snes', 'snes', {}, '', True),
            ('snes disabled', 'snes', {'subset.slot-snes': 'off'}, '', False),
            ('snes hack disabled', 'snesh', {}, 'subset.slot-snes=off\r', False),
            ('nes', 'nes', {}, '', True),
            ('nes disabled', 'nes', {'subset.slot-nes': 'off'}, '', False),
            ('nes hack disabled', 'nesh', {}, 'subset.slot-nes=off\r', False),
            ('n64', 'n64', {}, '', True),
            ('n64 disabled', 'n64', {'subset.slot-n64': 'off'}, '', False),
            ('n64 hack disabled', 'n64h', {}, 'subset.slot-n64=off\r', False),
            ('megadrive', 'megadrive', {}, '', True),
            ('megadrive disabled', 'megadrive', {'subset.slot-megadrive': 'off'}, '', False),
            ('genesis alias disabled', 'genesis', {}, 'subset.slot-megadrive=off\r', False),
            ('genesis alias', 'genesis', {}, '', True),
            ('psx', 'psx', {}, '', True),
            ('psx disabled', 'psx', {'subset.slot-psx': 'off'}, '', False),
            ('psx profile disabled', 'psx', {}, 'subset.slot-psx=off\r', False),
            ('psx system disabled', 'psx', {'subset.psx.slot-psx': 'off'}, '', False),
            ('psp', 'psp', {}, '', True),
            ('psp disabled', 'psp', {'subset.slot-psp': 'off'}, '', False),
            ('psp profile disabled', 'psp', {}, 'subset.slot-psp=off\r', False),
            ('psp system disabled', 'psp', {'subset.psp.slot-psp': 'off'}, '', False),
            ('nds', 'nds', {}, '', True),
            ('nds disabled', 'nds', {'subset.slot-nds': 'off'}, '', False),
            ('nds profile disabled', 'nds', {}, 'subset.slot-nds=off\r', False),
            ('nds system disabled', 'nds', {'subset.nds.slot-nds': 'off'}, '', False),
            ('pico8', 'pico8', {}, '', True),
            ('pico8 disabled', 'pico8', {'subset.slot-pico8': 'off'}, '', False),
            ('pico8 profile disabled', 'pico8', {}, 'subset.slot-pico8=off\r', False),
            ('pico8 system disabled', 'pico8', {'subset.pico8.slot-pico8': 'off'}, '', False),
            ('unrelated system', 'atari2600', {}, '', False),
            ('stock theme', 'gba', {'ThemeSet': 'es-theme-art-book-next'}, '', False),
            ('shelf off', 'gba', {'subset.slot-gba': 'off'}, '', False),
            ('profile off', 'gba', {}, 'subset.slot-gba=off\r', False),
            ('live beats profile', 'gba', {'subset.slot-gba': 'on'}, 'subset.slot-gba=off\r', True),
            ('system subset', 'gba', {'subset.gba.slot-gba': 'off'}, 'subset.slot-gba=on\r', False),
            ('global detailed', 'gba', {'GamelistViewStyle': 'detailed'}, '', False),
            ('profile detailed', 'gba', {}, 'GamelistViewStyle=detailed\r', False),
            ('system detailed', 'gba', {'gba.defaultView': 'detailed'}, '', False),
            ('system carousel', 'gba', {'gba.defaultView': 'gamecarousel', 'GamelistViewStyle': 'detailed'}, '', True),
            ('profile carousel', 'gba', {}, 'GamelistViewStyle=detailed\rgba.defaultView=gamecarousel\r', True),
            ('LF profile', 'gba', {}, 'subset.slot-wallpaper=on\nsubset.slot-gba=off\n', False),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper, settings, profile = root/'helper', root/'settings', root/'profile'
            helper.touch()
            helper.chmod(0o755)
            for name, system, values, config, expected in cases:
                with self.subTest(name=name):
                    values = {'ThemeSet': 'art-book-slot', **values}
                    settings.write_text('<config>\n' + ''.join(
                        '<string name="%s" value="%s"/>\n' % pair for pair in values.items()) + '</config>')
                    profile.write_bytes(config.encode())
                    result = subprocess.run(['sh', '-c',
                        '. "$1"; SLOT_HELPER="$2"; SLOT_SETTINGS="$3"; SLOT_THEME_SETTINGS="$4"; slot_enabled "$5"',
                        'slot-gate', str(SOURCE), str(helper), str(settings), str(profile),
                        '/userdata/roms/%s/Game.gba' % system], capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, expected, result.stderr)

    def test_early_claim_must_be_fresh_and_for_this_rom(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            uptime = int(float(Path('/proc/uptime').read_text().split()[0]))
            rom = '/userdata/roms/gba/Cart & Friends (Europe).gba'
            cases = [(uptime, rom, rom, True),
                     (uptime, rom, rom.replace(' ', '\\ '), True),
                     (uptime-20, rom, rom, False),
                     (uptime+20, rom, rom, False),
                     ('broken', rom, rom, False),
                     (uptime, rom, '/userdata/roms/gba/Other.gba', False)]
            for stamp, claimed, requested, expected in cases:
                with self.subTest(stamp=stamp, requested=requested):
                    (root/'early').write_text('%s\n%s\n' % (stamp, claimed))
                    result = subprocess.run(['sh', '-c',
                        '. "$1"; SLOT_STATE="$2"; slot_early_insert "$3"',
                        'slot-claim', str(SOURCE), str(root), requested], capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, expected, result.stderr)


if __name__ == '__main__':
    unittest.main()
