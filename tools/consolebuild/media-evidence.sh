#!/bin/sh
# Physical media slice: rebuild, determinism, clearance, label and regression
# evidence. Offline only; writes to ignored build/media. MIT.
# Needs BLENDER (4.5), WSL x86-64 SDL2/SDL2_image + Mesa (build/native/desktop)
# and a frozen receiving tree in build/media/before (git archive, see docs).
set -eu
trap 'result=$?; printf "\nexit=%s\n" "$result"' 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
run="$blender -t 1 -b --disable-autoexec --python-exit-code 1 --python"
out=build/media; mkdir -p "$out"
systems="snes snes-us nes n64 md md-jp nds pico8"
files() {
    for s in $systems; do find "theme/art-book-slot/_slot/consoles/$s" -type f; done | sort
    echo tools/slotlaunch/media-specs.h
}

# Repeat and reverse builds must be byte-identical.
$run tools/consolebuild/models.py -- $systems >/dev/null
files | xargs sha256sum > "$out/hash-forward.txt"
$run tools/consolebuild/models.py -- $(echo $systems | tr ' ' '\n' | tac | tr '\n' ' ') >/dev/null
files | xargs sha256sum > "$out/hash-reverse.txt"
$run tools/consolebuild/models.py -- $systems >/dev/null
files | xargs sha256sum > "$out/hash-repeat.txt"
cmp "$out/hash-forward.txt" "$out/hash-reverse.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reverse)"

python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
# Shelf faces are the 3D hero renders: capture them, then rebuild the 12 cartridge shapes.
sh tools/consolebuild/hero-shells.sh
python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n: SHAPES[n] for n in ('gb','gbc','gba','snes','snes-us','nes','n64','md','md-jp','md-ea','nds','pico8')})"
python3 tools/consolebuild/media.py
status=0; $run tools/consolebuild/check_handhelds.py > "$out/check-handhelds.log" 2>&1 || status=$?
grep '^{' "$out/check-handhelds.log"; [ "$status" = 0 ]
# A pipe would hide a checker's failing status; keep both logs instead.
status=0; $run tools/consolebuild/check_media.py > "$out/check.log" 2>&1 || status=$?
grep '^{' "$out/check.log"; [ "$status" = 0 ]
$run tools/consolebuild/review_media.py >/dev/null
sh tools/slotlaunch/build.sh

# Native 720x480 poses, before/after, plus the four accepted families.
SLOT_REVIEW_BUILD="$root/$out" SLOT_REVIEW_SYSTEMS="snes snes-us nes n64 md md-jp md:md-ea nds pico8 gb psp gbc gba" \
    sh tools/consolebuild/offline-preview.sh > "$out/preview.log" 2>&1 || { tail -20 "$out/preview.log"; exit 1; }
lib=$root/build/native/desktop/usr/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH=$lib SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1
for entry in snes snes-us nes n64 md md-jp md:md-ea nds pico8; do
    system=${entry%%:*}; shell=${entry#*:}; dir=$out/diagnostic/$shell; mkdir -p "$dir"
    "$out/native/after" "$system" theme/art-book-slot/_slot "$dir" insert "shell=$shell" diagnostic 2>/dev/null
    cat "$dir/label-check.json"
done
# PSP must stay byte-identical. DMG/CGB/AGS intentionally change: 3D hero frames,
# their recess label crop and (DMG) the baked plastic tint; report the count.
compared=0; differing=0
for f in "$out"/after/psp/*.png; do
    compared=$((compared+1)); cmp -s "$f" "$out/before/${f#"$out"/after/}" || differing=$((differing+1))
done
echo "accepted PSP native PNGs: $compared compared, $differing differing"
[ "$differing" = 0 ]
for s in gb gbc gba; do
    n=0; d=0; for f in "$out"/after/$s/*.png; do n=$((n+1)); cmp -s "$f" "$out/before/${f#"$out"/after/}" || d=$((d+1)); done
    echo "$s native PNGs changed by the always-3D shelf/hero contract: $d of $n"
done
python3 tools/consolebuild/compose_media.py
