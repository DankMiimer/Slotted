#!/usr/bin/env python3
"""Watch ES's confirmed launch XML before its synchronous audio/display shutdown.

Linux inotify sleeps between file events; no input interception or framebuffer polling.
The ordinary game-start hook remains the fallback if this watcher is unavailable.
"""
import argparse
import ctypes
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

STATE = Path('/tmp/art-book-slot-launch')
SOURCE = Path(__file__).resolve().parent
IN_CLOSE_WRITE = 8
EVENT = struct.Struct('iIII')


def launch_rom(path):
    try:
        rom = ET.parse(path).findtext('./game/path')
        return rom if rom and rom.startswith('/userdata/roms/') else None
    except (OSError, ET.ParseError):
        return None


def ensure():
    subprocess.Popen([sys.executable, str(SOURCE / 'watch.py'), 'run'],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def run():
    import fcntl
    STATE.mkdir(mode=0o700, exist_ok=True)
    with (STATE / 'watch.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        pids = subprocess.run(['pidof', 'emulationstation'], capture_output=True,
                              text=True).stdout.split()
        if not pids:
            return
        frontend = Path('/proc') / pids[-1]
        (STATE / 'watch.pid').write_text(str(os.getpid()))
        libc = ctypes.CDLL(None, use_errno=True)
        fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            return
        try:
            if libc.inotify_add_watch(fd, b'/tmp', IN_CLOSE_WRITE) < 0:
                return
            child = None
            last_rom, last_launch = None, 0
            last_return = 0
            while frontend.exists():
                if child is not None:
                    child.poll()
                if not select.select([fd], [], [], 1)[0]:
                    continue
                events = os.read(fd, 65536)
                offset = 0
                launch = False
                while offset + EVENT.size <= len(events):
                    descriptor, mask, _, length = EVENT.unpack_from(events, offset)
                    offset += EVENT.size
                    name = events[offset:offset + length].split(b'\0', 1)[0]
                    offset += length
                    launch |= bool(mask & IN_CLOSE_WRITE and name == b'game.xml')
                if launch:
                    rom = launch_rom('/tmp/game.xml')
                    try:
                        returned = (STATE / 'returned').stat().st_mtime_ns
                    except FileNotFoundError:
                        returned = 0
                    if returned != last_return:
                        last_rom, last_launch = None, 0
                        last_return = returned
                    # ES can build the command more than once for one launch.
                    # Reap the old helper and consume only one signal per attempt.
                    if child is not None:
                        child.poll()
                    if rom and (rom != last_rom or time.monotonic() - last_launch > 8) and (child is None or child.poll() is not None):
                        last_rom, last_launch = rom, time.monotonic()
                        child = subprocess.Popen(['/bin/sh', str(SOURCE / 'art-book-slot-early.sh'), rom],
                                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
        finally:
            os.close(fd)


def stop():
    try:
        pid = int((STATE / 'watch.pid').read_text())
        # Only stop our owned watcher, even if a stale PID has been reused.
        args = Path('/proc/%s/cmdline' % pid).read_bytes().split(b'\0')
        if str(SOURCE / 'watch.py').encode() in args and b'run' in args:
            import signal
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('ensure', 'run', 'stop'))
    globals()[parser.parse_args().action]()
