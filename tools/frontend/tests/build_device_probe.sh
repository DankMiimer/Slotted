#!/bin/sh
# Cross-build the shared-context native probe for the handheld (ARM64, device libs).
# Usage: build_device_probe.sh [patched-frontend] [output]; run apply.py first.
set -eu
project=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
frontend=${1:-$HOME/slot-es-presentation/frontend}
output=${2:-$project/build/queued-models/device/native-probe}
libs=$project/build/slotted-presentation/lib
components=$frontend/es-app/src/components
mkdir -p "$(dirname "$output")"
aarch64-linux-gnu-gcc -O2 -std=gnu11 -I"$project/build/native/SDL-release-2.32.8/include" \
    "-DSLOT_HELPER_SOURCE=\"$components/slot-scene/slot-launch.c\"" \
    "$project/tools/frontend/tests/native.c" "$components/SlotNative.c" \
    -L"$libs" -Wl,--allow-shlib-undefined -l:libSDL2_image-2.0.so.0 -l:libSDL2-2.0.so.0 -l:libmali.so -lm -o "$output"
aarch64-linux-gnu-strip "$output"
echo "device probe: $output"
