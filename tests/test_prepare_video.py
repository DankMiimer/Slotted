"""Real decoder/encoder contract for source-preserving pixel-aspect correction."""
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.dev.prepare_video import prepare, probe, square_pixels


class PreviewVideoTests(unittest.TestCase):
    def test_target_ratios_preserve_display_aspect_within_one_even_pixel(self):
        for width,height,sar in ((720,480,Fraction(8,9)), (320,480,Fraction(2)),
                                  (720,576,Fraction(16,15)), (241,321,Fraction(3,2))):
            w,h = square_pixels(width,height,sar)
            self.assertEqual((w%2,h%2),(0,0))
            self.assertLess(abs(w/h-float(Fraction(width,height)*sar)),2/h)
        with self.assertRaises(ValueError):
            square_pixels(320,480,Fraction(0))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg/ffprobe unavailable')
    def test_real_preview_keeps_original_and_refuses_output_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'original.mp4'
            preview = Path(folder)/'preview.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi',
                '-i','testsrc2=size=320x240:rate=10','-t','0.2','-vf','setsar=2',
                '-an','-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True)
            original = source.read_bytes()
            self.assertFalse(prepare(source,preview)['copied'])
            self.assertEqual(probe(preview),(640,240,Fraction(1)))
            self.assertEqual(source.read_bytes(),original)
            result = preview.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(source,preview)
            self.assertEqual(preview.read_bytes(),result)
            copied = Path(folder)/'copy.mp4'
            self.assertTrue(prepare(preview,copied)['copied'])
            self.assertEqual(copied.read_bytes(),result)
            self.assertEqual(list(Path(folder).glob('*.preparing-*')),[])


if __name__ == '__main__':
    unittest.main()
