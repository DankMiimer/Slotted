#!/bin/sh
# Private research executable; its instrumentation is not linked into the frontend.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${1:-$root/build/system-switch-research-20261020/switch-probe}
lib=${SLOT_SCENE_LIBS:-$root/build/native/desktop/usr/lib/x86_64-linux-gnu}
headers=${SLOT_HEADERS:-$HOME/slot-es-presentation/headers/usr/include}
mkdir -p "$(dirname "$out")"
"${CXX:-g++}" -O2 -std=c++14 -Wall -Wextra -Wno-misleading-indentation -Wno-subobject-linkage \
    -I"$root/build/native/SDL-release-2.32.8/include" -idirafter "$headers/SDL2" \
    -idirafter "$headers" -I"$root/tools/frontend/overlay/es-app/src/components" \
    "$root/tools/tabletop/switch_probe.cpp" -L"$lib" -Wl,--allow-shlib-undefined \
    -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -l:"${SLOT_SCENE_GLES:-libGLESv2.so.2}" -lm -pthread -o "$out"
echo "private switch probe: $out"
