"""Preserve display aspect in a square-pixel preview copy for Scarab's VLC player.

The installed frontend ignores source SAR. This corrects pixel interpretation;
it never overwrites a source or edits the gamelist. Point test metadata at the
returned copy. Ordinary square-pixel clips are copied without re-encoding.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,sample_aspect_ratio', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)['streams'][0]
    ratio = stream.get('sample_aspect_ratio', '1:1')
    sar = Fraction(ratio.replace(':','/')) if ratio not in ('N/A', '0:1') else Fraction(1)
    return int(stream['width']), int(stream['height']), sar


def square_pixels(width, height, sar):
    if not 0 < width <= 8192 or not 0 < height <= 8192 or not Fraction(1,8) <= sar <= 8:
        raise ValueError('Unsupported preview dimensions/pixel aspect')
    # Same physical height; width now counts square pixels instead of stored
    # rectangular pixels. Even dimensions are required by the yuv420p encoder.
    out_height = math.ceil(height/2)*2
    out_width = math.ceil(float(Fraction(width,height)*sar*out_height)/2)*2
    return out_width, out_height


def prepare(source, target):
    source, target = Path(source), Path(target)
    if target.exists() or target.resolve() == source.resolve():
        raise FileExistsError('Keep existing files: ' + str(target))
    width,height,sar = probe(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    out_width,out_height = square_pixels(width,height,sar)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.stem+'.preparing-',
                                     suffix='.mp4',delete=False) as staged:
        temporary = Path(staged.name)
    try:
        if sar == 1:
            shutil.copy2(source,temporary)
        else:
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-i',str(source),'-map','0:v:0','-map','0:a?',
                '-vf','scale=%d:%d:flags=lanczos,setsar=1' % (out_width,out_height),
                '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',
                '-c:a','copy','-movflags','+faststart',str(temporary)], check=True)
            actual_width,actual_height,actual_sar = probe(temporary)
            if (actual_width,actual_height,actual_sar) != (out_width,out_height,Fraction(1)):
                raise ValueError('Preview output did not preserve the requested display aspect')
        # Hard linking publishes without replacing a file created concurrently.
        target.hardlink_to(temporary)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(source=str(source), preview=str(target), copied=sar==1,
                original_sar=str(sar), dimensions=[out_width,out_height])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('preview',type=Path)
    options = parser.parse_args()
    print(json.dumps(prepare(options.source,options.preview)))
