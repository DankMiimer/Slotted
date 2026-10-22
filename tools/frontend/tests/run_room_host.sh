#!/bin/sh
# Runs a fresh host fixture; no deletion, deployment or device access.
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
name=${1:?fresh run name required};height=${2:-480}
case "$name" in *[!a-zA-Z0-9_-]*|'') echo 'simple run name required' >&2;exit 2;; esac
work=$HOME/slotted-room-host;box=$work/boxes/$name;out=$repo/build/slotted-phase3/frontend-$name
[ ! -e "$box" ] && [ ! -e "$out" ] || { echo 'Use fresh paths' >&2;exit 2; }
mkdir -p "$out"
python3 "$repo/tools/frontend/tests/make_room_sandbox.py" "$box" > "$out/sandbox.txt"
set +e
sh "$repo/spikes/slotted-phase0/host/sandbox.sh" "$box" env SDL_VIDEODRIVER=offscreen EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy \
    LD_LIBRARY_PATH="$work/host-shim:$repo/build/native/desktop/usr/lib/x86_64-linux-gnu" HOME=/userdata \
    SLOT_TABLETOP_ASSETS="${SLOT_ROOM_TEST_ASSETS:-$repo/build/tabletop/assets}" SLOT_ROOM_TEST_OUTPUT="$out" SLOT_ROOM_TEST_SCRIPT="${SLOT_ROOM_TEST_SCRIPT:-$repo/tools/frontend/tests/room-script.txt}" \
    timeout 600 "$work/frontend/emulationstation" --resolution 720 "$height" --windowed --no-splash > "$out/stdout.log" 2>&1
status=$?
set -e
printf 'exit=%s\n' "$status" > "$out/run.txt"
[ ! -f "$box/userdata/system/logs/es_log.txt" ] || cp "$box/userdata/system/logs/es_log.txt" "$out/es_log.txt"
printf 'room host complete: %s\n' "$out"
exit "$status"
