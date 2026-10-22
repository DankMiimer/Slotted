#!/bin/sh
# Capture every cartridge shelf face from its 3D model at the native hero pose
# (offline GLES harness, no device). Writes the committed theme-build inputs
# tools/themebuild/assets/hero/<shape>.png/.json. MIT.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
lib=${SLOT_DESKTOP_IMAGE_LIB:-$root/build/native/desktop/usr/lib/x86_64-linux-gnu}
mkdir -p build/media/native build/media/hero tools/themebuild/assets/hero
gcc -O2 -std=c11 -Wall -Wextra -Werror -DSLOT_AUTHORED_MEDIA -DSLOT_NEXT_MEDIA -DSLOT_CARTRIDGE_MEDIA \
    -I"$root/build/native/SDL-release-2.32.8/include" "-DSLOT_HELPER_SOURCE=\"$root/tools/slotlaunch/slot-launch.c\"" \
    tools/consolebuild/offline-preview.c -L"$lib" -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -lm \
    -o build/media/native/after
export LD_LIBRARY_PATH="$lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
# SHAPE:SYSTEM. The notched gb shape is the DMG Game Pak.
entries="${*:-gb:gb gbc:gbc gba:gba snes:snes snes-us:snes-us nes:nes n64:n64 md:md md-jp:md-jp md-ea:md nds:nds pico8:pico8}"
for entry in $entries; do
    shape=${entry%%:*}; system=${entry#*:}; dir=build/media/hero/$shape; mkdir -p "$dir"
    SLOT_MODEL_STYLE=realistic build/media/native/after "$system" theme/art-book-slot/_slot "$dir" hero "shell=$shape" > "$dir/hero.log" 2>&1
    grep '^hero' "$dir/hero.log"
    cp "$dir/hero.png" "tools/themebuild/assets/hero/$shape.png"
    cp "$dir/hero.json" "tools/themebuild/assets/hero/$shape.json"
    if test -f "$dir/hero-fixed.png"; then cp "$dir/hero-fixed.png" "tools/themebuild/assets/hero/$shape-fixed.png"; fi
    cp "$dir/hero-label.png" "tools/themebuild/assets/hero/$shape-label.png"
done
