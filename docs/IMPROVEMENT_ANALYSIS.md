# Precision, responsiveness and animation review

Reviewed 2026-10-13 against commit `55cb06b`. This is an analysis; runtime changes have not been implemented in this review. The refined implementation proposal is [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md), and external references are collected in [FRONTEND_RESEARCH.md](FRONTEND_RESEARCH.md).

## Direction

The next milestone should improve the existing systems before packaging. The desired result is recognisable, accurately proportioned hardware, smooth navigation, an immediately usable shelf after eject, and videos cropped to the actual media surface. Preserve the black default background, opaque neighbouring media, top status, regional shells, silent delayed previews and existing shelf/video toggles.

Treat the physical geometry and printed identity as accurate reproductions. The user selected **accurate hardware with restrained cel shading** during plan refinement. Pico-8 is invented hardware and needs its own consistent design standard.

## What was checked

- Current theme generator, media geometry, cart baker, Blender generator, native GLES renderer, launch hooks and return holder.
- Stored all-console/all-cart comparisons and composed handheld overview in `build/shots/all-*-review-after.png` and `all-quality-device-overview.jpg`.
- Existing scroll sampler, unit-test contracts, native timing logs and return-review JSONs.
- Connected handheld status, read only: EmulationStation was running, Art Book Slot was active and no game was running. No input was injected, game launched, theme deployed or settings changed.
- Primary frontend/theme repositories and manufacturer/reference sources linked in the research document.

This review does **not** supply new hardware timings. Measurements below come from the earlier saved captures. Cached Knulli source and the browsed source at commit `10834d004ec3de0808703b46220b6a8574d53218` help explain candidate paths; that revision has not been established as the exact source of the handheld's installed binary.

## Findings

| Area | Evidence | Implication |
|---|---|---|
| Hardware identity | Generic procedural primitives, generic lettering, exaggerated housing thickness, coarse curves | Another detail pass alone will not establish precision; introduce measured references and comparison gates |
| Scroll continuity | 500 ms slides, hard-coded quintic easing in examined frontend source, immediate RGB changes, lazy item creation | Separate frame stalls from velocity/brightness discontinuities before selecting a fix |
| Return usability | Synchronous eject hook followed by frontend restoration; historical DS/PSP handoffs at 4.60/4.67 s | Stable held imagery concealed a remaining return delay; measure the first accepted input explicitly |
| Video placement | One rectangular `minSize` crop per shelf, no shader configured by this project | Aspect ratio is preserved by the crop mode, but the shapes and coverage need redesign |
| PS1 video | Current video bounds are a small rectangle below the hub | Replace with video over the full CD surface, clipped to the outer circle and physical center hole |
| Existing validation | Frame CRCs, settled plastic samples, mesh validity and selected proportions | Useful regression checks, but insufficient evidence for smooth frame pacing, responsive input or overall physical accuracy |

### 1. Why the models still look approximate

`tools/consolebuild/models.py` builds the hardware from boxes, cylinders and a few contours. That is a useful starting point, but its parameters are presentation units, without a source-backed dimensional specification for each part.

Concrete limitations:

- SNES, SNES US, NES, N64 and MD receive a final nonuniform vertical scale of 1.7, 1.7, 2.1, 2.3 and 1.7. In the Blender coordinate mapping this exaggerates thickness. Some ports compensate, but the complete housing remains altered. See the `yscale` setup and final `stretch` in `models.py`, also mirrored in `tools/themebuild/consoles.py`.
- Printed legends use Open Sans SemiBold; some text is compressed horizontally to fit. Nintendo/Sega identity and PSP stroke lettering therefore remain approximations.
- `bevel()` caps curves at three segments and cylinders at 32 sides. Large characteristic curves need more careful allocation of geometry.
- Export applies broad decimation to a roughly 14,000-triangle target. Recognisable contours and thin details need protection rather than equal treatment.
- Native shading has three diffuse bands and a black outline. The material function accepts roughness/metallic arguments, but the authored shader graph and native vertex-colour format do not implement those material properties. Plastic, LCD glass, chrome and printed ink largely share the same response.
- Current meshes carry position, normal and colour, without texture UVs. Accurate decal atlases would require a deliberate exporter/renderer extension or a separate projected decal pass.
- PS1 uses a separate procedural model in `tools/discpreview/preview.py` and `tools/slotlaunch/psx.h`. It needs the same reference checks as the Blender models.
- Shelf/native regional selection uses differently cased filename rules, while the baker has broader case-insensitive tag rules. For example `North America` selects a US SNES shell in the baker but is absent from the native console test. Resolve media and console variants from one contract.

Recommended workflow:

1. Specify the exact revision and region: DMG, CGB, AGS SP, DS Lite, PSP-3000, PAL/SFC versus US SNES, NES front-loader, N64, Model 1 Genesis/MD, and the intended original PlayStation revision.
2. Assemble front, rear, side, top and open/closed references. Record official overall dimensions separately from photograph-derived ratios and uncertain details. Perspective photos are references, not orthographic measurements.
3. Model in physical units. Keep screen framing in camera, uniform object scale and placement. Reconcile cartridge dimensions, slot coordinates and animation clearance in those same units.
4. Establish silhouette, width/depth/height, bezel sizes, control spacing and seam locations first. Then add brand marks, connector geometry, screws, vents and surface treatment.
5. Preserve editable masters. Derive a native asset with a contour-aware triangle budget. Compare the master, exported mesh and actual handheld render.
6. Use precise vector paths for distinctive marks. Consider a small original decal atlas for fine printing; distinguish decals from physical embossed geometry. If textures are added, change the existing test that forbids all GLB images to forbid game imagery while allowing documented hardware decals.
7. Compare at fixed front/top/side cameras and at the actual 720×480 launch camera. Record discrepancies per model; fix them before moving to the next family.

Start with GB/DMG as a simple complete reference model and PSP as the curved/material stress case. Review neutral shading to expose geometry, then compare the existing cel treatment with a lighter outline and restrained material highlights. Roll the accepted workflow through the home consoles and remaining handhelds. Do not equate more triangles with more accuracy.

### 2. Scroll stutter: two problems to distinguish

`tools/themebuild/shelves.py` sets `SLIDE_MS = 500`. Its activate/deactivate/scroll storyboards change colour in 1 ms. Every templated item contains backing, face, logo, paper and fallback text, with repeated dynamic file lookups.

The examined carousel source starts a new `easeOutQuint` animation from the current position on cursor changes. It also ensures nearby items, updates bindings/details and iterates instantiated items to trigger scroll storyboards. These are **candidates**, not a measured cause of the reported stutter. Extending the slide duration changes the movement curve but does not remove a decode/upload stall or preserve velocity when another input arrives.

The old `tools/dev/profile_scroll.py` detects changed framebuffer-row CRCs during a held scroll and omits the initial repeat delay and release/settling period. A changed CRC does not prove evenly paced motion. It cannot isolate a velocity kink, a brightness snap, a first tap, or the transition out of a playing video. Native animation fps also does not measure ES shelf scrolling.

Investigation matrix:

| Dimension | Cases |
|---|---|
| Input | Single taps, repeated taps, held input, immediate direction reversal, wraparound, letter/page jumps |
| Media state | Before video starts, while video plays, missing video, video disabled |
| Cache | First visit, revisiting warm items, immediately after a game |
| Shelf | Large GB/GBC/SNES/NES libraries; PS1, PSP and DS |
| Load | Normal run and composed-display capture, reported separately |

Measure input timestamps, presented-frame intervals, visible cart position and velocity. With frontend instrumentation, time item creation, image decode/upload, bindings, metadata updates and video lifecycle separately. Use bounded logs so profiling does not become the dominant workload.

Choose fixes from evidence:

- If cold-item work stalls: simplify the baked-item path and prefetch a bounded neighbour window; measure RAM/VRAM. Any merged face/backing asset must preserve the opaque silhouette of transparent shells.
- If warm motion still pulses: make repeated navigation preserve movement velocity, preferably with a critically damped spring or equivalent continuous controller. The examined theme exposes duration, not arbitrary carousel easing; a small frontend change may be needed.
- If video teardown correlates with stalls: verify the installed VLC path and move expensive lifecycle work away from input/render processing where supported. The cached source already has asynchronous player release, so do not assume a synchronous VLC stop.
- If brightness is the visible snap: tie dimming to motion progress or a short coherent transition, preserving opaque carts and correct selected brightness after return. Recheck the earlier ghosting regressions.

### 3. Eject finishes before the frontend is usable

The current `gameStop` hook runs `slot_refresh_state` and the eject helper synchronously. ES regains control after configgen returns. For GB/GBC/DS/PSP, native eject motion is 1.75 s plus a 350 ms hold. The return holder forks a detached child, closes inherited graphics and output descriptors, and covers the shelf until a fresh selection event plus eight matching plastic samples remain stable for 120 ms, with a five-second bound.

The five-second bound is **not** a mandatory wait in the parent hook. Reducing it would not prove that input returns earlier. The holder can also conceal a frontend that has already changed behind its saved image; a fixed-cart pixel test may keep failing after navigation or after video coverage changes.

Saved real-game timing in `build/shots/all-quality-native-animation.log`:

| Event since helper startup | DS | PSP |
|---|---:|---:|
| Eject render loop completed | 2.282 s | 2.284 s |
| Helper logged done | 2.394 s | 2.395 s |
| Holder confirmed frontend shelf | 4.605 s | 4.672 s |
| Time from helper done to holder confirmation | 2.211 s | 2.277 s |

These support the user's report of a visible shelf followed by extra delay, but the last timestamp is a **visual readiness proxy**, not the first accepted button. Previous return JSONs only count black frames, blank rows and plastic changes after settling.

The examined Knulli `FileData::launchGame` path waits for the launcher, performs cleanup, recreates the window/input/resources, initializes audio, updates metadata/collections and reactivates the GUI. `ViewController` holds its input lock through launch/return. Determine which stages consume the actual device's time before choosing an implementation.

Next measurement should distinguish:

1. Emulator process exit and `gameStop` entry.
2. State-photo update and other hook completion.
3. Eject motion end, hold end, graphics teardown and helper completion.
4. Configgen exit, renderer/input/audio restoration and metadata/view rebuilding.
5. First valid primary shelf frame, input unlock and holder release.
6. A deliberately scheduled navigation press, its selection event and the first visible movement.

Use separate runs with single timed navigation taps, rather than flooding the input queue. Check menu/cancel input too. Preserve launch/save/metadata snapshots when real games are used.

Likely work order: remove unnecessary synchronous return work, establish an explicit readiness contract, then investigate safely overlapping eject with frontend restoration. A detached renderer drawing through its own display layer could let ES restore underneath it, but this must be demonstrated on Sunxi before changing the hook. The helper currently polls/drains SDL events, so concurrent input ownership also needs review. Keep exit chords from becoming accidental launches and preserve the proven display-layer cleanup.

Do not repeat the already unsuccessful `HideWindow=false`/retained-context experiment without new evidence. The earlier work recorded invalid textures and black intervals.

### 4. Videos: crop first, then mask to the surface

The project's current `minSize` path uses cover cropping. The examined VLC `resize()` scales both dimensions by one factor, then crops the excess. The project does **not** currently configure stretched video. Its poor fit comes from rectangular placement and chosen dimensions.

Use this invariant for every preview: normalize the source display aspect ratio, apply one uniform scale `s = max(target_width/source_width, target_height/source_height)`, crop to the target canvas, then apply the surface mask. Handle non-square pixel aspect ratios and pre-existing borders deliberately. Never independently scale video width and height, and never deform video pixels with squash/stretch animations.

| Media | Intended video surface |
|---|---|
| GB/GBC/GBA | Actual rounded label recess, with plastic and embossed header visible |
| SNES PAL/SFC and US | Separate masks matching each regional label area |
| NES | Label strip with a per-system crop anchor; evaluate how much gameplay a full tall strip removes |
| N64 | Rounded/tapered label shape |
| MD/Genesis/EA | Variant-specific label masks preserving moulding and EA grip |
| PS1 | Full CD face: outer circular boundary minus the physical center hole |
| PSP UMD | Circular exposed disc area clipped by the surrounding UMD case |
| DS | Rounded label area, with card edges/notch preserved |
| Pico-8 | Its artwork screen/window with pixel treatment and credits preserved |

PS1 requirement: the resting preview covers the whole CD, with a circular center cut-out in disc-plane coordinates. Preserve alignment with the existing disc pose; a perfectly front-facing shelf disc is an optional presentation choice. Physical perspective can project that circle into an ellipse without stretching the source in the media plane. The first rollout addresses live shelf previews; native loading needs a separately designed handoff to a printed face or captured still. Preserve a thin edge/bore treatment without restricting gameplay to the current lower rectangle. A dark dot painted over the video is insufficient for an open hole over wallpaper.

The generated PS1 print mask already excludes outside the disc and its bore. Its pose/homography and hub assets provide a useful geometry source, but the video element currently sits above the poster and does not use them. Build video boundaries, foreground rims and return-readiness samples from the same media definition so they cannot drift apart.

**Promising first implementation route:** a theme-level video shader. Browsed Knulli source supports nested custom shaders on video elements and the GLES2 renderer loads them. An analytic annulus can cut the CD and center hole; analytic rounded shapes can cover several cartridges. Custom shader support on the installed Scarab build, its coordinate/uniform conventions, alpha blending and performance still need a device spike. Sources: [VideoVlcComponent at the inspected revision](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/components/VideoVlcComponent.cpp), [GLES2 renderer](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/renderers/Renderer_GLES20.cpp).

Check target-local mask coordinates independently of cropped source UVs. Compile/warm the shader outside the first visible video frame. Keep one active preview decoder and existing three-second delay/reset behavior. If the installed renderer cannot supply true masking, compare a narrowly scoped frontend extension with a theme-only fallback; an opaque black inverse mask only works for the black backdrop and cannot satisfy wallpaper transparency.

Use synthetic 4:3, 16:9, square, vertical and pixel-aspect test videos with circles, grids and moving edge markers. Confirm preserved geometry, complete outside/hole exclusion, antialiased boundaries, no movement over plastic/credits, stable transitions and accurate missing-video fallback. On PS1, move holder-readiness samples off the newly animated full disc face or replace that heuristic with explicit readiness.

## Proposed work order

This initial ordering is expanded and superseded by the staged deliverables and decision gates in [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md).

| Step | Deliverable | Decision it resolves |
|---|---|---|
| A. Baseline and feasibility | Device timing/scroll traces; PS1 shader mask spike; GB/PSP reference boards | Identify the return bottleneck, motion versus frame stalls, shader support and precision standard |
| B. Responsiveness | Independently reviewable scroll and return fixes | Navigation stays smooth and the shelf becomes usable when eject ends |
| C. Media previews | PS1 annulus first, then UMD and each cartridge variant | Crop-only gameplay fits every physical surface |
| D. Hardware accuracy | Approved GB/PSP masters, followed by per-family replacements | Exact proportions, contours, printing, materials and insertion clearance |
| E. Animation consistency | Shared motion/sound rules across browse, preview, launch, return and menus | The whole theme feels like one finished product |
| F. Packaging | Installer/update/uninstall and publication assets | Resume Phase 6 once the quality gates are met |

No frontend replacement is justified by the current evidence. Theme assets, custom shaders, launch-hook improvements and small upstreamable frontend fixes should be evaluated first.

## Proposed acceptance targets

These are targets for the next plan, not achieved measurements. Establish the device baseline before locking them.

- **Scrolling:** target 60 Hz; aim for 95th-percentile presented-frame intervals at or below 20 ms and 99th-percentile at or below 33.3 ms during active movement, with no reproducible navigation stall above 50 ms. Assess continuous motion independently of frame intervals.
- **Return:** a navigation/menu tap sent at visible eject completion is handled; aim for visible response within 100 ms, with no multi-second inactive held shelf. Measure input readiness independently of holder release. If the measured OS recovery prevents this, quantify it and adjust return orchestration rather than merely hiding it.
- **Models:** documented revision/dimensions and landmark comparisons; initial target within 1–2% for source-supported major ratios and about 1–2 pixels for key aligned landmarks at actual display size. Unknown dimensions stay marked uncertain. Visual approval of front/rear/side/loading poses remains required.
- **Video:** circles remain circles after cover cropping in the media plane; zero changing pixels outside the mask or inside the PS1 bore, allowing a separately defined antialias edge band; correct wallpaper visibility through openings.
- **Performance:** retain the current indexed native rendering budget; report normal and capture-loaded timings separately. Reject new material effects that visibly damage browsing or launch pacing.
- **Regression:** all shelf toggles, regional/special shells, wallpaper, selected brightness, rapid relaunch, missing media, saves and display-layer release still work. Extend tests where they validate these outcomes rather than restating implementation.

## Additional ideas

1. A consistent motion language: small selection settle, a restrained preview reveal, physically correct hinge/load/click motion, then a responsive return. Use animation to explain state changes and keep the path interruptible where input is safe.
2. Original system-specific sounds aligned to latch, tray, lid and power events, with consistent volume. Add a quiet navigation tick and a mute choice. Avoid introducing a longer audio wait.
3. Small physical highlights on LCD glass, the PS1 rim and UMD window. Animate them subtly after settling, with a fixed lighting direction across systems.
4. A unified media manifest resolving region/revision, shell, console, label, preview mask and slot path. This removes inconsistent filename rules and makes the shelf/native handoff share geometry.
5. A consistent system-selection transition and menu typography. Art Book Next currently supplies these screens; start with matching accent, spacing and motion, and evaluate custom overrides after the core issues are solved.
6. Optional inspect mode: rotate a cartridge to its rear, expose connectors and show revision/region. Keep it a separate deliberate action so browsing remains fast.
7. Better large-library cues: a briefly shown letter during jumps, a readable title when scanning quickly, and saved position per shelf. Keep the normal shelf visually quiet.
8. A permanent comparison set using blank original media and synthetic videos. Maintain reference-versus-model overlays and frame traces for every accepted revision, without putting personal ROM/game art in publication assets.

## First implementation session

Instrument one DS or PSP real return, profile one large warm/cold cartridge shelf with preview on/off, and test the PS1 annulus shader on the actual installed renderer. In the same quality cycle, prepare the measured DMG/PSP comparison boards. Those concrete results are enough to turn this proposal into a scoped implementation plan without guessing at the bottlenecks.
