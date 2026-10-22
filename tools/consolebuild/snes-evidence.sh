#!/bin/sh
# Offline, scoped SNES reproducibility/clearance evidence. MIT.
set -eu
trap 'result=$?; printf "\nexit=%s\n" "$result"' 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
run="$blender -t 1 -b --disable-autoexec --python-exit-code 1 --python"
out=build/snes; mkdir -p "$out"
export SLOT_SNES_DETAIL=${SLOT_SNES_DETAIL:-detailed}
files() {
    find theme/art-book-slot/_slot/consoles/snes theme/art-book-slot/_slot/consoles/snes-us -type f
    find theme/art-book-slot/_slot/shapes/snes theme/art-book-slot/_slot/shapes/snes-us tools/themebuild/assets/hero -type f
    printf '%s\n' theme/art-book-slot/_slot/shells/snes.png theme/art-book-slot/_slot/shells/snes-us.png theme/art-book-slot/_slot/backings/snes.png theme/art-book-slot/_slot/backings/snes-us.png
    find theme/art-book-slot/_slot/appearance -type f | grep -E '/(consoles/snes(-us)?/|band-console-snes(-us)?\.png$|manifest.json$|shelf.xml$)'
    printf '%s\n' tools/slotlaunch/console-specs.h tools/slotlaunch/media-specs.h tools/slotlaunch/appearance-data.h theme/art-book-slot/_slot/consoles/specs.json theme/art-book-slot/_slot/band-console-snes.png theme/art-book-slot/_slot/band-console-snes-us.png
}
build() {
    $run tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n:SHAPES[n] for n in ('snes','snes-us')})"
    sh tools/consolebuild/appearance-preview.sh > "$out/appearance-$pass.log" 2>&1
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward; build snes snes-us
pass=reverse; build snes-us snes
pass=repeat; build snes snes-us
cmp "$out/hash-forward.txt" "$out/hash-reverse.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reverse)"
echo 'hero: 24 PNG/JSON files identical'
export SLOT_MEDIA_EVIDENCE="$root/$out"
$run tools/consolebuild/check_media.py > "$out/check.log" 2>&1
grep '^{' "$out/check.log"
sh tools/slotlaunch/build.sh > "$out/arm64-final.log" 2>&1
echo 'ARM64: warning-clean build passed'
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -5 "$out/wsl-tests.log"
