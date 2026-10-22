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

`tools/frontend/build.sh` documents the existing ARM64 H700 build. It requires
Linux/WSL, CMake, an AArch64 GCC/G++ cross compiler, development headers and target
libraries matching the firmware. Set `SLOT_ES_BUILD_ROOT` to the directory holding
the dedicated `frontend/`, `headers/` and `arm64/` folders. Inspect the script's
explicit SDL2, GLES/Mali, FreeImage, VLC, FreeType, curl, ALSA, PulseAudio, udev and
espeak paths before building. SDL headers are expected at
`build/native/SDL-release-2.32.8/include/`; target libraries at
`build/slotted-presentation/lib/`. These proprietary/system binaries and the
author's prepared sysroot are not bundled. Preparing a clean target sysroot is
still a manual prerequisite; an end-to-end fresh ARM64 build is not verified
by this publication work. Do not use host libraries in place of target libraries.

The native launch helper has separate `tools/slotlaunch/build.sh` / `build.ps1`
scripts and expects target SDL libraries. No executable is included in the
public source export. Before distributing a compiled frontend, audit its exact
dependencies and include all required notices and corresponding source where
applicable. The pinned frontend's own MIT notice is retained in `LICENSES/`.

## Device configuration and install boundaries

Configure SSH key access, then set `SLOT_DEVICE` to your target, or put it in the
ignored `tools/dev/device.txt`. Never commit passwords, keys, settings snapshots
or saves. No publication command connects to a device.

Existing Slotted installers/trials copy shared `_slot` files from an installed
Art Book Slot theme. They were developed for that migration path. A fresh device
needs the shared runtime, compatible frontend, launch helper and registered
layouts deployed as a reviewed set; a theme-only package is insufficient. Keep
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
