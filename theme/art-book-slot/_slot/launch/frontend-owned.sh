#!/bin/sh
# A matching live frontend transaction owns both the seating and return scene.
# Never evaluate record contents as shell text. No per-selection process runs.
slot_frontend_owned() {
    [ -r "$SLOT_STATE/frontend-owned" ] || return 1
    {
        IFS= read -r slot_owner_version && IFS= read -r slot_owner_pid &&
        IFS= read -r slot_owner_start && IFS= read -r slot_owner_token &&
        IFS= read -r slot_owner_rom || return 1
        if IFS= read -r slot_owner_extra; then return 1; fi
    } < "$SLOT_STATE/frontend-owned"
    # ES's async game-start hook can receive a shell-escaped ROM, whereas
    # configgen and the launch XML use the actual path. Unescape only when the
    # literal path is absent and the resulting exact file exists. Never eval.
    slot_owner_requested=$1
    if [ ! -f "$slot_owner_requested" ]; then
        slot_owner_unescaped=$(printf '%s' "$slot_owner_requested" | sed 's/\\//g')
        [ ! -f "$slot_owner_unescaped" ] || slot_owner_requested=$slot_owner_unescaped
    fi
    [ "$slot_owner_version" = 1 ] && [ "$slot_owner_rom" = "$slot_owner_requested" ] || return 1
    case "$slot_owner_pid:$slot_owner_start" in *[!0-9:]*|:*|*:) return 1 ;; esac
    [ "$slot_owner_pid" -gt 1 ] 2>/dev/null || return 1
    [ "${#slot_owner_token}" = 32 ] || return 1
    case "$slot_owner_token" in *[!a-f0-9]*) return 1 ;; esac
    [ -r "/proc/$slot_owner_pid/stat" ] || return 1
    # The closing parenthesis ends comm, which can contain spaces. Field 22
    # becomes field 20 after removing pid and comm; guard PID reuse as well.
    slot_owner_live=$(sed 's/.*) //' "/proc/$slot_owner_pid/stat" | cut -d ' ' -f20)
    [ "$slot_owner_live" = "$slot_owner_start" ]
}
