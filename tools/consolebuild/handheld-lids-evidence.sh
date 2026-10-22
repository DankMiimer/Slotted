#!/bin/sh
# Offline GBA/DS source, animation and repeat-build evidence; MIT.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
run="$blender -t 1 -b --disable-autoexec --python-exit-code 1 --python"
out=build/handheld-lids;mkdir -p "$out"
for pass in 1 2;do
    $run tools/consolebuild/import_gba_cart.py -- research/hardware-review/downloads "$out/cart-$pass" > "$out/cart-prepare-$pass.log" 2>&1
    cmp "$out/cart-$pass/model.glb" third_party/models/dave-gba/model.glb
    cmp "$out/cart-$pass/source.json" third_party/models/dave-gba/source.json
    sha256sum third_party/models/thegraphicsgeek-ags/model.glb third_party/models/thegraphicsgeek-ags/source.json > "$out/ags-before.txt"
    $run tools/consolebuild/import_handhelds.py -- gba research/gba/gameboy_advance_sp.glb > "$out/ags-prepare-$pass.log" 2>&1
    sha256sum third_party/models/thegraphicsgeek-ags/model.glb third_party/models/thegraphicsgeek-ags/source.json > "$out/ags-after.txt"
    cmp "$out/ags-before.txt" "$out/ags-after.txt"
done
echo 'prepared sources: each repeated twice byte for byte'
files() {
    find theme/art-book-slot/_slot/consoles/gba theme/art-book-slot/_slot/shapes/gba tools/themebuild/assets/hero -type f
    printf '%s\n' theme/art-book-slot/_slot/shells/gba.png theme/art-book-slot/_slot/backings/gba.png theme/art-book-slot/_slot/band-console-gba.png
    find theme/art-book-slot/_slot/appearance -type f | grep -E '/(consoles/gba/|band-console-gba\.png$|manifest.json$|shelf.xml$)'
    printf '%s\n' tools/slotlaunch/console-specs.h tools/slotlaunch/media-specs.h tools/slotlaunch/appearance-data.h tools/slotlaunch/lid-data.h theme/art-book-slot/_slot/consoles/specs.json
}
build() {
    $run tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n:SHAPES[n] for n in ('gba',)})"
    sh tools/consolebuild/appearance-preview.sh > "$out/appearance-$pass.log" 2>&1
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward;build gba
pass=reordered;build gbc gba
pass=repeat;build gba
cmp "$out/hash-forward.txt" "$out/hash-reordered.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reordered)"
$run tools/consolebuild/check_handhelds.py > "$out/clearance.log" 2>&1
$run tools/consolebuild/check_handheld_lids.py > "$out/lid-clearance.log" 2>&1
grep '^{' "$out/clearance.log" "$out/lid-clearance.log"
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -4 "$out/wsl-tests.log"
sh tools/slotlaunch/build.sh > "$out/arm64.log" 2>&1
echo 'ARM64: warning-clean build passed'
