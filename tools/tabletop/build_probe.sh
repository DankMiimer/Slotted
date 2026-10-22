#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
out=${1:-$root/build/tabletop/probe}
lib=${SLOT_SCENE_LIBS:-${SLOT_DESKTOP_IMAGE_LIB:-$root/build/native/desktop/usr/lib/x86_64-linux-gnu}}
gles=${SLOT_SCENE_GLES:-libGLESv2.so.2}
compiler=${CXX:-g++}
headers=${SLOT_HEADERS:-$HOME/slot-es-presentation/headers/usr/include}
probe_source=${SLOT_SCENE_PROBE_SOURCE:-$root/tools/tabletop/probe.cpp}
components=${SLOT_SCENE_COMPONENTS:-$root/tools/frontend/overlay/es-app/src/components}
mkdir -p "$(dirname "$out")"
"$compiler" -O2 -std=c++14 -Wall -Wextra -Wno-misleading-indentation \
    -I"$root/build/native/SDL-release-2.32.8/include" -idirafter "$headers/SDL2" \
    -idirafter "$headers" -I"$components" \
    "$probe_source" "$components/SlotTabletop.cpp" \
    -L"$lib" -Wl,--allow-shlib-undefined -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -l:"$gles" -lm -pthread -o "$out"
echo "tabletop probe: $out"
