#!/bin/sh
# Turns the Phase 0 launch hooks on or off by moving them in or out of the folders ES and
# configgen read. Nothing is deleted; "off" parks them in /userdata/system/slot-dev/hooks-off.
#   spike-hooks.sh on|off|status
ES_HOOK=/userdata/system/configs/emulationstation/scripts/game-start/slot-insert.sh
CG_HOOK=/userdata/system/scripts/slot-wait.sh
PARK=/userdata/system/slot-dev/hooks-off

case "$1" in
off)
	mkdir -p "$PARK"
	[ -e "$ES_HOOK" ] && mv "$ES_HOOK" "$PARK/"
	[ -e "$CG_HOOK" ] && mv "$CG_HOOK" "$PARK/"
	;;
on)
	mkdir -p "$(dirname "$ES_HOOK")" "$(dirname "$CG_HOOK")"
	[ -e "$PARK/slot-insert.sh" ] && mv "$PARK/slot-insert.sh" "$ES_HOOK"
	[ -e "$PARK/slot-wait.sh" ] && mv "$PARK/slot-wait.sh" "$CG_HOOK"
	;;
esac
for f in "$ES_HOOK" "$CG_HOOK"; do
	[ -e "$f" ] && echo "active: $f" || echo "inactive: $f"
done
