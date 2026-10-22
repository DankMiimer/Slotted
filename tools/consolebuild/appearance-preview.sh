#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir -p "$root/build/appearance"
cd "$root"
# The preview binary embeds the supported families; refresh that generated
# header before compiling when a newly completed model joins the palette.
python3 -m tools.themebuild.appearance > "$root/build/appearance/masks.log"
lib="$root/build/native/desktop/usr/lib/x86_64-linux-gnu"
gcc -O2 -std=c11 -Wall -Wextra -Werror -I"$root/build/native/SDL-release-2.32.8/include" \
    "$root/tools/consolebuild/appearance-preview.c" -L"$lib" \
    -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -lm -o "$root/build/appearance/preview"
export LD_LIBRARY_PATH="$lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
cd "$root"
python3 -m tools.consolebuild.appearance
