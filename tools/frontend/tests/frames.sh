#!/bin/sh
# Render native scene frames for review: frames.sh PROBE MODEL OUTDIR [PROGRESS...]
# Values are insertion progress (0..1), or the probe's 'front'/'browse' poses.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project=$(CDPATH= cd -- "$here/../../.." && pwd)
probe=$1 model=$2 out=$3
shift 3
mkdir -p "$out"
[ $# -gt 0 ] || set -- .10 .25 .35 .45 .55 .65 .75 .85 .95 1 front browse
for value in "$@"; do
    sh "$here/run_probe.sh" "$probe" "$project/theme/art-book-slot/_slot" "$out/$model-$value.bmp" "$model" "$value" >/dev/null
done
echo "frames: $out"
