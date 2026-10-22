#!/bin/sh
# Offline original DS Lite fold/finish reproducibility evidence; MIT.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
blender=${BLENDER:-$HOME/slot-tooling/blender-4.5.0-linux-x64/blender}
run="$blender -t 1 -b --disable-autoexec --python-exit-code 1 --python"
out=build/ds-lid;mkdir -p "$out"
files() {
    find theme/art-book-slot/_slot/consoles/nds theme/art-book-slot/_slot/shapes/nds tools/themebuild/assets/hero -type f
    printf '%s\n' theme/art-book-slot/_slot/shells/nds.png theme/art-book-slot/_slot/backings/nds.png theme/art-book-slot/_slot/band-console-nds.png
    find theme/art-book-slot/_slot/appearance -type f | grep -E '/(consoles/nds/|band-console-nds\.png$|manifest.json$|shelf.xml$)'
    printf '%s\n' tools/slotlaunch/console-specs.h tools/slotlaunch/media-specs.h tools/slotlaunch/appearance-data.h tools/slotlaunch/lid-data.h theme/art-book-slot/_slot/consoles/specs.json
}
build() {
    $run tools/consolebuild/models.py -- "$@" > "$out/build-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
    sh tools/consolebuild/hero-shells.sh > "$out/hero-$pass.log" 2>&1
    python3 -c "from pathlib import Path; from tools.themebuild import shells; from tools.themebuild.geometry import SHAPES; shells.build(Path('theme/art-book-slot/_slot'), {'nds':SHAPES['nds']})"
    sh tools/consolebuild/appearance-preview.sh > "$out/appearance-$pass.log" 2>&1
    files | sort | xargs sha256sum > "$out/hash-$pass.txt"
}
pass=forward;build nds
pass=reordered;build gb nds
pass=repeat;build nds
cmp "$out/hash-forward.txt" "$out/hash-reordered.txt"
cmp "$out/hash-forward.txt" "$out/hash-repeat.txt"
echo "determinism: $(wc -l < "$out/hash-forward.txt") generated files identical (repeat, reordered)"
$run tools/consolebuild/check_handheld_lids.py > "$out/lid-clearance.log" 2>&1
SLOT_MEDIA_EVIDENCE="$out" $run tools/consolebuild/check_media.py > "$out/feed-clearance.log" 2>&1
grep '^{' "$out/lid-clearance.log" "$out/feed-clearance.log"
python3 -m unittest discover -s tests > "$out/wsl-tests.log" 2>&1
tail -4 "$out/wsl-tests.log"
sh tools/slotlaunch/build.sh > "$out/arm64.log" 2>&1
echo 'ARM64: warning-clean build passed'
