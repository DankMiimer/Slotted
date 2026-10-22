#!/bin/sh
# Device-side frame capture around one action, for checking transitions.
#   capture.sh <prefix> <shots> <action...>
# Clears /tmp/<prefix>*.png and /tmp/slot-spike.log, starts shooting in the background, runs the
# action, waits, then prints the timing log.
prefix=$1
shots=$2
shift 2
find /tmp -maxdepth 1 -name "${prefix}*.png" -delete
: > /tmp/slot-spike.log
(
	i=0
	while [ "$i" -lt "$shots" ]; do
		knulli-screenshot "/tmp/${prefix}$(printf %02d "$i").png"
		echo "$(cut -d' ' -f1 /proc/uptime) shot $i" >> /tmp/slot-spike.log
		i=$((i + 1))
	done
) &
sleep 0.2
echo "$(cut -d' ' -f1 /proc/uptime) action: $*" >> /tmp/slot-spike.log
"$@"
wait
cat /tmp/slot-spike.log
