#!/bin/sh
# Offline, scoped N64 reproducibility/clearance evidence. MIT.
set -eu
trap 'result=$?; printf "\nexit=%s\n" "$result"' 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
run="$blender -t 1 -b --disable-autoexec --python-exit-code 1 --python"
out=build/n64; mkdir -p "$out"
source="research/n64/rohm/extracted/source/N64_with_controller.fbx"
if [ -f "$source" ]; then
    for pass in 1 2; do
        $run tools/consolebuild/import_n64.py -- "$source" "$root/$out/prepare-$pass" > "$out/prepare-$pass.log" 2>&1
        cmp "$out/prepare-$pass/model.glb" third_party/models/josephrohm-n64/model.glb
        cmp "$out/prepare-$pass/source.json" third_party/models/josephrohm-n64/source.json
    done
    echo 'prepared source: repeated twice byte for byte'
else
    echo "prepared source: $source not present; committed source used"
fi
files() {
    find theme/art-book-slot/_slot/consoles/n64 theme/art-book-slot/_slot/shapes/n64 tools/themebuild/assets/hero -type f
    printf '%s\n' theme/art-book-slot/_slot/shells/n64.png theme/art-book-slot/_slot/backings/n64.png
    find theme/art-book-slot/_slot/appearance -type f | grep -E '/(consoles/n64/|band-console-n64\.png$|manifest.json$|shelf.xml$)'
    printf '%s\n' tools/slotlaunch/console-specs.h tools/slotlaunch/media-specs.h tools/slotlaunch/appearance-data.h tools/slotlaunch/n64-data.h theme/art-book-slot/_slot/consoles/specs.json theme/art-book-slot/_slot/band-console-n64.png
}
build() {
    $run tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {n:SHAPES[n] for n in ('n64',)})"
    sh tools/consolebuild/appearance-preview.sh > "$out/appearance-$pass.log" 2>&1
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward; build n64
pass=reverse; build snes-us n64
pass=repeat; build n64
cmp "$out/hash-forward.txt" "$out/hash-reverse.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reverse)"
export SLOT_MEDIA_EVIDENCE="$root/$out"
$run tools/consolebuild/check_media.py > "$out/check.log" 2>&1
grep '^{' "$out/check.log"
$run tools/consolebuild/check_n64_flaps.py > "$out/flap-check.log" 2>&1
grep '^{' "$out/flap-check.log"
sh tools/slotlaunch/build.sh > "$out/arm64.log" 2>&1
echo 'ARM64: warning-clean build passed'
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -3 "$out/wsl-tests.log"
