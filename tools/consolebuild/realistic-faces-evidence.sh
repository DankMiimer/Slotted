#!/bin/sh
# Offline repeatability and shelf/scene contracts for Realistic faces. MIT.
set -eu
trap 'result=$?; printf "\nexit=%s\n" "$result"' 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
out=build/realistic-faces; mkdir -p "$out"
files() {
    find theme/art-book-slot/_slot/consoles/gba tools/themebuild/assets/hero -type f
    for shape in gb gbc gba snes snes-us n64; do
        find "theme/art-book-slot/_slot/shapes/$shape" -type f
        printf '%s\n' "theme/art-book-slot/_slot/shells/$shape.png" "theme/art-book-slot/_slot/backings/$shape.png"
    done
    printf '%s\n' tools/slotlaunch/media-specs.h
}
build() {
    "$blender" -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n:SHAPES[n] for n in ('gb','gbc','gba','snes','snes-us','n64')})"
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward; build gba
pass=reverse; build gba gb
pass=repeat; build gba
cmp "$out/hash-forward.txt" "$out/hash-reverse.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reverse)"
export SLOT_MEDIA_EVIDENCE="$root/$out"
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -4 "$out/wsl-tests.log"
sh tools/slotlaunch/build.sh > "$out/arm64.log" 2>&1
echo 'ARM64: warning-clean build passed'
