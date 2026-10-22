#!/bin/sh
# Art Book Slot managed hook (MIT): ES game-start, async; $1 is the ROM path.
. /userdata/themes/art-book-slot/_slot/launch/common.sh
slot_enabled "$1" || exit 0
mkdir -p "$SLOT_STATE"
if slot_early_insert "$1"; then
    slot_log 'ES game-start; early insert already claimed'
    exit 0
fi
rm -f "$SLOT_DONE"
slot_log 'ES game-start'
"$SLOT_HELPER" insert "$1" "$SLOT_ASSETS" "$SLOT_DONE" || :
# The watcher normally starts with ES; this covers a theme switched in later.
slot_ensure_watcher
