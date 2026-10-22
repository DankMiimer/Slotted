# Seamless system switching — research and implementation design

20 October 2026. User request: remove the long black interval between consoles;
animate console and cartridges off screen and the next set into their exact saved
layout; change TVs when the destination layout calls for it. Keep browsing snappy
by preparing expected resources and retiring unused ones.

**Status (20 Oct follow-up): integrated implementation is device-tested and
installed as n17, SHA-256
`722c5b0803f2b37b42ee5f6a33ba0c0dae4ee2c13d66ce721761027f7f3b7890`.** The original research below
is retained as measured history. See the current implementation checkpoint in
[TABLETOP_HANDOFF.md](TABLETOP_HANDOFF.md). Selected full-detail models and authored
layouts remain unchanged.

## Recommendation

Keep one scene session alive across system changes. Retain the room, camera,
shaders and render targets; stream hardware and game labels as independent
resources. Predict the neighboring systems, prepare their CPU data in a worker,
and complete GPU preparation ahead of the gesture where possible. Both tested
upload strategies still cause frame spikes; preallocation and upload scheduling
need another measured increment. The animation is then a small
transient transform on real geometry, rather than a screen hiding a synchronous
load. An uncached request must continue drawing the existing scene while it is
prepared. There is no reason to replace the scene with black.

The saved destination remains authoritative: exact console/cart transforms,
chosen TV, furniture, table scale, cameras and display settings. All intermediate
motion is disposable runtime state. Never write animation values into a saved
JSON, browser draft or native `.scene`.

## What the current implementation does

At the pinned public frontend revision `4041b56a714265de81de8165b34fbd10f313a891`:

| Location | Finding | Consequence |
|---|---|---|
| `tools/frontend/apply.py`, generated `CarouselGameListView::onHide()` | Resets the presentation when leaving a list outside a launch. | Ordinary system browsing tears down graphics and loaded state. |
| `SlotPresentation.cpp::tabletop()` | Closes the old renderer and opens another when its root/system/TV/style/colour/SP key changes, inside rendering. | Input, drawing and animation wait for the whole new scene. |
| `SlotTabletop.cpp::slot_tabletop_open()` | Creates a context, compiles shaders, allocates output/scene/depth targets, loads the table, TV, console, media and regional alternative, then reads the layout. | Shared room resources are repeatedly reconstructed. |
| `SlotTabletop.cpp::image()` / `mesh()` | Image decoding, source/UV integrity checks, texture upload, mip generation and vertex/index upload are synchronous. | Reading from an OS file cache still requires decode, validation and GPU preparation. |
| `slot_tabletop_items()` | Loads up to twelve labels before returning. `trimLabels()` immediately retires everything outside the current window/resident. | No adjacent label window is ready for fast browsing. |
| `SlotPresentation::highlight()` / `SlotNative.c::slot_native_prefetch()` | Warms the legacy helper's two-entry CPU albedo cache. The tabletop loader calls `IMG_Load` independently. | Existing “prefetch” does not feed this renderer; it can duplicate work and memory. |
| Pinned `ViewController::playViewTransition()` | Has independent slide/fade/instant transitions. Its fade contains a 320 ms black hold in addition to two 240 ms ramps. | A tabletop coordinator must own tabletop-to-tabletop visual transitions. The existence of this branch does **not** prove it is active. |

Read-only device settings: list `TransitionStyle` absent (source default `auto`),
game-launch transition `instant`, global TV `oldtv`, startup `recent`. The live
list-transition mode was not instrumented; do not attribute the user's black
interval to the fade's fixed hold. The synchronous construction cost is measured
independently. Game-launch transitions and validation remain a separate path.

The device currently has nine installed authored profiles for eleven integrated
systems. Mega Drive and PICO-8 borrow an existing composition until authored.
The profile resolver correctly prefers the same console across TV variants, but
the renderer still uses the *requested global TV's geometry*, adjusting a saved
other-TV profile to fit it. To fulfill this new request, ordinary browsing must
resolve both the profile **and its TV asset** together. A deliberate editor
preview remains an explicit system/TV request; global settings need no rewrite.

## Device measurements

Valid native load study: `switch-study-20261020-023222-50e413`, 44 loads
(eleven systems × two aspects × two passes). Times include open, twelve item
bindings and first GPU-completed frame, but exclude ordinary frontend navigation,
metadata/video and fade/slide. Console groups request their saved Panasonic or
PVM TV; the current global `oldtv` selection is not being timed here.

| System | TV tested | Construction to first completed frame, min–max |
|---|---|---:|
| SNES | Panasonic | 2.65–2.84 s |
| NES | Panasonic | 2.21–2.28 s |
| N64 | Panasonic | 2.37–2.43 s |
| Mega Drive | Panasonic | 2.49–2.63 s |
| PlayStation | Panasonic | 2.95–3.06 s |
| Game Boy | PVM | 8.04–8.24 s |
| Game Boy Color | PVM | 8.25–9.03 s |
| GBA SP | PVM | 7.65–8.02 s |
| DS Lite | PVM | 7.96–8.15 s |
| PSP | PVM | 7.94–8.18 s |
| PICO-8 | Panasonic | 2.13–2.24 s |

Median image decode per system group is 1.51–2.12 s with Panasonic and
4.79–5.20 s with PVM. Context creation's median is only 1.37 ms and shader
compilation's is 20.85 ms: retaining those is sensible, but **image/resource
preparation dominates**. Repeating a system after earlier visits still pays the
cost; OS file caching is not a decoded/GPU resource cache.

Short departure studies also expose a separate rendering problem: worst per-run
motion p95 ranges from 25.3 ms (N64) to 150.4 ms (GBA), and most PVM studies miss
33.3 ms. Neither prefetch nor the fact that geometry can fly proves a smooth
integrated transition. Investigate camera-relative travel/TV overlap and room
redraw costs without dropping detail; profile draw counts and CPU/GPU work in a
longer continuous animation. These are 25-frame feasibility samples, including
early warm-up behavior, not acceptance benchmarks.

CPU/staged-upload study `switch-study-20261020-023916-37c31d` keeps a full SNES/
Panasonic scene drawing, forces complete 3D redraws, and prepares a 4096² PVM
texture without showing it:

| Stage | Samples | Frame p50 | Frame p95 | Maximum |
|---|---:|---:|---:|---:|
| Scene alone | 90 | 26.64 ms | 27.26 ms | 56.91 ms |
| CPU image decode on one worker | 90 | 26.59 ms | 31.24 ms | 36.84 ms |
| New texture, 1 MiB strip per frame + scene | 64 | 52.10 ms | 52.89 ms | 54.55 ms |

Decode/conversion took 1,135 ms off the render thread. Empty 4K texture allocation
still took 28.0 ms and final mip generation 42.1 ms, measured with completion.
This **rejects 1 MiB staged main-context uploads as a sufficient smoothness fix**
on this driver. Worker decode is promising; GPU upload ownership needs its own
experiment. A separate shared EGL pbuffer/context study is documented with its
results below; desktop success alone does not establish Mali success.

Shared-context study `switch-study-20261020-024320-dd8a8b` creates an EGL pbuffer
and a context sharing the scene's resources. One worker uploads the same full
4096² RGBA texture and generates mips; it waits for completion **on the worker**
before publication. The main scene continues drawing. A separate framebuffer
then samples sixteen uploaded base-level pixels against their CPU originals.

| Shared upload result | Measured on Mali-G31 |
|---|---:|
| Context/surface creation | 44.4 ms |
| Worker upload + mip generation + completion | 275.8 ms |
| Main scene, all 90 frames: p50 / p95 / maximum | 26.58 / 50.87 / 70.07 ms |
| Five frames overlapping upload: p50 / maximum | 51.14 / 70.07 ms |
| Worker exit / GL error | 0 / 0 |
| Sixteen base-level pixel samples match | Yes |
| Process RSS / high-water mark after shared upload | 345.2 / 349.8 MiB |

**Threaded GPU preparation is feasible, but this experiment also misses the
33.3 ms frame target during upload.** It has one texture, one context creation,
short timings and sampled base-level validation; no claim of all-mip identity,
race-free production shutdown, sustained load or complete-frame equivalence.
Keep one upload context for the session rather than creating it per switch.
Next compare preallocated inactive texture slots and smaller upload batches with
the same completion/identity checks, recording overlapping-frame maxima. Never
present a 90-frame median as proof that the upload caused no hitch.

The user's subsequent cleanup was acknowledged. Read-only `statvfs` reports
**285.56 GiB free** on userdata after that message. This permits optional
hash-bound preparation caches and retained recovery evidence, but changes no RAM
or frame-time result. No files were removed as part of this study, and none of
the clean snapshots was restored over that cleanup. Final free space is
**285.28 GiB** after retaining the last fresh research snapshot and outputs.

## Memory evidence

Read-only baseline: 2,027,140 KiB total RAM, 1,420,004 KiB available; frontend
RSS 522,032 KiB and high-water mark 555,196 KiB. No swap. This is one observed
state, not a memory allowance for every game, video or menu combination.

Installed texture headers establish these costs without changing their pixels:

| Shared scenery | Original runtime textures | RGBA base levels | With a complete mip chain, approximately |
|---|---|---:|---:|
| Current wooden tabletop | One 4096² PNG | 64 MiB | 85.3 MiB |
| Sony PVM | Four 4096² images | 256 MiB | 341.3 MiB |
| Panasonic | Two 1024² images | 8 MiB | 10.7 MiB |
| Old TV | Four 2048² PNGs | 64 MiB | 85.3 MiB |
| Alternative TV stand | One 4096² PNG | 64 MiB | 85.3 MiB |

These figures exclude geometry, render targets, driver allocation/tiling,
temporary decode/conversion buffers and frontend caches. Three of the PVM's
`.png` files, and both Panasonic `.png` files, actually contain JPEG streams;
inspect signatures/SOF dimensions, not filenames or PNG headers alone. The
complete inventory checks both formats. A compressed file size is not a GPU
residency estimate. PVM and table alone account for roughly **426.7 MiB with
mips**, justifying shared ownership instead of a complete scene per cached system.

Proposed initial **tuning limits**, to verify under the full frontend:

- Pin the active room and hardware. Deduplicate common meshes/textures by asset
  identity; never evict a live draw's resource.
- Keep one incoming GPU hardware bundle and at most one recent bundle within a
  shared 128 MiB *optional* hardware budget. This is a soft cap: a larger active
  source is retained at full quality, while optional predictions are declined.
- One CPU preparation worker; start with a 96 MiB decoded/staging cap, including
  reservations for conversion's raw+RGBA peak. A single 4K image can require
  128 MiB temporarily, so this cap is also soft for the active request: admit one
  oversize image exclusively after retiring speculation. Never deadlock waiting
  for an image that cannot fit the nominal cap.
- Predict only previous/next visible systems and a bounded adjacent label window.
  Prioritize current requested hardware, then its twelve visible labels, then
  the likely navigation direction. The opposite neighbor can stay CPU-only.
- Keep at least 256 MiB of measured available system memory as an initial reserve;
  adapt downward or disable speculation under pressure. Release predictions and
  transient CPU pixels before emulator handoff. Tune against actual Mali memory
  accounting and RSS plateau tests, not these provisional numbers alone.

No lower-resolution replacements, texture recompression, decimation, source
substitutions, reduced antialiasing or model-setting changes are part of this
design.

## Scene ownership and animation

The session belongs to the window/ViewController lifetime, not to any individual
game-list presentation. Views pass immutable descriptions to it; hiding one list
stops its preview and input state without destroying the shared room. Actual
frontend shutdown, graphics-context loss and game handoff still have explicit
release/cancellation paths.

1. A system request increments a generation number and reprioritizes preparation.
   Continue rendering immediately; input and menus remain responsive. A cached
   neighbor can start departure in the next frame. For an uncached destination,
   a small anticipation motion can acknowledge input while the old scene remains
   visible; do not fly everything away and leave an empty table for seconds.
2. Console and its moving parts, any seated cartridge, and loose carts leave in
   about 200–240 ms. Use a small cart stagger, approximately 6–8 ms/item and no
   more than 80 ms total. These are starting values for device review.
3. Once destination resources are ready and departure is complete, commit the
   matching generation. Retain the table. The same TV at the same world pose stays
   put; a changed TV moves with its glass and status as one group. If the same
   cabinet has a different authored pose, interpolate to that pose. When furniture
   changes, prepare the new furniture before changing the visible room too.
4. Incoming hardware flies in from the opposite side and settles over about
   280–340 ms. Use a zero-velocity endpoint without bouncing through the tabletop.
   Cross-console camera changes interpolate from the *actual current camera* to
   the saved destination browse camera, finishing on its exact values. Honour
   manually selected views within each system and existing profile pan settings;
   a system-switch duration is separate from the user's launch/inspection pan.
5. Settle to literal authored matrices, with no accumulated integration error.
   TV metadata belongs to the committed loaded identity; the persistent system
   info/status must never flash stale labels as if they belonged to the new game.

The private `SlotSystemFlight.h` study uses camera-relative rigid 3D transforms
and quintic ease. The console's parts and label surfaces travel together. Native
draws use the existing shared depth, lighting, viewport culling and fitted near
plane. The table remains present; optional TV/status motion is grouped. It is
**not wired into `SlotPresentation` or ViewController**. Its endpoint tests and
captures prove the transform/landing approach, not a completed UI animation.

Rapid taps/holds must replace the pending destination, not enqueue every
intermediate console. A canceled generation can finish a small indivisible read
or upload, but cannot publish a scene or touch a newer identity. Never join a
still-running loader from the animation/update path. A partially entering scene
must reverse/replan from its current pose rather than snapping home first.

Selection/navigation can continue while preparation runs. A press that would
insert or launch must be checked against the currently committed game/list
identity and readiness. Do not replay an old A press after another system lands.
Ordinary A insert/swap, A on loaded game, R3, Select+R3, L3, options and exactly-once
launch validation remain intact. Unsupported tabletop systems use the ordinary
frontend view; don't invent missing 3D models for this transition.

## Streaming pipeline

Use separate resource states: requested → reading/validating → decoded → queued
for upload → GPU-ready → visible → retired. Cancellation and failed loads are
explicit states, not “ready with missing parts.”

The CPU worker reads meshes, validates sidecars/hashes, computes bounds and
decodes labels/albedo into owned buffers. It never uses FileData pointers after
the view changes, modifies a live GL object, or takes ownership of the render
context. Existing native-helper CPU prefetch should be skipped on the tabletop
path once this shared loader exists; retain it for the legacy fallback.

One candidate is uploading on the render thread into **new** textures/buffers.
Reserve storage, then transfer strips or bounded mesh batches before drawing a
frame. The measured 1 MiB candidate misses the frame target; smaller chunks and
an approximately 2 ms submission budget remain experiments, not an approved
production choice. Stop speculation when animation consumes the frame. Allocation,
mipmap generation and a single GL call cannot be preempted by a stopwatch: each
must be measured separately. Mark GPU-ready only after all required meshes,
labels, textures and mips are usable. Active full-detail objects never briefly
appear as an untextured stand-in.

Arm documents how modifying resources still referenced by queued Mali draws can
stall the pipeline or create extra “ghost” allocations. It also recommends
grouping updates before drawing. This supports preparing new immutable resource
names and retaining old ones until retirement.
[Arm: efficiently updating dynamic resources](https://developer.arm.com/community/arm-community-blogs/b/mobile-graphics-and-gaming-blog/posts/mali-performance-6-efficiently-updating-dynamic-resources).

The current renderer has a shared scene context and calls `glFinish()` after
every frame. Preserve that working synchronization in the first implementation.
Replacing it is a separate measured change: a plain `glFlush()` does not establish
cross-context texture completion. CPU threading and staged main-context uploads
can be tested without changing this policy.
[OpenGL ES 2.0 specification, sections 2.2 and 5.1](https://registry.khronos.org/OpenGL/specs/es/2.0/es_full_spec_2.0.pdf).

A shared upload context passes the private completion/pixel test, with the frame
spikes recorded above. Production use still needs proven context/thread ownership and
visibility on the actual EGL/Mali stack, including shutdown/cancellation.
SDL's context creation also makes the new context current; existing open/close
functions cannot simply be called from a worker while another thread owns their
restored `owner` context.
[SDL2 CreateContext](https://wiki.libsdl.org/SDL2/SDL_GL_CreateContext),
[SDL2 MakeCurrent](https://wiki.libsdl.org/SDL2/SDL_GL_MakeCurrent).

EGL fence sync can provide a capability-gated completion mechanism; polling with
a zero timeout need not block the render thread. Flush the producer correctly
and retain resources until the fence signals. Query the installed extensions
before using it. Desktop PBO/fence examples are not proof of GLES2 core support.
[EGL_KHR_fence_sync specification](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_fence_sync.txt).

Cache identity includes the actual asset/registration versions, resolved layout,
TV/furniture, regional media choices, SP alternative and appearance. A profile or
asset update invalidates that entry. Calculate file integrity once during CPU
preparation, then retain the validated resource; do not repeatedly hash a large
PNG on the frame thread. Any disk-derived cache must retain full pixel data,
be versioned/hash-bound, and remain disposable alongside the preserved originals.

## Private evidence and limits

Evidence root: `build/system-switch-research-20261020/`. The benchmark includes
the actual `SlotTabletop.cpp` implementation in a private executable; wrappers
time image decode, texture submission, mip generation, buffer upload, context
creation and shader compilation. It does not change the production renderer.

- Probe open/items/first-frame/close measurements use all eleven systems, twelve
  cartridge instances, selected current source geometry, both 3:2 and 4:3, and two
  passes in one process. No filesystem cache drop, no reboot-cold claim. First
  pass is a first visit in that process; repeat still recreates GPU resources.
  Nine systems supply twelve distinct real label images; DS supplies eleven and
  PICO-8 three, repeated to fill this stress window. This intentionally exceeds
  small-library counts and is not proof of production small-list behavior.
- The historical `png_ms` column times `IMG_Load` for **both PNG and JPEG**.
  API wrapper timings are CPU call durations, not isolated GPU times. First frame
  and motion submission include `glFinish()`. Uploaded-byte totals are cumulative
  base-level/target/buffer traffic estimates, excluding mip/depth/driver overhead;
  they are **not** actual resident VRAM.
- The motion study renders a fixed authored overview and moves queued real
  geometry. It does not simulate metadata/video, concurrent CPU preparation,
  ViewController layout loading, live input or cancellation. Its 25-sample timing
  per departure is feasibility evidence, not long-run p95 acceptance.
- Host SNES and GBA studies render source-quality 2x supersampling with llvmpipe;
  the device retains its chosen native 4x MSAA path. Home and final landing are
  pixel-identical. Crops already present in authored cameras are retained and
  must not be reported as newly verified full-frame layouts.
- An initial private probe incorrectly reused an already-consumed draw queue.
  Its flight images/timings are invalid. Its child was explicitly stopped; the
  worker audited all 326 data/1,720 runtime files clean and reopened n16. Corrected
  code retains the immutable home draws. The failed evidence is retained, not
  silently mixed into valid results.

## Implementation increments and acceptance

1. Introduce session ownership and resource handles, retaining one context,
   table, shaders, targets and same-TV geometry across list changes. Keep the
   normal launch-release path explicit. Instrument full frontend frame gaps and
   allocation/resource counts before changing its navigation transition.
2. Extend the upload research with one persistent upload context, preallocated
   inactive slots and measured batching. Resolve the full-detail PVM/motion
   redraw costs. Then add generation-based CPU preparation, byte reservations,
   the measured upload policy, priority and bounded previous/next prefetch.
   Ensure the renderer can keep
   drawing throughout an intentionally delayed read and failed/canceled load.
3. Connect transient departures/arrivals, TV/status grouping and saved camera
   interpolation. Bypass ViewController's ordinary list fade/slide **only** for
   eligible tabletop-to-tabletop changes owned by this session. Never globally
   change the user's transition preferences or the validated game-launch path.
4. Run full frontend/device acceptance and persistently deploy a binary-only
   increment using the editor's fresh-snapshot/hash/restore/audit transaction.
   Do not include saved layouts or models in that payload unless separately
   required and explicitly owned. Update the compatible editor frontend record
   only after the feature actually works.

Acceptance targets (not yet achieved): visible input acknowledgment by the next
frame; a prepared switch completing in roughly 0.5–0.65 s; moving-frame p95 within
33.3 ms on the device. Log maximum/p99 frame gaps, preparation-to-ready latency,
texture/buffer upload maxima, cache hit rate and actual memory high-water marks.
Do not stretch a half-second animation to mask a multi-second load.

Verify thirty+ rapid changes, direction reversals and wraparound, pending-load
failure, a missing texture, slow storage, memory pressure, same TV/different TV,
same/different furniture, every regional/SP/cartridge choice and both aspects.
Compare every saved endpoint numerically and selected captures pixelwise. Repeat
enough switches to demonstrate a resource-count/memory plateau. Check twelve
distinct label identities, loaded-cart residency, no preview-decoder duplication,
and that the source/profile hashes remain unchanged. Finally replay the actual
patched input and real insert/swap/eject/launch/return with ordinary launch guards
and a clean save/settings audit.

An arbitrary uncached jump can still take time to read and decode. The design
guarantees continued scene rendering and lets common predicted changes be ready
before the user requests them; it does not claim zero storage latency for every
possible destination. Removing black screens, responsive input, smooth motion
and fast resource readiness must be measured separately.

## Preservation, reproducibility and actual state

- Completed load/flight session: `switch-study-20261020-023222-50e413`; private
  binary SHA-256 `384a22c388f240686454b34434e8bcde4d4f0d741838e69eaa521afd64e65e9f`.
- Completed CPU/strip session: `switch-study-20261020-023916-37c31d`; private
  binary SHA-256 `04011535e06701c51174b93742156c03627b856eb62f8a8e56dc48939bbac703`.
- Completed shared-context session: `switch-study-20261020-024320-dd8a8b`; private
  binary SHA-256 `74f086a5fd4a2758fa775da446ddcac8ffcc978e832c2d03a62d104b5616bd4e`.
- Each unique session takes a fresh standard snapshot with the frontend stopped,
  blocks on a running game/editor upload, retains the process preview environment,
  audits all **326 data + 1,720 runtime files**, and reopens the unchanged frontend
  in `finally`. All completed audits are clean; no restoration was necessary.
  The discarded initial motion probe also ended with a clean audit.
- All nine installed layout hashes match before/after each session. All **460**
  protected original host source/model/layout files match their initial hashes.
  New research code is separate; no source/archive/alternative was replaced.
- Host flight math tests pass; native SNES/GBA home/landing captures match
  pixel-for-pixel in 3:2 and 4:3 on the device. Host shared-context test also
  passes its completion/pixel check. The actual pinned view input replay passes.
  New Python files compile. Source-level ordinary launch/input behavior is
  unchanged; no new actual game launch was performed or claimed.
- Installed frontend stays n16, SHA-256
  `152a1498e27717fa7ecaf2d49a6eb5e0e02e115d94f5629376269e9b1de2adb1`.
  Last transaction reopened PID 8818, no running game, original SDL environment
  and no preview override. Global TV remains `oldtv`, StartupSystem `recent`.
  No new binary selection, persistent startup change or editor frontend-record
  update was made. Scene editor/browser drafts were not reloaded or edited.

Commands from the repository in WSL:

```sh
sh tools/tabletop/build_switch_probe.sh
CXX=aarch64-linux-gnu-g++ SLOT_SCENE_LIBS=$PWD/build/slotted-presentation/lib \
  SLOT_SCENE_GLES=libmali.so sh tools/tabletop/build_switch_probe.sh \
  build/system-switch-research-20261020/switch-probe-arm64
python3 tools/frontend/tests/input.py ~/slot-es-presentation/frontend
g++ -O2 -std=c++14 -Wno-misleading-indentation \
  -Itools/frontend/overlay/es-app/src/components \
  tools/frontend/tests/system_flight.cpp \
  -o build/system-switch-research-20261020/system-flight-test
build/system-switch-research-20261020/system-flight-test
```

Host-side `python -m tools.tabletop.run_switch_research` dispatches an immutable
private device job; `--stream-only` limits it to the streaming study. Fetch with
`--fetch` (and `--images` for captures). These are development transactions, not
deployment commands. Older job manifests/results remain in their own directories;
the latest pointer never substitutes for those records. `texture_inventory.py`
provides the signature-aware PNG/JPEG dimension inventory.


## Integrated implementation follow-up (20 October)

The user authorized implementation after reviewing the research. The frontend
now retains one native scene across eligible console and handheld views, so the
outgoing table scene remains rendered while an incoming request prepares. The
ordinary menu/non-tabletop and actual emulator launch paths retain their normal
ownership. The initial frontend start and return from an emulator still prepare
a scene; the change targets browsing between tabletop systems.

`SlotTabletopStream.inc` copies each requested system, TV, GBA alternative and
label list, and uses generation numbers to discard obsolete work. One persistent
shared EGL pbuffer context handles CPU decode and GPU preparation. It pauses GPU
uploads during console departure/arrival and the existing insert, inspection and
power/launch motions. It never joins a worker on system navigation. The old scene
continues rendering on a cold miss; no loading overlay or black fade is inserted.

GPU resources have shared leases and deferred deletion on a current context.
Room meshes/textures are shared; up to three prepared hardware bundles and two
expected neighbors are considered. The optional-resource soft cap is 768 MiB,
with a 256 MiB MemAvailable reserve. Active/incoming assets and decoder scratch
can temporarily exceed that cap. Six room slots cover the three existing table
choices and three TVs, still subject to that byte/memory budget. An earlier
three-room limit evicted PVM when a saved table variant was visited; increasing
that limit removed the measured multi-second return-to-PVM reload. No asset was
resized, recompressed, decimated, substituted, stripped of mipmaps or changed in
quality. Native 4x MSAA is retained.

Hardware flies out in 240 ms and in over 320 ms, with camera-relative rigid
transforms and eased motion. A changed TV travels with its glass/status; an
unchanged TV stays and moves between its saved poses. Camera and table transforms
interpolate to the destination's authored values. A completed transition returns
to the exact saved matrices; no editor JSON, camera, history or browser draft is
rewritten. Twelve cartridges remain supported.

The original GPU warm-up experiment was removed after two private device runs
showed no consistent benefit. The final native renderer and full frontend are
separate measurements: low native transition times do not establish the complete
frontend's frame rate. First-use GPU spikes and full UI overhead remain limits;
this implementation does not claim steady 30 fps or instant cold asset creation.

Evidence for the integrated work is under
`build/system-switch-implementation-20261020/`. The current handoff identifies
final tested/installed hashes and sessions; earlier candidates and failed probe
attempts are retained with their actual scope. The original research above
remains historical evidence, not a description of the current installed state.


Final native session `transition-native-20261020-034049-fb0582` passes all four
same/changed-TV and 3:2/4:3 cases, exact landing pixels/cameras, thirty rapid
requests and shutdown during preparation. Final same-hash GUI trial
`transition-ui-20261020-033453-c5259f` passes repeated system walks, rapid input,
real validated SNES launch/return, exactly one play-count increment and a switch
after return. The corrected GUI completion check returns from utility views to a
visible tabletop before waiting for native settlement; earlier harness timeouts
remain explicitly excluded evidence.

Binary-only install `transition-n17-20261020-034251-de18f4` uses an empty theme
manifest. Fresh 326-data/1,720-runtime audit is clean; nine layout hashes match,
normal StartupSystem `recent` and global TV `oldtv` remain, no preview/profiling
environment is inherited. Persistent activation hashes verify. Models, labels,
materials, originals, source archives, authored JSON/history and browser drafts
remain unchanged. See the handoff for recovery paths and the current device PID.

Most final first-walk switches finish in 0.67-0.93 s (PSX 1.35 s), including the
flight. The cache correction reduces GBC/PVM preparation to 226/204 ms on the two
walks. Request-time tracked resources remain 571-627 MiB; frontend walk peak RSS
is about 941 MiB. Native GBA arrival p95 is 26.48/29.36 ms, but the first stable
frame reaches 168/177 ms; full frontend logging is around 18 fps. These are
separate measurements, and the remaining spikes preclude a steady-30-fps claim.
Further optimization should profile that first stable GPU wait and the full UI
frame cost while preserving all source quality and saved cameras.
