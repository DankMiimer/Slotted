#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
out="$root/build/slotted-phase3/room-checks"
mkdir -p "$out"
g++ -O2 -std=c++14 -Wall -Wextra -Wno-misleading-indentation \
    -I"$root/tools/frontend" -I"$root/tools/frontend/overlay/es-app/src/components" \
    "$root/tools/frontend/tests/room_session.cpp" -o "$out/room-session"
"$out/room-session" "$out/roundtrip-invalid-after-test.world"
g++ -O2 -std=c++14 -Wall -Wextra "$root/tools/frontend/tests/state.cpp" -o "$out/state"
"$out/state"
g++ -O2 -std=c++14 -Wall -Wextra -Wno-misleading-indentation \
    -I"$root/tools/frontend/overlay/es-app/src/components" \
    "$root/tools/frontend/tests/system_flight.cpp" -o "$out/system-flight"
"$out/system-flight"
python3 "$root/tools/frontend/tests/world_navigation.py"
