# Development setup

Slotted is a theme **and a native frontend extension**. This source snapshot is
not a stock-theme-only installer or a portable firmware image. Hardware evidence
is primarily from RG34XXSP / Knulli; other targets need testing.

## Host editor and theme tools

Use Python 3.11+, Git, Pillow, numpy and resvg-py (`requirements-dev.txt`). The
cartridge/video tools also use ffmpeg/ffprobe on PATH. Geometry authoring uses
Blender 4.5 with scripts run via `--disable-autoexec --python-exit-code 1 -t 1`.
Blender's `bpy` is not a normal pip dependency for these workflows.

The public export contains `assets/restore-map.json`, prepared TV/table meshes,
registrations, a neutral editor default, generated room surfaces and the three
licensed furniture source GLBs. Restore these local prerequisites:

```sh
python -m tools.publication.restore_assets
python tools/tabletop/editor/server.py
```

Restore checks all asset hashes before writing, copies only missing files and
refuses differing existing files. It does not replace authored profiles, browser
drafts, local models or device data. It restores furniture originals into their
expected ignored `research/` paths for the existing Blender importer. Other
historical model importers may still need original creator downloads described
in their provenance; prepared runtime GLBs/meshes and masters supplied in the
theme do not need rebuilding to use the editor.

The editor listens on loopback port 8765 and downloads Three.js 0.170.0 on first
use, with its MIT license. Neutral game surfaces remain blank until you supply
your own artwork. Never add scraped/cached artwork to publication inputs.

`python -m tools.slotted.build` regenerates Slotted XML and original TV graphics.
`python -m tools.slotted.install --package-only` packages those files without
device access. Neither command compiles a frontend or bootstraps a new device.

## Custom frontend

The supported upstream pin is
`4041b56a714265de81de8165b34fbd10f313a891` in
[knulli-cfw/batocera-emulationstation](https://github.com/knulli-cfw/batocera-emulationstation).
Use a dedicated clean clone; the patcher refuses another revision and protects
previous patch output against overwriting local edits.

```sh
git clone https://github.com/knulli-cfw/batocera-emulationstation.git frontend
git -C frontend checkout 4041b56a714265de81de8165b34fbd10f313a891
python -m tools.frontend.apply frontend
```

The [build/install guide](BUILD_AND_INSTALL.md) provides the fresh ARM64 H700
recipe. `tools/frontend/prepare_build.py` fetches the pinned frontend/submodule,
verifies 17 locked API-header packages and SDL headers, and records user-supplied
target firmware libraries. `tools/frontend/build.sh` verifies that workspace and
records the compiled frontend. A fresh end-to-end Ubuntu 24.04/WSL build has
passed; different firmware/hardware and bit-identical builds remain unverified.
Do not use host libraries in place of target libraries.

`tools/frontend/build_helper.py` builds the native launch helper using the same
verified workspace. Historical `tools/slotlaunch/build.sh` / `build.ps1` scripts
remain available for older setups. No executable is included in the
public source export. Before distributing a compiled frontend, audit its exact
dependencies and include all required notices and corresponding source where
applicable. The pinned frontend's own MIT notice is retained in `LICENSES/`.

## Native screenshot and input regression (host)

`tools/frontend/tests/build_room_host.py` makes a separate x86-64 test frontend
from a prepared workspace. It uses test-only FreeImage/VLC/mixer stand-ins, a
fixed 16 ms frame step and fixed status values (75%, Wi-Fi, 12:34); it is never
installed. `tools/frontend/tests/native_room.py` runs it in a private user/mount
namespace with a synthetic five-system library (empty launch targets, generated
art, long titles/descriptions, missing images), replays a scripted input file and
saves room and TV-UI captures plus a per-frame state log (`frames.tsv`).

```sh
python3 -m tools.frontend.tests.build_room_host \
  --output "$HOME/slotted-room-test" --sdk "$HOME/slotted-sdk"
python3 -m tools.frontend.tests.native_room --build "$HOME/slotted-room-test" \
  --source build/public-candidate --output build/captures/oldtv-720 --tv oldtv --width 720
python3 -m tools.frontend.tests.native_room --compare build/captures/oldtv-720-new \
  --baseline build/captures/oldtv-720 --output build/captures/oldtv-720-diff
```

It needs Linux with unprivileged user namespaces, Mesa EGL (surfaceless) and host
SDL2, SDL2_image, GLESv2, EGL, FreeType, curl, PulseAudio, udev and ALSA
libraries; pass `--libraries` for a directory that supplies any missing ones.
`--tv` takes `panasonic`, `pvm`, `oldtv` or `retro` (which documents the current
Panasonic-cabinet fallback) and `--width` 720 or 640. The default script is
`room-regression-script.txt`; `--script` replays `room-script.txt` (insert, R3,
menus, R2/L2 with remembered media, eject, TV channels), `room-travel-script.txt`,
`room-collections-script.txt` and the other room scripts.

Comparison is exact RGB with no masks or tolerance, and refuses captures made
under different TV/size/script conditions; difference images are kept for every
changed capture. Repeated runs of the same binary have been pixel-identical. Make
baselines locally from a known-good commit; they are not committed. These are
llvmpipe host captures without audio/video playback: useful layout/input
evidence, not Mali hardware or device acceptance.

## Device configuration and install boundaries

Configure SSH key access, then set `SLOT_DEVICE` to your target, or put it in the
ignored `tools/dev/device.txt`. Never commit passwords, keys, settings snapshots
or saves. No publication command connects to a device.

`tools.slotted.standalone` packages a complete runtime, compatible frontend,
launch helper and saved layouts from a verified public export. Its fresh-install
transaction checks exact target library hashes and refuses an existing Slotted
theme. Theme-only updates preserve the installed runtime and frontend; the
historical migration path can still copy shared files from Art Book Slot. See
the build/install guide for the separate commands and current test limits. Keep
Art Book Slot and recovery data until you have accepted Slotted on your device.

Use the existing snapshot/apply/verify/restart/restore/audit transaction tools.
An actual device layout upload also needs a device-specific compatible frontend
record and binary hash; these private records are intentionally not exported.
Do not reuse another person's session or frontend record. Slotted currently has
remaining startup/travel performance and wider-variant acceptance work; a source
archive does not certify every feature on every target.

## Verification

```sh
python -m unittest discover -s tests -p test_publication.py
python -m tools.publication.export --verify PATH_TO_PUBLIC_EXPORT
```

The broader `tests/` suite has asset/native/WSL/device-dependent cases. Run
appropriate tests for a runtime change and report missing prerequisites. Model
rebuilds, host probes, protected hardware trials and permanent installs are
distinct validation levels. Publication CI checks the export and host-only
publication tests; it does not claim hardware coverage.
