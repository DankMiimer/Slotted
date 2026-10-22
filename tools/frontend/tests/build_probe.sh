#!/bin/sh
# Build the host shared-context native probe from the patched private frontend.
# No device interaction. Needs x86-64 SDL2/SDL2_image + Mesa EGL/GLESv2 in WSL.
# Usage: build_probe.sh [patched-frontend] [output]; run apply.py first.
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
frontend=${1:-$HOME/slot-es-presentation/frontend}
output=${2:-$project/build/slotted-presentation/native-probe}
lib=${SLOT_DESKTOP_IMAGE_LIB:-$project/build/native/desktop/usr/lib/x86_64-linux-gnu}
[ -f "$lib/libGLESv2.so.2" ] || { echo 'Missing desktop GLES library; set SLOT_DESKTOP_IMAGE_LIB' >&2; exit 1; }
components=$frontend/es-app/src/components
gcc -O2 -std=gnu11 -I"$project/build/native/SDL-release-2.32.8/include" \
    "-DSLOT_HELPER_SOURCE=\"$components/slot-scene/slot-launch.c\"" \
    "$project/tools/frontend/tests/native.c" "$components/SlotNative.c" \
    -L"$lib" -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -l:libGLESv2.so.2 -lm -o "$output"
echo "probe: $output"
echo "run with: LD_LIBRARY_PATH=$lib SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1"
