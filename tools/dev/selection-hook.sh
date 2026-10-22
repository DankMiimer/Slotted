#!/bin/sh
# Development-only game-selected hook for profile_navigation.py and return_probe.py.
# Install temporarily as scripts/game-selected/zz-slot-dev-selection.sh and remove it
# afterwards: ES forks for it on every cursor move, costing frames while browsing.
[ -n "$2" ] || exit 0
mkdir -p /tmp/art-book-slot-launch
printf '%s\n' "$2" > "/tmp/art-book-slot-launch/selected.$$"
mv "/tmp/art-book-slot-launch/selected.$$" /tmp/art-book-slot-launch/selected
