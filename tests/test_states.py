"""State photos choose the latest exact ROM match and leave original saves untouched."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'theme/art-book-slot/_slot'))
states = importlib.import_module('slotcart.states')


class StatePhotos(unittest.TestCase):
    def test_latest_exact_match_cache_invalidation_and_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            roms, saves = root / 'roms', root / 'saves'
            rom = roms / 'gba' / 'Game.gba'
            rom.parent.mkdir(parents=True)
            rom.touch()
            source = saves / 'gba'
            source.mkdir(parents=True)
            for name, colour, timestamp in [('Game.state1.png', 'red', 1),
                                             ('Game.state.auto.png', 'blue', 2),
                                             ('Game Extra.state1.png', 'green', 3),
                                             ('Game.stateother.png', 'green', 3)]:
                path = source / name
                Image.new('RGB', (240, 160), colour).save(path)
                os.utime(path, (timestamp, timestamp))
            originals = {p.name: p.read_bytes() for p in source.iterdir()}
            self.assertTrue(states.refresh(rom, saves, roms))
            output = rom.parent / 'media/slotstates/Game.png'
            self.assertEqual(Image.open(output).getpixel((80, 60))[:3], (0, 0, 255))
            timestamp = output.stat().st_mtime_ns
            states.refresh(rom, saves, roms)
            self.assertEqual(output.stat().st_mtime_ns, timestamp)
            os.utime(source / 'Game.state1.png', (4, 4))
            states.refresh(rom, saves, roms)
            self.assertEqual(Image.open(output).getpixel((80, 60))[:3], (255, 0, 0))
            self.assertEqual(originals, {p.name: p.read_bytes() for p in source.iterdir()})
            (source / 'Game.state1.png').unlink()
            (source / 'Game.state.auto.png').unlink()
            self.assertFalse(states.refresh(rom, saves, roms))
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.json').exists())


if __name__ == '__main__':
    unittest.main()
