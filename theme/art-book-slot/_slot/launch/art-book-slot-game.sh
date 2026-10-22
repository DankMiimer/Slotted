#!/bin/sh
# Art Book Slot managed hook (MIT): configgen, sync; event/system/emulator/core/ROM.
. /userdata/themes/art-book-slot/_slot/launch/common.sh
slot_enabled "$5" || exit 0
case "$1" in
    gameStart)
        i=0
        while [ ! -f "$SLOT_DONE" ] && [ "$i" -lt 30 ]; do
            sleep 0.1
            i=$((i + 1))
        done
        slot_log "configgen gameStart waited ${i}x100ms"
        ;;
    gameStop)
        slot_log 'configgen gameStop'
        touch "$SLOT_STATE/returned"
        slot_refresh_state "$5"
        "$SLOT_HELPER" eject "$5" "$SLOT_ASSETS" "$SLOT_DONE" || :
        slot_log 'eject returned'
        ;;
esac
