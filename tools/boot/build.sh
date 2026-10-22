#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
frontend=${SLOT_FRONTEND:-$HOME/slot-es-presentation/frontend}
out=${1:-$root/build/tabletop/slot-boot}
mkdir -p "$(dirname "$out")"
${CC:-aarch64-linux-gnu-gcc} -O2 -std=gnu11 -Wall -Wextra -Wno-misleading-indentation \
    -I"$frontend/external/libcheevos/libretro-common/include" \
    "$root/tools/boot/slot-boot.c" -ldl -lm -o "$out"
echo "boot probe: $out"
