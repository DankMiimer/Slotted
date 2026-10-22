#!/bin/sh
# Art Book Slot managed hook (MIT): ensure the early-launch watcher when ES starts.
# Deliberately not a game-selected hook: ES forks for every script on every
# cursor move, which drops frames at the start of each shelf slide.
. /userdata/themes/art-book-slot/_slot/launch/common.sh
slot_ensure_watcher
