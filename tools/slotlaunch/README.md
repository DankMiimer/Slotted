# Native slot launch helper

`slot-launch.c` is our MIT implementation of the insert/eject motion. It uses the installed
SDL2 and SDL2_image libraries; no SDL library is redistributed. It is currently built for
ARM64 Linux and a 720×480 framebuffer, tested on RG34XXSP / Knulli Scarab.

## Build on Windows + WSL

WSL needs `aarch64-linux-gnu-gcc`, its libc development files, `curl` and `tar`.
With the SSH target in `tools/dev/device.txt` or `$env:SLOT_DEVICE`:

```powershell
. .\tools\slotlaunch\build.ps1
```

This copies the device's SDL shared libraries into ignored `build/native/lib`, downloads
the official SDL 2.32.8 public headers into `build/native`, and writes the stripped helper
to `theme/art-book-slot/_slot/launch/slot-launch`. The generated binary is ignored by git;
it must be present when copying the theme or assembling a release. A tested local binary
is available after the build. `tools/themebuild` generates the theme art independently.

## Runtime

The theme's `_slot/launch/install.py install|uninstall|status` manages three owned hook files:
ES `start`, async ES `game-start`, and synchronous configgen scripts. It leaves settings and
other hooks alone, refuses collisions/symlinks, and supports repeated install/uninstall.
Install and uninstall also remove our earlier `game-selected` hook, never anyone else's file.
Set ES's **Game launch transition** to **Instant** and leave the managed hooks installed.
Selecting the theme alone does not install them. `install.py status` reports all three hooks.
Hooks run only for Art Book Slot, supported ROM folders, enabled shelves and carousel
views. They read active ES settings plus the CR-separated per-theme profile. When enabled,
the save-state photo cache refreshes on exit. Optional wallpaper is also drawn behind the
animated cart, with the same 62% scrim as the shelf.

`start` ensures one sleeping Linux inotify watcher, tied to the ES process; `game-start`
ensures it too, for a theme selected after ES started. Closing a complete `/tmp/game.xml`
export confirms a launch; the watcher starts insert before ES's synchronous audio/display
shutdown. `game-start` remains a fallback.

Do not add `game-selected` hooks. ES forks itself for every event script on every cursor
move and its main thread waits for the fork: measured on the RG34XXSP, each tap then
dropped 2–3 frames at the start of the slide (p99 67 ms, max 84 ms). Without the hook,
rapid taps measure p99 22 ms and max 27 ms (`tools/dev/frame_pacing.py`).
Duplicate command exports are consumed once, with a fresh claim checked against the exact
ROM path. A return resets the debounce so rapid relaunches still work. No input is intercepted.

Insert captures `/dev/fb0` before SDL takes the display. Battery and clock remain
at the top, and eject reuses the saved shelf. The cartridge and DS-card families use
complete 3D console models and their ROM's baked cartridge face. DMG/PSP include
separately credited CC BY authored geometry; see
[MODEL_WORKFLOW.md](../../docs/MODEL_WORKFLOW.md) for sourcing and adaptation and
[MODEL_EXEMPLARS.md](../../docs/MODEL_EXEMPLARS.md) for current evidence. Region
selects the PAL/Japanese or North American SNES housing and the Mega Drive branding.

`console-gl.h` draws indexed coloured meshes into SDL's scene framebuffer with a
private depth attachment, three cel-shading bands and a black silhouette outline.
It restores SDL's GL state and attribute enables after each draw. Indices reuse
transformed vertices; the original unindexed pass ran at about 30 fps on the device,
while the indexed meshes run at roughly 56–59 fps. Model reads are bounded, validate
indices and finite attributes, and fall back to the idle preview if unavailable.

GB/GBC rise with their fronts visible and rotate around to the rear bay. GB receives
the authored Game Pak mesh; dedicated GBC carts receive the complete rounded mesh.
The baked asymmetric switch notch retains the existing compatible GB slab without
changing the media pipeline. The label is clipped
at the retaining lip. Motion lasts 1.85/1.75 seconds.
The open GBA SP receives its authored cartridge connector-first through the front
edge, label toward its underside (Nintendo AGS manual illustration 4). It makes
the short forward turn, reverses it on withdrawal and shares the housing depth.
The real recessed well preserves the existing 266:138 ROM-label crop aspect.
NES rotates its
hinged flap separately, lays the cartridge on its tray, slides it inside and closes.
NES insert lasts 1.20 seconds; the other cartridge consoles insert in 1.15 seconds.
Every eject lasts 1.75 seconds plus the 350 ms hold, matching GB/DS/PSP, while ES
recovers underneath. Input reinitialization can still finish after the motion;
the exemplar report records separate single-tap checks. Short scenes
gain an unseat beat instead of slower motion: top-loader carts spring 22% out of the slot
(GBA SP 30%, enough to protrude from its front slot), hold, then the reversed scene resumes
where its own motion starts. NES plays its door, tray and slide sequence more slowly.
DS uses the same 1.85/1.75 second duration as GB/GBC. Its front-to-rear turn adds a
15-degree tilt to reveal the rear lid and Slot-1;
the card flips label-down, feeds connector-first and compresses the retaining spring before
settling. Return readiness samples the card's outside plastic, away from its wide label
and video window.
Pico-8 uses the home top-loader's 1.15/1.05-second motion with an original fantasy console.
Its 264×338 cartridge preserves the local ROM's artwork. Separate readiness samples stay
on the outside plastic and away from its square video window and printed credits.
Every complete scene fades together. The existing 100 ms insert/350 ms eject holds
and bounded configgen completion remain in place. Build geometry with
`tools/consolebuild/models.py`; its README covers the source and asset licences.

PSP uses `psp.h` with the full cel-shaded PSP-3000 mesh and a separate hinged door range.
The front turns to the rear; the door opens, the free UMD makes a 12-degree
adjustment and straightens before feeding into its holder, then the cover closes.
Eject reverses the adjustment after withdrawal. Motion lasts 1.85/1.75 seconds,
with the same 100 ms insert/350 ms eject holds as PS1. Optical readiness samples use
neighbouring shelf art and console chrome outside the live media face.
PS1 and PSP both present complete scenes through the independent animation layer.

Eject retains a CPU copy of the saved shelf with the baked face composited over any paused
video. On the RG34XXSP's Sunxi display, an unused display layer holds that image while ES
rebuilds the primary layer. Its private uncached ION DMA buffer is separate from framebuffer
storage. `sunxi-layer.h` contains the minimal ARM64 disp2 DMA-buffer ABI bindings.

A detached child closes inherited pipes and graphics descriptors, then reads the primary
framebuffer through fresh read-only descriptors. ES resumes once configgen (the hook's
grandparent) has exited; a framebuffer page flip after that shows ES presenting again.
Then all eight static samples matching for 120 ms confirm the frontend shelf is ready.
A controller press after ES is presenting also releases the holder 50 ms later, once the
cart row is drawn, because browsing deliberately differs from the saved shelf; presses are
observed read-only and still reach ES. ES writing `/tmp/game.xml` (a relaunch) releases it
immediately. ES reloads cart textures asynchronously after a return, so the row check keeps
an empty black shelf hidden. The child then
restores the unused layer and releases its buffer; it stops after at most five seconds.
It holds no SDL context and cannot block configgen's output pipes. It never writes or pans
the primary framebuffer. Unsupported displays or an occupied spare layer skip this holder
and retain the ordinary eject. The launch animation itself still uses SDL.

Both private output and return buffers now use the BSP's IOMMU-backed ION system heap.
The previous CMA allocations could fail after PSP emulator handoffs because of fragmented
contiguous memory, even with free RAM. Private animation output uses ARGB8888, globally
opaque; the saved CPU return image uses XRGB8888. Stage-specific allocation failures are
logged. Audio children close inherited DMA and Mali descriptors before executing the player.

Shelf images set `autoFade=false`, and RGB activation/deactivation is immediate. This avoids
texture-loading and brightness fades when ES recreates the carousel. Positional slides run
at 650 ms, with opaque neighbours at 55% brightness.

Eject overlaps frontend recovery by default: the helper forks before SDL starts, and
configgen is released once the detached scene has latched its first private frame.
`SLOT_RETURN_ASYNC=0` restores the fully synchronous eject. After configgen is released,
Knulli's system gameStop scripts, a fixed 0.5 s sleep and interpreter exit take about
1.2 s, then ES's window/texture/input reload about 1.1 s. Measured first accepted press
after eject motion ends, RG34XXSP, with probe taps 0.25 s apart:

| System | Synchronous | Overlapped, old short ejects | Overlapped, 2.1 s ejects |
|---|---|---|---|
| PSP | about 2.5 s | — | 0.26–0.30 s |
| GBA | about 2.5 s | 0.81–1.0 s | 0.31 s |
| PS1 | about 2.3 s | about 1.0 s | 0.26 s |
| SNES | — | 0.79 s | 0.29 s |

A file lock (`/tmp/art-book-slot-launch/scene.lock`) serializes scenes: the eject and its
shelf holder keep it, and an insert started by an early relaunch waits for it (at most
1.5 s). Keep normal window hiding. See `docs/IMPLEMENTATION_PROGRESS.md` for evidence.

The configgen wait is bounded to 3 s. Insert writes the completion flag even if art or SDL
fails, so a failed animation does not trap a game launch. Diagnostics are in
`/tmp/art-book-slot-launch/animation.log` and `hooks.log`.

## Device validation, 2026-10-09

| System | Insert / eject fps | First insert frame after helper startup |
|---|---|---|
| GBA | 59.3 / 59.3 | 126 ms |
| NES | 59.6 / 59.3 | 141 ms |
| SNES | 55.6 / 59.9 | 125 ms |
| N64 | 59.1 / 59.8 | 131 ms |
| Genesis/MD | 58.5 / 59.3 | 132 ms |
| Genesis/MD EA | 60.3 / 59.7 | 133 ms |

These timings start when the helper process starts, not at the physical A press. SNES insert
was recorded with LCD writeback sampling active, adding measurement overhead. Eight-second
composed LCD recordings passed on GBA, NES and SNES: zero black frames, zero blank horizontal
bands and zero plastic RGB change after eject settled. Evidence is in ignored
`build/shots/timing-dmabuf-{gba,nes,snes}-eject/`. The independent layer released after ES's
redraw in every case; the framebuffer-only sampler cannot see this layer. Raw captures
contain game art and must not be published.

The N64 follow-up recorded a direct A-to-first-frame delay of 486 ms, complete scene clearance
at 1.35 s after the capture started, and 127 composed LCD frames over eight seconds on return.
All 94 samples after eject settled had no black frames, blank bands or plastic RGB changes.
The holder released when ES redrew the shelf, 3.61 s after eject started. Evidence:
`build/shots/n64-launch/`, `n64-return/` and `n64-animation.log`.

Genesis/MD and its taller EA shell recorded A-to-first-frame delays of 575/450 ms. Both
scenes clear completely before launch. Their eight-second composed returns each contain
125 frames, with 93 settled samples and no black frames, blank bands or plastic RGB changes.
The holder releases after 3.65/3.42 s on the frontend redraw. Held scrolling changes in every
one of 122 active intervals (35.2 ms largest sample gap). Evidence: `build/shots/md-insert/`,
`md-eject/`, `md-ea-insert/`, `md-ea-eject/`, `md-scroll/` and `md-animation.log`.

PS1 uses our original Socket-inspired disc/console model in `psx.h`: perspective texture
grids, physical edge/bore walls, rear hinge, separate shadow, spindle and brief seated spin.
Insert runs for 950 ms plus a 100 ms end hold. Eject runs for 1.75 s plus a 350 ms settled
hold: the lid springs open with a slight bounce while the disc spins down one full turn
(ending at its original label angle), then the disc lifts off and returns to the shelf.
Eject ends with the same baked poster as the carousel. Runtime TGA textures are decoded
before SDL takes the display; ring triangles are batched. Ring samples avoid the bore
and video window, preserving the existing independent layer architecture. Final captured
insert measures 58.4 fps, first frames 158/163 ms after startup and 492/536 ms after A.
Composed-LCD eject measures 57.1/57.8 fps. Bugs Bunny/Crash returns contain 127/125 samples
over eight seconds; all 78/77 settled samples (t≥3 s) have no black frames, blank rows or
ring RGB changes. Evidence: `build/shots/psx-insert-final{1,2}/` and `psx-eject-final{1,2}/`.

The PS1 follow-up on 2026-10-10 fixes missing console tiles during seated spin and lid
closure. The same model renders correctly with ES stopped; during early launch, ES's
display teardown can erase stationary parts of the primary framebuffer. Offscreen
rendering alone did not protect the displayed image. `animation-layer.h` now presents
each completed GPU scene through two private uncached DMA buffers on unused channel
2/layer 0, at order 14. SDL readback completes the scene before a buffer is published;
SDL's vsync separates alternating buffers. Occupied or unsupported layers retain the
ordinary SDL presentation. The model geometry, timing and sound remain the same.

On eject, the existing channel 3/order 15 shelf holder latches before the animation
layer is released. Both layers restore their original configuration. Full composed-LCD
Bugs Bunny/Crash insert and eject captures pass the moving-console guard checks, and
their eight-second returns have no settled black frames, blank rows or ring RGB changes.
An uncaptured insert measures 56.0 fps; composed capture adds overhead. Evidence is in
`build/shots/psx-lid-final-*` and `psx-lid-clean.log`. The reusable check is
`python tools/dev/check_psx_animation.py CAPTURE_DIR ANIMATION_LOG --mode insert|eject`.
It checks descent, seating and closure separately from the settled shelf statistics;
the original failing capture is rejected. No game artwork is part of the checker.
This follow-up restores all 15 original PS1 saves and metadata byte-for-byte, with zero
changed settings values. Three new and one changed test save are preserved separately.
All three hooks remain enabled; only the normal primary layer remains active afterward.

The PSP milestone also moves status to the top across theme views. Final PSP composed returns
contain 128/129 samples over eight seconds; all 78/79 settled samples have no black frames,
blank rows or plastic RGB changes. Final captured insert/eject measure 54.4/56.4 fps, with
first frames 174/172 ms after helper startup. Seven descent/seating/closure frames retain both
console shoulders and neighbouring UMDs (neighbour RGB differs by at most one from the saved
shelf). PS1 moving-console checks pass with the new buffers, and PS1/GBA settled return checks
pass with 77/78 samples. GBA insert/eject both measure 59.0 fps. Evidence:
`build/shots/psp-final-*`, `psp-regression-*` and `psp-animation.log`.

`tools/dev/capture_frames.py` reads fresh framebuffer data around an action and compresses
afterward. Use `--display --inspect-cart SYSTEM --stats-only` for composed LCD recordings;
`tools/dev/sunxi_capture.py` supplies private DMA writeback. `--button a` records the direct
input time, while repeated `--button` arguments inject a chord. Allow at least 8 s for returns
so recordings include the later frontend redraw. The native helper uses the `opengles2`
renderer, with software fallback.

Keep normal `HideWindow=true` and `HideWindowFullReinit=false`; retaining ES's graphics
context caused invalid textures and longer black intervals. Reading a final frame from
Mali sometimes produced an empty image, so the holder uses the saved CPU shelf instead.
With the optional `CheckBiosesAtLaunch=false`, A-to-first-frame is about 0.45–0.5 s, compared
with roughly 1.6 s before the early watcher. Manual BIOS checks remain available.

The NES scrolling check changed in all 133 active intervals, largest unchanged gap 34.6 ms.
The final SNES check with synchronous texture loading had a largest unchanged interval of
50.1 ms. These are framebuffer sampling intervals, not internal renderer frame rates.
Original saves, gamelists and the theme profile were restored, with changed/new test saves
preserved separately. Session settings were restored with only `CheckBiosesAtLaunch=false`
retained deliberately. Art Book Slot, Instant and all three hooks remain enabled.

The DS/PSP accuracy refinement is built locally and visually checked with the actual
native GLES renderer in an offscreen WSL run. Both insert/eject sequences pass;
PSP closed-cover samples contain zero bright UMD pixels in the door area. ARM64
compilation and all 57 unit tests pass (the two POSIX gates run separately in WSL).
The follow-up refines the DS D-pad, button heights and joined hinge knuckles, and installs
both models on the RG34XXSP. Composed preview insert/eject: DS 56.9/56.4 fps, PSP
58.5/57.7 fps; closed PSP cover samples hide the UMD completely. Real DS launch/eject
measure 54.9/52.8 fps and PSP 56.4/55.7 fps, with writeback capture running. Both
nine-second returns have no black takeovers or blank card rows after shelf return;
the final 60/61 samples have identical plastic RGB. Label videos can change separately.
All 80 fresh DS/PSP save/config/metadata files were restored byte-for-byte after testing.
No saves changed; three test-modified metadata files are preserved separately. Desktop
screenshots use blank original media; desktop capture rates are not handheld timings.

Pico-8 is installed and device-tested. Composed native previews measure 57.6/55.4 fps;
real Continent Factory insert/eject 54.9/56.1 fps and Marble Merger 53.8/52.6 fps with
display capture running. Direct A to first frame is about 0.48/0.47 s. Both nine-second
return recordings have 61 settled samples with no black frames, blank rows or plastic
changes. The holder confirms frontend readiness at 3.92/4.14 s after eject starts.
Evidence is in `build/shots/pico8-*`; all 59 fresh data files and three ROM hashes match
after testing. No save changed. The final targeted update ZIP has 30 SHA-256 checked files.

The all-console/cart quality pass (2026-10-10) is installed across all 13 console variants.
Printed details skip the outline hull using 0.25-length native normals and vertex-shader
clipping; physical surfaces use unit normals. This preserves early depth testing and
avoids the per-fragment discard slowdown. Degenerate export triangles are omitted.
All 26 composed insert/eject previews measure 55.8–58.9 fps. Closed PSP cover samples
contain zero bright UMD pixels. Real CTGP Nitro DS insert/eject runs at 53.8/57.4 fps,
Angry Birds PSP at 55.8/54.5 fps, with writeback capture active. Both games boot; each
nine-second return has 33 settled samples with no black frames, blank rows or plastic
changes. Frontend readiness is confirmed at 4.60/4.67 s after eject begins. All 298 fresh
save/config/metadata files match after restart; no save changed or was added. Four changed
config/metadata files are preserved separately. The 62 tests, 33 XML parses and warning-clean
ARM64 build pass. Evidence: `build/shots/all-quality-*`, including the native log, full
composed preview recordings and both real return-review JSONs.
