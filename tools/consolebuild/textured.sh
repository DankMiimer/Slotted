#!/bin/sh
# Rebuild one registered textured model end to end (WSL; no device interaction).
#   textured.sh ADAPTER.py SOURCE MODEL
# e.g. textured.sh bpoole_gbc.py research/model-options-20261016/gbc.glb gbc
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
adapter=$1 source=$2 model=$3
mkdir -p "build/textured/$model"
blender=${SLOT_BLENDER:-/home/mads1/slot-tooling/blender-4.5.0-linux-x64/blender}
frontend=${SLOT_FRONTEND:-$HOME/slot-es-presentation/frontend}
probe=$root/build/queued-models/native-probe
"$blender" -b --factory-startup --disable-autoexec --python-exit-code 1 -t 1 --python "tools/consolebuild/$adapter" -- "$source" \
    > "build/textured/$model-blender.log" 2>&1 || { tail -30 "build/textured/$model-blender.log"; exit 1; }
grep -E 'PREPARED' "build/textured/$model-blender.log"
python3 -m tools.consolebuild.textured "$model"
python3 tools/frontend/apply.py "$frontend" | tail -1
sh tools/frontend/tests/build_probe.sh "$frontend" "$probe" >/dev/null
python3 -m tools.consolebuild.textured --body "$probe" "$model"
python3 -c "from pathlib import Path; from tools.themebuild import consoles; consoles.build(Path('theme/art-book-slot/_slot'),only={'$model'})"
# Specs changed: re-apply and rebuild so the probe uses the registered seating.
python3 tools/frontend/apply.py "$frontend" | tail -1
sh tools/frontend/tests/build_probe.sh "$frontend" "$probe" >/dev/null
echo "textured $model ready; review: sh tools/frontend/tests/frames.sh $probe $model build/queued-models/frames-$model"
