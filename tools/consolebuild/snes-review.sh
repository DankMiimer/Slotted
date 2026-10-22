#!/bin/sh
# Independent neutral, native, label and accepted-family regression review. MIT.
set -eu
trap 'result=$?; printf "\nexit=%s\n" "$result"' 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
out=build/snes
test -f "$out/before/tools/slotlaunch/slot-launch.c"
SLOT_REVIEW_BUILD="$root/$out" SLOT_REVIEW_SYSTEMS='snes snes-us gb gbc gba psp' \
    sh tools/consolebuild/offline-preview.sh > "$out/native-final.log" 2>&1
lib=$root/build/native/desktop/usr/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH="$lib" SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
for system in snes snes-us; do
    dir="$out/diagnostic/$system"; mkdir -p "$dir"
    "$out/native/after" "$system" theme/art-book-slot/_slot "$dir" insert diagnostic > "$dir/native.log" 2>&1
    cat "$dir/label-check.json"
    dir="$out/timed/$system"; mkdir -p "$dir"
    for mode in insert eject; do
        "$out/native/after" "$system" theme/art-book-slot/_slot "$dir" "$mode" timed > "$dir/$mode.log" 2>&1
    done
done
python3 - <<'PY'
import json,hashlib
from pathlib import Path
out=Path('build/snes');report={}
for name in ('gb','gbc','gba','psp'):
    files=sorted((out/'after'/name).glob('*.png'))
    changed=[p.name for p in files if p.read_bytes()!=(out/'before'/name/p.name).read_bytes()]
    report[name]=dict(compared=len(files),differing=changed)
    assert len(files)==244 and not changed,(name,report[name])
(out/'accepted-regression-final.json').write_text(json.dumps(report,indent=2)+'\n')
print('Accepted GB/CGB/AGS/PSP regression: 976 PNGs byte-identical')
PY
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
SLOT_REVIEW_VERSIONS="${SLOT_NEUTRAL_VERSIONS:-before after}" "$blender" -t 1 -b --disable-autoexec --python-exit-code 1 \
    --python tools/consolebuild/review_snes.py > "$out/neutral-final.log" 2>&1
python3 tools/consolebuild/compose_snes.py
echo 'Native, timed, neutral and appearance review assets complete'
