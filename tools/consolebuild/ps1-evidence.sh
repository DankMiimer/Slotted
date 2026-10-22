#!/bin/sh
# Offline PlayStation source/runtime/appearance repeatability, MIT.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
out=build/ps1;mkdir -p "$out"
source='research/hardware-review/independent/ps1-exterior/extracted/source/Sony_Pack_final(blend 3_6).blend'
if [ -f "$source" ]; then
    for pass in 1 2; do
        "$blender" -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/import_ps1.py -- "$source" "$root/$out/prepare-$pass" > "$out/prepare-$pass.log" 2>&1
        cmp "$out/prepare-$pass/model.glb" third_party/models/darkigorek-ps1/model.glb
        cmp "$out/prepare-$pass/source.json" third_party/models/darkigorek-ps1/source.json
    done
    echo 'prepared PS1 source: two repeats identical'
fi
files() {
    find theme/art-book-slot/_slot/consoles/psx theme/art-book-slot/_slot/appearance tools/themebuild/assets/hero -type f
    for shape in gb gbc gba snes snes-us nes n64 md md-jp md-ea nds pico8; do
        find "theme/art-book-slot/_slot/shapes/$shape" -type f
        printf '%s\n' "theme/art-book-slot/_slot/shells/$shape.png" "theme/art-book-slot/_slot/backings/$shape.png"
    done
    printf '%s\n' theme/art-book-slot/_slot/band-console-psx.png theme/art-book-slot/_slot/consoles/specs.json
    printf '%s\n' tools/slotlaunch/ps1-data.h tools/slotlaunch/appearance-data.h tools/slotlaunch/console-specs.h tools/slotlaunch/media-specs.h
}
build() {
    "$blender" -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n:SHAPES[n] for n in ('gb','gbc','gba','snes','snes-us','nes','n64','md','md-jp','md-ea','nds','pico8')})"
    sh tools/consolebuild/appearance-preview.sh > "$out/appearance-$pass.log" 2>&1
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward;build psx
pass=reordered;build gb psx
pass=repeat;build psx
cmp "$out/hash-forward.txt" "$out/hash-reordered.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reordered)"
export SLOT_MEDIA_EVIDENCE="$root/$out"
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -4 "$out/wsl-tests.log"
sh tools/slotlaunch/build.sh > "$out/arm64.log" 2>&1
echo 'ARM64: warning-clean build passed'
