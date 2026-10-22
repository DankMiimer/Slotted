# Independent cartridge presentation — implementation

2026-10-16. Implements the [accepted plan](SLOTTED_PRESENTATION_PLAN.md) on the
RG34XX-SP running Knulli Scarab 2026/05/11 (Batocera 42, ARM64/GLES2).

Later quality follow-up: [supplied GBA SP and sharper rendering](MODEL_QUALITY_INTEGRATION.md)
records the installed 81k-triangle local model, 2x live/browse renderer and current
temporary binary. It supersedes the earlier GBA source and 720px model target.

## Delivered behavior

The optional **Independent slotting (frontend extension)** theme subset enables a frontend-owned
scene in the 720×480 cartridge carousel. Down inserts the highlighted game; Up
ejects the inserted game. Neither calls the game launcher. Left/Right remains a
normal, repeat-while-held browser around the independently inserted game.
Confirm keeps normal frontend validation/options, then seats the captured
highlighted game and launches it exactly once. Returning from a game restores
its inserted scene. An INSERTED marker replaces its physical wheel copy.

The top wheel occupies y=0–120. The hardware scene occupies y=120–480. Home
consoles sit left of the [selected Panasonic CRT](TV_MODEL_RESEARCH.md), whose
cabinet fills the lower 360px height on the right. GB/GBC, GBA SP, DS Lite and
PSP content is projected directly onto the registered native LCD vertices.
There is no external metadata panel. The original cartridge, disc, UMD and
hinge mechanisms remain in use; the added motion turns the loaded handheld
forward and frames its display, then reverses that movement before ejecting.

After viewing the first close reading pose, the user requested **50% less
zoom**. GB/GBC, GBA and PSP now use half that magnification, with final-size
text rather than a downscaled old UI. DS frames both screens together: top
artwork/video and fixed game/player/year HUD; bottom scrolling description or
details. Further halving the complete DS view would leave ~64px per screen;
that is unsuitable for readable metadata, so its two-screen framing is retained.

All displays offer overview, complete details, box art, available additional
images, video and library pages using L1/R1. Unknown fields are omitted or
identified as unknown. The description scrolls at 18px/sec, with a 3-second
start pause and 2-second end pause. Title, player count, year and page controls
stay outside that scrolling viewport. Highlight changes do not restart it.
The half-zoom GB/GBC LCD has limited paragraph space; the details page uses
the whole width and includes the complete game title.

One VLC decoder belongs to the inserted game. It starts after the existing
3-second wait, keeps playing while browsing, letterboxes its source and splits
stacked DS footage from the same decoded texture. A still remains available
until a video frame arrives. Cartridge-label video is suspended while the
inserted display owns the decoder. Sparse selected-cart idle motion starts
after 4 seconds, lasts 1.8 seconds and repeats every 10 seconds at 2px amplitude.

DS clips can also embed the stacked picture inside widescreen black borders.
Twelve consistent decoded frames establish a conservative active rectangle,
using a bounded, sparse CPU-pixel sample while VLC already holds the frame.
Only tall content consistent with two stacked 4:3 screens is cropped; black or
ambiguous footage retains its full rectangle. After the first 180 decoded frames,
sampling drops to one frame in 30 until confidence is established. This handles
long black/title introductions without continuous full-frame scanning, readback,
a second decoder or a background FFmpeg process.

Battery/time remain at the top; Wi-Fi moved beside the battery at top-left.
The intermediate request to move them to the bottom was cancelled.

## Source and asset ownership

- Frontend source: Knulli `batocera-emulationstation`, pinned exactly to
  `4041b56a714265de81de8165b34fbd10f313a891`. `tools/frontend/apply.py` refuses
  other revisions, a dirty first-time clone, and locally modified owned outputs.
  It regenerates exact anchors from Git objects and records output hashes.
- Current model baseline: `cd6ca96` from `Slot_ESDE-next-models`, imported with
  an allowlist. Original renderer sources and the installed native helper are
  preserved. Camera adaptations operate on private copied renderer headers.
  Realistic remains the default, with Cel and all paint variants retained.
- `tools/frontend/SlotState.h`: independent loaded/desired/launch identities,
  bounded latest-intent commands, safe-boundary swaps and exactly-once launch.
  Only immutable metadata snapshots cross transitions; no stale `FileData*`.
- `SlotNative.c`: shared GLES2 texture rendered through the actual approved
  loading machinery, without another window/input loop/present. One cached
  bounds readback per model; no readback per animation/idle frame. Mali needs
  `glFinish` before the owner context samples a freshly rendered shared target.
- `SlotPresentation.cpp`: metadata snapshots, display FBOs, LCD projection,
  camera transitions, clipping and media ownership.
- `tools/themebuild/stage.py`: 208 full-silhouette browse renders at 720×240,
  plus fallback housing images. Enlarges the first small prototype without
  distorting tall versus wide systems. `screens.py` derives LCD corners from
  named model geometry. `television.py` registers the attributed TV glass.
- `SlotLaunchGuard.h` plus `_slot/launch/frontend-owned.sh`: one private atomic
  transaction matched by ROM, PID, process-start time and random token. Hooks
  skip the standalone insert/eject only for that live transaction. ES's escaped
  async-hook path is normalized only if the exact unescaped file exists;
  record contents are never evaluated as shell code.

The pre-existing 18 unrelated dirty scraper/video files were hash-checked and
preserved. The scrape was not resumed. Game art stays on the user's device.

## Build and deployment

The working private build lives in WSL at
`/home/mads1/slot-es-presentation/frontend`, with build output in the adjacent
`arm64/` directory. The project supplies the source applier, overlay, state and
input regression probes, cross-build recipe and allowlisted runtime packager.

```sh
python3 tools/frontend/apply.py /path/to/clean/pinned/frontend
SLOT_ES_BUILD_ROOT=/path/to/build-root sh tools/frontend/build.sh
python3 tools/frontend/tests/input.py /path/to/patched/frontend
g++ -std=c++14 tools/frontend/tests/state.cpp -o /tmp/slot-state
/tmp/slot-state
python -m tools.frontend.package build/slotted-presentation/runtime.tar
```

`build.sh` expects an ARM64 GCC/G++ toolchain, CMake, SDL 2.32.8 headers under
`build/native/`, development headers under `$SLOT_ES_BUILD_ROOT/headers/usr/include`
and target libraries under `build/slotted-presentation/lib/`. The verified
development environment uses Ubuntu 24.04 development headers and the device's
SDL2/image/mixer, Mali/EGL, FreeImage, FreeType, VLC, Pulse, udev, eSpeak, ALSA
and curl libraries. It is a **device-tested development cross-build**, not a
reconstructed official Buildroot image or a promise of bit-identical binaries.
The upstream frontend retains its own license; the original helper and new
integration code retain their applicable notices. Model derivatives retain
their individual Creative Commons terms.

`package.py` includes only owned theme paths, stage assets, credits, shared
status and the launch ownership gate. It never deploys the whole dirty theme.
The installed standalone helper SHA-256 remains:
`9a9e2ffcf412b5b192b07db2b89c73973fc030179522425007fa59ffdd9c183f`.
The official frontend SHA-256 is:
`d02c1f349952151ba5cd5b67125e848e95279483230d1582203efd44cf37af64`.

**Release limit:** the public frontend sources do not contain the official
build's private scraper developer credentials. This build does not acquire or
extract them. Built-in services requiring those keys cannot be assumed to work;
the existing external Skraper workflow remains available. The device test uses
a reversible bind mount over `/usr/bin/emulationstation`; the original system
binary is never overwritten. Reboot returns to the official frontend. A durable
firmware/package integration with suitable build credentials remains release
work; do not silently save a whole system overlay to make this prototype persist.

Before device tests, stop ES and run `tools/dev/session_data.py backup NAME` on
the device. Restore with `restore NAME --runtime`, then `audit NAME --runtime`
before reapplying any desired development runtime. Changed/new saves and files
are preserved before restoration. Start ES with `tools/dev/esdev.py start`,
which detaches and redirects service output; starting the init service directly
over SSH caused a restart loop even with the official binary.

## Verified and still unmeasured

- Windows suite: **152 tests, 6 POSIX skips**, passing. Fourteen Linux ownership/gate
  checks and the 50-cycle C++ state/DS source-crop test pass.
- Regression replay executes the **actual patched view input method** against
  Knulli's actual `InputConfig`: hat, axis and keyboard neutral releases stop
  Left/Right repeat; Up/Down are edge-triggered. This catches the device bug
  where neutral hats matched Up/Down and swallowed horizontal release.
- Shared-context native probes: all 13 model variants render populated textures
  with GLES error 0 and complete, unclipped persistent silhouettes. LCD
  coordinates are projected from model vertices. TV
  geometry tests verify every content corner stays on glass and broadcast maps
  are absent from the prepared model.
- Real-device captures verify the top wheel, Panasonic/console layout, GB/GBA/
  GBC/DS/PSP LCD presentation, independent browsing, manual swaps/ejects, fixed HUD
  and scrolling description. Tap and held Right both stop after release.
  A pixel comparison confirms unchanged TV header/HUD while description pixels
  change. A real pillarboxed 856×480 DS clip correctly splits across both LCDs.
- Real GBA launches verify Confirm swaps to Highlighted, runs that ROM and
  returns inserted. The corrected ownership gate produces no duplicate
  standalone insert/eject hook activity; its token is removed on return.
- Captures and logs: ignored `build/slotted-presentation/`. Device snapshots:
  `slotted-prototype-20261016a` through `d`; tests restore game/config/stat files
  and audit hashes before leaving the desired development presentation active.
  The final restore audited 321 data and 869 runtime files with zero changed/new
  files. After reapplying the view and doing inspection-only navigation, a second
  data audit showed only `es_settings.cfg` changed (the enabled feature); saves,
  gamelists/play statistics and emulator configs still matched the snapshot.

The original plan's p95/p99 input/frame targets, incremental 48MiB memory budget,
20–30 minute thermal/battery run, all modal/save-state/netplay combinations and
controller reconnects have **not** been comprehensively measured. VLC's legacy
synchronous release can still stall on a real inserted-game swap. Independent
browsing avoids decoder churn; an asynchronous VLC backport should follow
measurement, not be claimed complete. No unsupported performance or production
readiness claim follows from successful screenshots and average native fps.
