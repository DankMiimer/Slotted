#!/bin/sh
# Offline ARM64 build against cached libraries. Never contacts the handheld.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir -p "$root/build/snes"
aarch64-linux-gnu-gcc -O2 -std=c11 -Wall -Wextra -Werror \
    -I"$root/build/native/SDL-release-2.32.8/include" \
    "$root/tools/consolebuild/benchmark-snes.c" \
    -L"$root/build/native/lib" -Wl,--allow-shlib-undefined -lSDL2_image -lSDL2 -lm \
    -o "$root/build/snes/benchmark-snes"
aarch64-linux-gnu-strip "$root/build/snes/benchmark-snes"
