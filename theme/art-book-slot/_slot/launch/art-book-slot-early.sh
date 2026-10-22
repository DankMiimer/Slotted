#!/bin/sh
# Called by the owned watcher only when ES closes its confirmed game launch XML.
. /userdata/themes/art-book-slot/_slot/launch/common.sh
slot_enabled "$1" || exit 0
mkdir -p "$SLOT_STATE"
rm -f "$SLOT_DONE"
stamp=$(cut -d' ' -f1 /proc/uptime)
printf '%s\n%s\n' "${stamp%.*}" "$1" > "$SLOT_STATE/early.part"
mv "$SLOT_STATE/early.part" "$SLOT_STATE/early"
slot_log 'confirmed launch; early insert'
"$SLOT_HELPER" insert "$1" "$SLOT_ASSETS" "$SLOT_DONE" || :
