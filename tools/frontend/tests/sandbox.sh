#!/bin/sh
# Run a command with a private /userdata and /usr/share/emulationstation, without root and without
# creating anything outside the sandbox folder: an unprivileged user + mount namespace whose new
# root bind-mounts the host's own directories, plus the two private ones. Host only (WSL).
# Usage: sandbox.sh SANDBOX_DIR COMMAND...   (SANDBOX_DIR holds userdata/ and es-share/)
set -eu
box=$(cd "$1" && pwd); shift
[ -d "$box/userdata" ] && [ -d "$box/es-share" ] || { echo "need $box/userdata and $box/es-share" >&2; exit 2; }
root="$box/root"
mkdir -p "$root" "$box/tmp"
cwd=$(pwd)
exec unshare -Urm sh -s "$box" "$root" "$cwd" "$@" <<'EOF'
set -eu
box=$1; root=$2; cwd=$3; shift 3
mount -t tmpfs none "$root"
for d in bin sbin lib lib32 lib64 libx32 etc dev proc sys run var home mnt opt srv; do
    [ -e "/$d" ] || continue
    if [ -L "/$d" ]; then ln -s "$(readlink "/$d")" "$root/$d"; else mkdir -p "$root/$d" && mount --rbind "/$d" "$root/$d"; fi
done
mkdir -p "$root/tmp" "$root/usr/share" "$root/userdata" "$root/usr/share/emulationstation"
mount --rbind "$box/tmp" "$root/tmp"
for d in /usr/*; do
    name=${d#/usr/}; [ "$name" = share ] && continue
    if [ -L "$d" ]; then ln -s "$(readlink "$d")" "$root/usr/$name"; else mkdir -p "$root/usr/$name" && mount --rbind "$d" "$root/usr/$name"; fi
done
for d in /usr/share/*; do
    name=${d#/usr/share/}
    if [ -L "$d" ]; then ln -s "$(readlink "$d")" "$root/usr/share/$name"
    elif [ -d "$d" ]; then mkdir -p "$root/usr/share/$name" && mount --rbind "$d" "$root/usr/share/$name"
    else touch "$root/usr/share/$name" && mount --bind "$d" "$root/usr/share/$name"; fi
done
mount --rbind "$box/es-share" "$root/usr/share/emulationstation"
mount --rbind "$box/userdata" "$root/userdata"
cd "$root" && exec chroot "$root" sh -c 'cd "$1" && shift && exec "$@"' sandbox "$cwd" "$@"
EOF
