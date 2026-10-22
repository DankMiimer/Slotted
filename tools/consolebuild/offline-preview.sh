#!/bin/sh
# No device interaction. x86-64 SDL2/SDL2_image + Mesa EGL needed in WSL.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
build=${SLOT_REVIEW_BUILD:-$root/build/exemplars}
mkdir -p "$build/native"
image_lib=${SLOT_DESKTOP_IMAGE_LIB:-$root/build/native/desktop/usr/lib/x86_64-linux-gnu}
export LD_LIBRARY_PATH="$image_lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
for version in ${SLOT_REVIEW_VERSIONS:-before after}; do
    assets="$root/theme/art-book-slot/_slot"
    source="$root/tools/slotlaunch/slot-launch.c"
    authored='-DSLOT_AUTHORED_MEDIA -DSLOT_NEXT_MEDIA -DSLOT_CARTRIDGE_MEDIA'
    if [ "$version" = before ]; then
        assets="$build/before/theme/art-book-slot/_slot"
        source="$build/before/tools/slotlaunch/slot-launch.c"
        authored=
        # Current receiving branches support authored media; fba7ffe's older
        # baseline does not. Keep both review recipes usable.
        if [ -f "$build/before/tools/slotlaunch/exemplar-media.h" ]; then
            authored=-DSLOT_AUTHORED_MEDIA
        fi
        # Receiving branches with the CGB/AGS media tint need it in the baseline.
        if grep -q cartridge_media_colour "$build/before/tools/slotlaunch/cartridge-console.h"; then
            authored="$authored -DSLOT_NEXT_MEDIA"
        fi
        if grep -q ExemplarShelf "$build/before/tools/slotlaunch/cartridge-console.h"; then
            authored="$authored -DSLOT_CARTRIDGE_MEDIA"
        fi
    fi
    gcc -O2 -std=c11 -Wall -Wextra -Werror $authored -I"$root/build/native/SDL-release-2.32.8/include" \
        "-DSLOT_HELPER_SOURCE=\"$source\"" "$root/tools/consolebuild/offline-preview.c" \
        -L"$image_lib" -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -lm \
        -o "$build/native/$version"
    # SYSTEM or SYSTEM:SHELL, e.g. md:md-ea renders the md console with EA media.
    for entry in ${SLOT_REVIEW_SYSTEMS:-gb psp}; do
        system=${entry%%:*}; shell=${entry#*:}; name=$shell
        mkdir -p "$build/$version/$name"
        for mode in insert eject; do
            if [ "$shell" = "$system" ]; then
                "$build/native/$version" "$system" "$assets" "$build/$version/$name" "$mode"
            else
                "$build/native/$version" "$system" "$assets" "$build/$version/$name" "$mode" "shell=$shell"
            fi
        done
    done
done
