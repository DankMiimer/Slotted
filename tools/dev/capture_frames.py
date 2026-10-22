#!/usr/bin/env python3
"""Capture framebuffer frames around an action, compressing only after it finishes.

Device usage: capture_frames.py /tmp/insert 2 --period .05 -- python3 esdev.py press a
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import struct
import subprocess
import time

from PIL import Image, ImageDraw, ImageStat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('seconds', type=float)
    parser.add_argument('--period', type=float, default=0.05)
    parser.add_argument('--button', action='append', help='press a button directly; repeat for a chord')
    parser.add_argument('--inspect-cart', choices=('gba', 'gb', 'gbc', 'snes', 'nes', 'n64', 'md', 'psx', 'psp', 'nds', 'pico8'))
    parser.add_argument('--stats-only', action='store_true', help='save row brightness and three representative images')
    parser.add_argument('--display', action='store_true', help='sample composed LCD output through Sunxi writeback')
    parser.add_argument('--display-wait', type=float, default=.04, help='writeback wait; .034 for denser 60-Hz captures')
    parser.add_argument('--capture-scale',type=float,choices=(1,.5),default=1,
                        help='hardware downscale composed capture for a higher sample rate')
    parser.add_argument('--grid-cols', type=int, default=4)
    parser.add_argument('--grid-rows', type=int, default=0, help='paginate contact sheets (0: all frames)')
    parser.add_argument('--thumb-width', type=int, default=360)
    options, command = parser.parse_known_args()
    if command[:1] == ['--']:
        command = command[1:]
    if (not command and not options.button) or (command and options.button) or options.period <= 0 or options.seconds <= 0:
        parser.error('provide a positive duration/period and an action command')
    if options.stats_only and not options.inspect_cart:
        parser.error('--stats-only requires --inspect-cart')
    if options.inspect_cart and options.capture_scale!=1:
        parser.error('cart pixel inspection requires full-size captures')
    if options.grid_cols<1 or options.grid_rows<0 or options.thumb_width<120:
        parser.error('invalid contact sheet dimensions')
    controller = None
    if options.button:
        from esdev import BUTTONS, HAT, pad
        if any(button not in BUTTONS and button not in HAT for button in options.button):
            parser.error('unknown button')
        controller = pad()
    options.output.mkdir(parents=True, exist_ok=True)
    stride = int(Path('/sys/class/graphics/fb0/stride').read_text())
    frames = []
    display = None
    if options.display:
        from sunxi_capture import DisplayCapture
        display = DisplayCapture(options.display_wait,options.capture_scale)
    with open('/dev/fb0', 'rb', buffering=0) as framebuffer:
        info = bytearray(160)
        fcntl.ioctl(framebuffer, 0x4600, info)
        width, height, _, virtual_height, _, _, bpp = struct.unpack_from('7I', info)
        if bpp != 32:
            raise SystemExit('requires a 32-bit framebuffer')
        red, green, blue = (struct.unpack_from('I', info, offset)[0] for offset in (32, 44, 56))
        rawmode = 'BGRX' if (red, green, blue) == (16, 8, 0) else 'RGBX'
        if display:width,height,stride=display.width,display.height,display.stride
        started, child, action_at, released = time.monotonic(), None, None, False
        next_sample = started
        while time.monotonic() - started < options.seconds:
            elapsed = time.monotonic() - started
            if action_at is None and elapsed >= 0.2:
                action_at = time.monotonic()
                if controller:
                    for button in options.button:
                        if button in HAT:
                            axis, value = HAT[button]
                            controller.write(3,axis,value)
                        else:
                            controller.write(1, BUTTONS[button], 1)
                    controller.write(0, 0, 0)
                else:
                    child = subprocess.Popen(command)
            if controller and action_at is not None and not released and time.monotonic() - action_at >= .06:
                for button in reversed(options.button):
                    if button in HAT:
                        controller.write(3,HAT[button][0],0)
                    else:
                        controller.write(1, BUTTONS[button], 0)
                controller.write(0, 0, 0)
                released = True
            # SDL can replace framebuffer storage when ownership changes. An mmap
            # made while ES owns it then points at the retired buffer; read afresh.
            if display:
                # Composed writeback has its own DMA buffer. Querying fb0 on
                # every sample adds a separate display wait for no useful data.
                pixels = display.read()
            else:
                fresh = os.open('/dev/fb0', os.O_RDONLY)
                try:
                    fcntl.ioctl(fresh, 0x4600, info)
                    base = struct.unpack_from('I', info, 20)[0] * stride
                    pixels = os.pread(fresh, height * stride, base)
                finally:
                    os.close(fresh)
            if len(pixels) == height * stride:
                frames.append((time.monotonic()-started, pixels))
            next_sample += options.period
            time.sleep(max(0, next_sample - time.monotonic()))
    if display:
        display.close()
    if child is not None:
        child.wait(timeout=60)
    fps=(len(frames)-1)/(frames[-1][0]-frames[0][0]) if len(frames)>1 else 0
    (options.output / 'timing.json').write_text(json.dumps({'started': started, 'action_at': action_at,
        'requested_fps':1/options.period,'captured_fps':fps,'size':[width,height],'frames': [t for t, _ in frames]}))
    if options.inspect_cart:
        bounds = {'gba': (190,140,530,330), 'gb': (220,52,500,365),
                  'gbc': (220,52,500,365), 'snes': (190,100,530,315),
                  'nes': (212,50,510,310), 'n64': (190,130,530,318),
                  'md': (240,105,490,320), 'psx': (240,100,480,315), 'psp': (240,100,480,315), 'nds': (221,75,499,345), 'pico8': (231,45,489,377)}[options.inspect_cart]
        cart_width, cart_height, foot = {'gba': (360,212,346), 'gb': (312,337,380),
                                      'gbc': (312,337,380), 'snes': (360,245,334),
                                      'nes': (304,337,380), 'n64': (360,241,332),
                                      'md': (360,270,346), 'psx': (336,336,379), 'psp': (336,336,379), 'nds': (312,341,382), 'pico8': (264,338,380)}[options.inspect_cart]
        fractions=((.3,.12),(.7,.12),(.15,.3),(.85,.3),(.1,.5),(.9,.5),(.22,.76),(.78,.76)) if options.inspect_cart=='psx' else ((.3,.08),(.7,.08),(.1,.2),(.9,.2),(.08,.45),(.92,.45),(.2,.95),(.8,.95))
        if options.inspect_cart=='psp': fractions=((.3,.12),(.7,.12),(.15,.3),(.85,.3),(.1,.5),(.9,.5),(.18,.84),(.82,.84))
        if options.inspect_cart=='nds': fractions=((.35,.04),(.65,.04),(.025,.20),(.975,.20),(.025,.60),(.975,.60),(.22,.955),(.78,.955))
        if options.inspect_cart=='pico8': fractions=((.30,.08),(.70,.08),(.04,.20),(.96,.20),(.04,.60),(.96,.60),(.30,.98),(.70,.98))
        points = [((width-cart_width)//2+round(cart_width*x), foot-cart_height+round(cart_height*y))
                  for x,y in fractions]
        stats = []
        for elapsed, pixels in frames:
            frame = Image.frombytes('RGB', (width, height), pixels, 'raw', rawmode, stride)
            cart = frame.crop(bounds)
            rows = cart.resize((1, cart.height), Image.Resampling.BOX)
            stats.append({'t': elapsed, 'mean': sum(ImageStat.Stat(cart).mean)/3,
                          'blank_rows': sum(sum(row)<6 for row in rows.getdata()),
                          'plastic': [frame.getpixel(point) for point in points]})
        (options.output/'brightness.json').write_text(json.dumps(stats))
        if options.stats_only:
            worst = min((i for i, (t, _) in enumerate(frames) if t >= 2),
                        key=lambda i: stats[i]['mean'], default=0)
            for index in {0, worst, len(frames)-1}:
                Image.frombytes('RGB', (width, height), frames[index][1], 'raw', rawmode, stride).save(
                    options.output/('frame-%03d.png' % index))
            print('%s: captured %d frames; brightness statistics saved' % (options.output, len(frames)))
            return
    thumb_width=options.thumb_width;thumb_height=round(thumb_width*height/width);cell=thumb_height+24
    cols=options.grid_cols;rows=options.grid_rows or (len(frames)+cols-1)//cols
    per_page=cols*rows;sheet=None
    for index, (elapsed, pixels) in enumerate(frames):
        local=index%per_page
        if local==0:
            sheet=Image.new('RGB',(thumb_width*cols,cell*min(rows,(len(frames)-index+cols-1)//cols)))
            draw=ImageDraw.Draw(sheet)
        frame = Image.frombytes('RGB', (width, height), pixels, 'raw', rawmode, stride)
        frame.save(options.output / ('frame-%03d.png' % index))
        x, y = (local % cols) * thumb_width, (local // cols) * cell
        sheet.paste(frame.resize((thumb_width,thumb_height)), (x, y))
        draw.text((x+6,y+thumb_height+4),'#%03d  %.3f s' % (index,elapsed),fill='white')
        if local==per_page-1 or index==len(frames)-1:
            page=index//per_page+1
            sheet.save(options.output/('grid-%03d.png'%page))
            if page==1: sheet.save(options.output/'sheet.png')
    print('%s: captured %d frames at %.1f fps; %d frames/grid' % (options.output,len(frames),fps,per_page))


if __name__ == '__main__':
    main()
