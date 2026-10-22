"""Read the composed LCD output, including independent Sunxi disp2 layers.

Development sampler only, for the RG34XXSP's 720x480 BSP display. Writeback uses
private uncached DMA memory so framebuffer clears cannot corrupt the recording.
"""
import ctypes as C
import atexit
import fcntl
import mmap
import os
import struct
import time


class Size(C.Structure):
    _fields_ = [('width', C.c_uint32), ('height', C.c_uint32)]


class Rect(C.Structure):
    _fields_ = [('x', C.c_int32), ('y', C.c_int32),
                ('width', C.c_uint32), ('height', C.c_uint32)]


class Frame(C.Structure):
    _fields_ = [('format', C.c_uint32), ('size', Size*3), ('crop', Rect),
                ('fd', C.c_int32)]


class Capture(C.Structure):
    _fields_ = [('window', Rect), ('frame', Frame)]


class Allocation(C.Structure):
    _fields_ = [('length', C.c_size_t), ('alignment', C.c_size_t),
                ('heap_mask', C.c_uint32), ('flags', C.c_uint32), ('handle', C.c_int32)]


class Shared(C.Structure):
    _fields_ = [('handle', C.c_int32), ('fd', C.c_int32)]


# retain=True keeps the DMA buffer for the next retained capture: later contiguous
# allocations can fail once CMA fragments during long sessions, despite free memory.
_retained = None


class DisplayCapture:
    def __init__(self, wait=.04, scale=1, retain=False):
        global _retained
        if wait < .034: raise ValueError('writeback needs two 60-Hz vblanks')
        if scale not in (1,.5): raise ValueError('capture scale must be 1 or .5')
        self.wait = wait
        fb = os.open('/dev/fb0', os.O_RDONLY)
        self.display = os.open('/dev/disp', os.O_RDWR)
        self.libc = C.CDLL(None, use_errno=True)
        var, fix = bytearray(160), bytearray(80)
        fcntl.ioctl(fb, 0x4600, var)
        fcntl.ioctl(fb, 0x4602, fix)
        os.close(fb)
        width, height, _, virtual_height, _, _, bpp = struct.unpack_from('7I', var)
        stride = struct.unpack_from('I', fix, 48)[0]
        allocation_length = stride*height
        self.width,self.height=round(width*scale),round(height*scale)
        self.stride=self.width*4
        self.length=self.stride*self.height
        if (width, height, bpp, stride) != (720,480,32,2880):
            os.close(self.display)
            raise RuntimeError('display capture requires the RG34XXSP BSP display')
        self.retain = retain
        if retain and _retained:
            self.ion, self.shared, self.memory = _retained
            _retained = None
        else:
            self.ion = os.open('/dev/ion', os.O_RDWR)
            # Retain full-size allocation even when testing hardware downscaling.
            allocation = Allocation(allocation_length, 4096, 16, 0, 0)
            if self.libc.ioctl(self.ion, 0xc0204900, C.byref(allocation)):
                os.close(self.ion)
                os.close(self.display)
                raise RuntimeError('could not allocate capture DMA memory')
            shared = Shared(allocation.handle, -1)
            if self.libc.ioctl(self.ion, 0xc0084904, C.byref(shared)):
                os.close(self.ion)
                os.close(self.display)
                raise RuntimeError('could not share capture DMA memory')
            self.shared = shared.fd
            self.memory = mmap.mmap(self.shared, allocation_length)
        self.capture = Capture()
        self.capture.window = Rect(0,0,width,height)
        self.capture.frame.format = 0
        self.capture.frame.size[0] = Size(self.width,self.height)
        self.capture.frame.crop = Rect(0,0,self.width,self.height)
        self.capture.frame.fd = self.shared
        if self.command(0x140) != 0:
            self.memory.close()
            os.close(self.shared)
            os.close(self.ion)
            os.close(self.display)
            raise RuntimeError('display capture engine is unavailable')
        self.closed = False
        atexit.register(self.close)

    def command(self, operation, data=None):
        args = (C.c_ulong*4)(0, C.addressof(data) if data is not None else 0, 1, 0)
        return self.libc.ioctl(self.display, operation, args)

    def read(self):
        if self.command(0x143, self.capture) != 0:
            raise RuntimeError('display capture commit failed')
        # BSP queues writeback at the next vblank and completes on the following one.
        time.sleep(self.wait)
        return self.memory[:self.length]

    def close(self):
        global _retained
        if self.closed:
            return
        self.closed = True
        self.command(0x141)
        time.sleep(.04)
        if self.retain and not _retained:
            _retained = (self.ion, self.shared, self.memory)
        else:
            self.memory.close()
            os.close(self.shared)
            os.close(self.ion)
        os.close(self.display)
