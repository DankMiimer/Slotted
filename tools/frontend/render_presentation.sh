#!/bin/sh
# Front/open LCD poses for every handheld and finish, then LCD registration.
# WSL host render with Mesa; no device interaction.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
lib=${SLOT_DESKTOP_IMAGE_LIB:-$root/build/native/desktop/usr/lib/x86_64-linux-gnu}
[ -f "$lib/libGLESv2.so.2" ] || { echo 'Missing desktop GLES library; set SLOT_DESKTOP_IMAGE_LIB' >&2; exit 1; }
mkdir -p build/appearance
gcc -O2 -std=gnu11 -I"$root/build/native/SDL-release-2.32.8/include" tools/consolebuild/presentation-preview.c \
    -L"$lib" -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -lm -o build/appearance/presentation-preview
slot=theme/art-book-slot/_slot
run() { sh tools/frontend/tests/run_probe.sh build/appearance/presentation-preview "$@"; }
SLOT_MODEL_STYLE=realistic SLOT_CONSOLE_COLOR=original run "$slot" "$slot/stage/front"
for style in realistic cel; do
    for colour in original black white red blue purple green yellow; do
        mkdir -p "$slot/stage/front/$style/$colour"
        SLOT_MODEL_STYLE=$style SLOT_CONSOLE_COLOR=$colour run "$slot" "$slot/stage/front/$style/$colour" cropped
    done
done
python3 -m tools.themebuild.screens
