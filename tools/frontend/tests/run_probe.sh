#!/bin/sh
# Run a host native probe with offscreen Mesa: run_probe.sh PROBE ARGS...
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
lib=${SLOT_DESKTOP_IMAGE_LIB:-$project/build/native/desktop/usr/lib/x86_64-linux-gnu}
[ -f "$lib/libGLESv2.so.2" ] || { echo 'Missing desktop GLES library; set SLOT_DESKTOP_IMAGE_LIB' >&2; exit 1; }
export LD_LIBRARY_PATH="$lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
# The helper's default state directory also receives its animation.log.
mkdir -p /tmp/art-book-slot-launch
exec "$@"
