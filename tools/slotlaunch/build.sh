#!/bin/sh
# Cross-build under WSL. Device SDL shared libraries live in build/native/lib.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
build="$root/build/native"
mkdir -p "$build"
headers="$build/SDL-release-2.32.8/include"
if [ ! -f "$headers/SDL.h" ]; then
    curl -fsSL --retry 2 https://github.com/libsdl-org/SDL/archive/refs/tags/release-2.32.8.tar.gz \
        -o "$build/SDL-headers.tar.gz"
    tar -xzf "$build/SDL-headers.tar.gz" -C "$build"
fi
# Only consuming the public ABI, not compiling SDL. Use its portable header config
# so host/distribution development-package architecture does not affect the build.
cp "$headers/SDL_config_minimal.h" "$headers/SDL_config.h"
aarch64-linux-gnu-gcc -O2 -std=c11 -Wall -Wextra -Werror \
    -I"$headers" \
    "$root/tools/slotlaunch/slot-launch.c" \
    -L"$build/lib" -Wl,--allow-shlib-undefined -lSDL2_image -lSDL2 -lm \
    -o "$root/theme/art-book-slot/_slot/launch/slot-launch"
aarch64-linux-gnu-strip "$root/theme/art-book-slot/_slot/launch/slot-launch"
