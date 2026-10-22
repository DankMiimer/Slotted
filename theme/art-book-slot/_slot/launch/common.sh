#!/bin/sh
# Art Book Slot launch hooks (MIT). Shared by the ES/configgen entry points.
SLOT_THEME=/userdata/themes/art-book-slot
SLOT_ASSETS="$SLOT_THEME/_slot"
SLOT_HELPER="$SLOT_ASSETS/launch/slot-launch"
SLOT_STATE=/tmp/art-book-slot-launch
SLOT_DONE="$SLOT_STATE/done"
SLOT_SETTINGS=/userdata/system/configs/emulationstation/es_settings.cfg
SLOT_THEME_SETTINGS=/userdata/system/configs/emulationstation/themesettings/art-book-slot.cfg
slot_frontend_owned() { return 1; }
[ ! -r "$SLOT_ASSETS/launch/frontend-owned.sh" ] || . "$SLOT_ASSETS/launch/frontend-owned.sh"

slot_setting() {
    [ -f "$SLOT_THEME_SETTINGS" ] || return 0
    # Batocera writes CR-separated records, rather than ordinary Unix lines.
    tr '\r' '\n' < "$SLOT_THEME_SETTINGS" | sed -n "s/^$1=//p"
}

slot_option() {
    # ES gives a system-specific subset priority over the common theme choice.
    option=$(slot_live_setting "subset\.$system\.$1")
    [ -n "$option" ] || option=$(slot_live_setting "subset\.$1")
    printf '%s' "${option:-$2}"
}

slot_live_setting() {
    live=$(sed -n "s/.*name=\"$1\" value=\"\([^\"]*\)\".*/\1/p" "$SLOT_SETTINGS")
    [ -n "$live" ] || live=$(slot_setting "$1")
    printf '%s' "$live"
}

slot_enabled() {
    slot_frontend_owned "$1" && return 1
    [ -x "$SLOT_HELPER" ] || return 1
    grep -q 'name="ThemeSet" value="art-book-slot"' "$SLOT_SETTINGS" || return 1
    case "$1" in
        /userdata/roms/gba/*|/userdata/roms/gbah/*|/userdata/roms/gb/*|/userdata/roms/gbh/*|/userdata/roms/gbc/*|/userdata/roms/gbch/*|/userdata/roms/snes/*|/userdata/roms/snesh/*|/userdata/roms/nes/*|/userdata/roms/nesh/*|/userdata/roms/n64/*|/userdata/roms/n64h/*|/userdata/roms/megadrive/*|/userdata/roms/genesis/*|/userdata/roms/psx/*|/userdata/roms/dreamcast/*|/userdata/roms/psp/*|/userdata/roms/nds/*|/userdata/roms/pico8/*) ;;
        *) return 1 ;;
    esac
    system=${1#/userdata/roms/}
    system=${system%%/*}
    family=${system%h}
    [ "$family" != genesis ] || family=megadrive
    [ "$(slot_option "slot-$family" on)" = on ] || return 1
    export SLOT_WALLPAPER=$(slot_option slot-wallpaper off)
    export SLOT_STATE_PHOTO=$(slot_option slot-state off)
    # Realistic is the default finish; the user found cel shading too flat.
    export SLOT_MODEL_STYLE=$(slot_option slot-model-style realistic)
    export SLOT_CONSOLE_COLOR=$(slot_option slot-console-color original)
    export SLOT_SNES_CARTRIDGE=$(slot_option slot-snes-cartridge-model regional)
    export SLOT_GBA_SP=$(slot_option slot-gba-sp-model neilvfx)
    view=$(slot_live_setting "$system\.defaultView")
    if [ -z "$view" ]; then
        view=$(slot_live_setting GamelistViewStyle)
    fi
    case "$view" in
        ''|automatic|gamecarousel) return 0 ;;
        *) return 1 ;;
    esac
}

slot_refresh_state() {
    [ "$SLOT_STATE_PHOTO" = on ] || return 0
    # Most ROMs have no states: avoid starting Python on their return path.
    filename=${1##*/}
    stem=${filename%.*}
    relative=${1#/userdata/roms/}
    have_state=0
    for screenshot in "/userdata/saves/${relative%/*}/$stem".state*.png "/userdata/saves/$system/$stem".state*.png; do
        [ ! -f "$screenshot" ] || have_state=1
    done
    [ "$have_state" = 1 ] || [ -f "${1%/*}/media/slotstates/$stem.png" ] || return 0
    # Configgen has closed the state image before gameStop; refresh only this game's photo.
    (cd "$SLOT_ASSETS" && python3 -m slotcart.states --rom "$1") || :
}

slot_ensure_watcher() {
    grep -q 'name="ThemeSet" value="art-book-slot"' "$SLOT_SETTINGS" || return 0
    if [ -r "$SLOT_STATE/watch.pid" ]; then
        read -r pid < "$SLOT_STATE/watch.pid"
        case "$pid" in
            ''|*[!0-9]*) ;;
            *)
                if [ -d "/proc/$pid" ] && grep -Fq "$SLOT_ASSETS/launch/watch.py" "/proc/$pid/cmdline"; then
                    return 0
                fi
                ;;
        esac
    fi
    python3 "$SLOT_ASSETS/launch/watch.py" ensure
}

slot_log() {
    mkdir -p "$SLOT_STATE"
    printf '%s %s\n' "$(cut -d' ' -f1 /proc/uptime)" "$*" >> "$SLOT_STATE/hooks.log"
}

slot_early_insert() {
    [ -f "$SLOT_STATE/early" ] || return 1
    stamp=$(sed -n '1p' "$SLOT_STATE/early")
    rom=$(sed -n '2p' "$SLOT_STATE/early")
    case "$stamp" in ''|*[!0-9]*) return 1 ;; esac
    current=$(cut -d' ' -f1 /proc/uptime)
    age=$((${current%.*} - stamp))
    [ "$age" -ge 0 ] && [ "$age" -lt 8 ] || return 1
    clean=$1
    [ -f "$clean" ] || clean=$(printf '%s' "$clean" | sed 's/\\//g')
    [ "$rom" = "$clean" ]
}
