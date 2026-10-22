# Independent slotting, connected displays and living cartridges

Research and implementation plan, 2026-10-16. **Implementation was authorized with
“GO AHEAD” and is now available as an opt-in, pinned frontend extension.** See
[implementation and validation](SLOTTED_PRESENTATION_IMPLEMENTATION.md) for the
actual delivery, device evidence and remaining release limits.

## Accepted layout and subsequent corrections

- Preserve the existing native cartridge loading/ejecting and lid/hinge sequences.
- Left/Right changes Highlighted while Inserted stays seated. Confirm swaps to
  Highlighted and launches once. Up/Down never launches a game.
- Keep the cartridge wheel in the **top 120px** of the 720×480 inserted view.
  Render the physical scene in the **bottom 360px**.
- Home systems: console left, selected **1990s Panasonic home CRT** right at
  the full 360px scene height. All game metadata is confined to its glass.
  [TV shortlist, assessment and attribution](TV_MODEL_RESEARCH.md).
- GB/GBC, GBA SP, DS Lite and PSP: game metadata is confined to their actual
  registered LCD geometry. DS shows art/HUD above and scrolling text below.
- Fixed title/player/year HUD; the description auto-scrolls with a start/end
  pause. Shoulder pages expose complete details, larger art and library fields.
- The user requested doubling the small prototype hardware/carts, then reduced
  the close single-screen reading zoom by **50%** after seeing it. DS already
  frames both LCDs; retain that combined framing for text readability.
- The latest status correction keeps battery and time **at the top**, with
  **Wi-Fi moved to the left beside the battery**. The interim bottom-status
  request was cancelled.
- Use the approved `cd6ca96` model baseline. **Realistic** remains its default;
  Cel and all existing paint variants are preserved.

The research and proposed acceptance targets below record the original design
investigation. This accepted contract supersedes the early lower-ribbon and
original-CRT suggestions. Performance targets below remain targets unless the
implementation evidence explicitly records a measurement.

This plan promotes console-screen presentation and richer animation from optional
ideas in [the earlier improvement plan](IMPROVEMENT_PLAN.md) to core work. The
existing accuracy and responsiveness requirements still apply.

## 1. Recommendation

Build a persistent **slotted presentation** inside the existing frontend. Down seats the highlighted game, Up removes the seated game, and neither action launches an emulator. A connected CRT, or a handheld's own display, presents the seated game's artwork, preview and metadata. Keep browsing independent from this presentation.

Three choices were explicitly settled with the user during this research:

- **Left/Right browses other cartridges while the current game stays slotted.**
- **Play/Confirm launches the highlighted game, swapping it in first if another game is slotted.**
- **GB/GBC use their own screens too, with a zoom for readable information.**

The largest engineering issue is ownership of input and persistent state. The inspected Knulli engine does not expose the required independent loaded-game state or directional slot actions through theme XML. Recommend a narrowly scoped, opt-in frontend extension, with the theme and generated assets supplying appearance. First prove its build, input, screen and video integration on the target firmware. Do not commit to all-system artwork production before that gate.

The bottom model replacement is a separate, lower-risk delivery and should proceed early in implementation. Most bottom images already derive from the newer models; their extreme cropping is a substantial part of the problem.

## 2. What research establishes

| Finding | Evidence | Consequence |
|---|---|---|
| This is Knulli/Batocera EmulationStation, not ES-DE | Project handoff; Knulli's [theme documentation](https://knulli.org/configure/customization/themes/) | Use this engine's source and APIs. An ES-DE theme example cannot establish feasibility here. |
| The device runs Scarab 2026/05/11 | [Existing device evidence](IMPLEMENTATION_PROGRESS.md); the [release recipe](https://github.com/knulli-cfw/knulli-linux/blob/20260511/package/emulationstation/knulli-emulationstation/knulli-emulationstation.mk) pins `4041b56a714265de81de8165b34fbd10f313a891` | Device version and original binary hashes were confirmed during implementation; the private build uses this exact source pin. The recipe alone does not establish a bit-identical official binary. |
| Horizontal carousel navigation already reserves Left/Right for selection | Pinned [CarouselComponent.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-core/src/components/CarouselComponent.cpp), `input()` | Up/Down are plausible new controls, but need frontend handling and correct press/release routing. |
| Normal confirmation and system switching are handled by the frontend | Pinned [ISimpleGameListView.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-app/src/views/gamelist/ISimpleGameListView.cpp), `input()`, `launchSelectedGame()` | Intercept only the opted-in shelf. Preserve mapped Confirm/Back, long-press options, folders, launch options and system navigation. |
| Theme bindings normally track the cursor's game | Pinned [CarouselGameListView.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-app/src/views/gamelist/CarouselGameListView.cpp), `updateInfoPanel()`; [bindings documentation](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/THEMES_BINDINGS.md) | Existing `{game:...}` bindings would change the TV while browsing. The seated display needs a separate, stable data source. |
| Storyboards support repeating property animation | Pinned [theme documentation](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/THEMES.md), plus `ThemeStoryboard.cpp` and `StoryboardAnimator.cpp` | Idle motion is feasible. Arbitrary storyboard event names do not create controller handlers or writable game state. |
| The current helper is a transient launch renderer | `tools/slotlaunch/slot-launch.c`; `_slot/launch/watch.py` and `art-book-slot-early.sh` | It starts from confirmed `/tmp/game.xml`, fades out and exits. It drains SDL events and has no persistent metadata display. Its preview mode is useful for diagnostics, not a finished inspection mode. |
| Bottom assets are cropped model renders | `tools/themebuild/consoles.py:build()`, `shelves.py:shelf_xml()`; inspected GBA band and full render | `band-console-*` is a 720×58 crop. Replacing a file path alone will leave barely visible hardware. PS1 also has a separate `band-psx` path to audit. |
| Current video teardown can stall | Pinned [Scarab VideoVlcComponent.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-core/src/components/VideoVlcComponent.cpp); [recorded 105–134 ms navigation stalls](IMPLEMENTATION_PROGRESS.md) | Keep the inserted preview alive while browsing. Swaps still need lifecycle work; measure an upstream-compatible asynchronous-release change if necessary. |
| Rich metadata is already represented locally | Pinned [MetaData.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-app/src/MetaData.cpp) and bindings reference | Read the in-memory library and existing local media. No new scrape is required to prove the feature. |

These are source and local-asset findings. This proposal includes no new device performance measurements. The [research notebook](FRONTEND_RESEARCH.md) contains broader design references; [Pegasus](https://pegasus-frontend.org/docs/themes/overview/) is an example of a more programmable theme architecture, not evidence that Knulli XML has the same facilities.

## 3. Exact interaction contract

Use **Highlighted** for the cartridge under the browse cursor and **Inserted** for the game physically seated in the scene. They may differ. The display and loaded console always follow Inserted; the carousel and ordinary game options follow Highlighted.

| Input | Empty console | A game is inserted |
|---|---|---|
| Left/Right | Browse as today | Browse as today; keep the inserted game, console model, display page and preview playback unchanged |
| Down | Insert the highlighted playable game; stop in the presentation state | Same game: no-op. Different game: eject the old one and insert the highlighted one; stop in the presentation state |
| Up | No-op with a quiet empty-slot cue | Eject the inserted game, even when another cartridge is highlighted; return it to its own shelf position |
| Play/Confirm | Validate ordinary launch options, insert the highlighted game, then launch once | Same game: launch without another insert. Different game: validate, swap, then launch the highlighted game once |
| Back | Existing folder/system behavior | Existing back navigation remains available; clear the presentation as that shelf is left |
| Menu, game options, search | Existing actions | Preserve their targets and mappings; suspend decorative motion while a modal is open |

“Confirm” means the user's mapped short-confirm action, not a hard-coded physical A button. A long Confirm must keep its existing save-state/game-options behavior and must not accidentally arm launch.

### State and consistency rules

- Track `highlightedGameId`, `insertedGameId`, `transitionTargetId`, `pendingLaunchId`, scene phase and display page independently. Identity is source system plus normalized source ROM path, not title, basename or carousel index. Collections and multidisc launch entries must resolve to the real source entry.
- `Down` captures its target at press time. If browsing continues during insertion, the destination does not change underneath the moving cartridge.
- Serial phases: empty → inserting → inserted → ejecting → empty. Swap is ejecting(old) → inserting(new). Launch adds validation → seating if required → committed launch → running → return presentation.
- Commit the inserted identity when seating completes; clear it when removal completes. During swaps the old display turns off before the new identity appears. An immutable transition snapshot prevents mixed title/art/region frames.
- Up/Down are edge-triggered: holding the direction never repeats insert/eject. Consume the corresponding releases without leaking them into carousel movement. Test D-pad hats, analog thresholds, keyboard and controller reconnects.
- Browse remains responsive during manual motion. Mechanical commands are serialized: retain at most one latest pending insert/eject request, and at most one captured launch target. Never queue a launch per repeated press. A later explicit slot command can cancel an uncommitted pending launch.
- Start with **safe-boundary cancellation**: finish the current mechanical step, then honor the newest command. Do not promise immediate reversal through a closed UMD door. Add continuous reversal only for mechanisms whose geometry and sounds support it.
- Launch validation dialogs complete before destructive scene changes. Any delayed continuation revalidates its captured game ID and view generation. Cancel, missing ROM, BIOS/options rejection or launch failure must leave a coherent usable shelf.
- An inserted cartridge gets a clearly labeled empty position or “INSERTED” marker in the carousel. Do not draw a second solid copy on the shelf. This marker remains selectable, launchable and present in counts. If its offscreen game is ejected, return it to the logical shelf location without flying through unrelated cartridges.
- While Highlighted differs from Inserted, show both titles and an explicit action such as “Swap & play: <highlighted title>.” Color alone is insufficient. Up's help label names the inserted game.

### Lifetime and navigation boundaries

Keep inserted state while browsing within the same physical-system shelf, opening a temporary menu, searching or filtering that shelf. If filtering hides the inserted game, retain the loaded scene and its identity; it can still be ejected. Resolve identities again after library reload and clear a removed/unavailable game safely; never retain a dangling `FileData*`.

Leaving for a different physical system, selecting a different theme or restarting ES clears the presentation. No persistent “inserted” flag is written to gamelists. A group/alias that resolves to the same physical platform need not force an eject. Mixed-system collections initially keep their existing presentation unless the extension can demonstrate correct per-entry console ownership; do not silently seat a DS card in a PSP.

**Proposed return behavior:** return from a real game to the same inserted presentation, ready to browse, eject or replay. This matches a console that still contains its game and avoids an unwanted automatic eject. It changes today's return scene and requires explicit validation with the launch hooks. If the user prefers automatic eject after play, that can be a setting after the persistent return path works.

## 4. Scene design and information hierarchy

“TV” here means a retro television rendered within the theme scene. This proposal does not change HDMI routing or add an external physical display dependency.

### Home-console scene

Use the selected, attributed Panasonic CRT with a recognizable casing, glass,
controls and feet, connected to the correct console. A near-frontal active
screen preserves legibility; avoid deep perspective and a cluttered room set.

There are two compositions, not a dense TV squeezed into today's cartridge layout:

- **Browse / empty:** the familiar large selected cartridge and dim neighbors remain dominant. A recognizable full console occupies the lower stage. A quiet powered-off TV may be small/backgrounded.
- **Inserted / browsing:** the seated console and lit display become the main
  scene. The cartridge browser shrinks into the top quarter; Left/Right still
  scrolls it while the display remains bound to Inserted.

At 720×480, prototype a 28–36 px status zone, about 300 px for the inserted display stage and 100–120 px for the cartridge ribbon/action hints. These are layout budgets to verify, not accepted final coordinates. A 320×240 active CRT picture already consumes half the panel width: a 160 px box cover plus a 160 px metadata column leaves little reading room. Use focused pages rather than shrinking everything.

### Handheld scene

GBA uses the existing open **GBA SP**, DS the **DS Lite**, and PSP the **PSP-3000**. After insertion into a rear slot/drive, rotate back to a readable front pose; today's terminal rear loading pose is unsuitable for a live screen. Keep the game attached to the console transform during that turn.

| Hardware | Main screen treatment | Critical limitation |
|---|---|---|
| GBA SP | Artwork or 3:2 preview on its own LCD; separate facts/description pages on that LCD | Screen size in the complete model is too small for a paragraph. Move the camera toward it for a reading page. |
| DS Lite | Top: art/video. Bottom: title and short facts; description/gallery pages can use both | Portrait stacked footage must split into two 4:3 source rectangles. The current shelf's top-screen-only crop is not valid for this mode. |
| PSP-3000 | Use the wide LCD for art/video with a compact facts region or separate reading page | Maintain correct source proportions; 4:3 footage is pillarboxed, not stretched to PSP's wide opening. |

“As much as possible” means useful access to the available library, not every field simultaneously. A reading page should zoom the same physical screen toward the viewer while leaving enough bezel to preserve identity. Render text for its final panel size, not at emulated LCD resolution before scaling it up. Keep game imagery at its proper aspect ratio.

Start native-size review with 20–22 px description text and an 18 px minimum for essential metadata on the 720×480 panel. Measure the final projected glyphs, including perspective; a nominal font size before projection is insufficient. If a complete handheld cannot fit that text, zoom its screen or shorten the page. Validate long words and accented/non-Latin names against the available font coverage. Decorative pixel lettering is appropriate for short labels, not automatically for long descriptions.

The user explicitly chose the **GB/GBC's own LCDs with a reading zoom** during this research. Apply the same art/preview and information-page logic, retaining their characteristic screen shape and restrained material treatment. Keep text crisp at the final panel size; an authentic low-resolution or green-tinted appearance must not make paragraphs unreadable. A TV adapter scene is unnecessary for the agreed scope. Pico-8 uses the existing fantasy console connected to the CRT.

### Artwork, facts and pages

Read local library metadata and resolve media once when the inserted identity changes. Existing fields can supply name, release date/year, developer, publisher, genre, players, rating, description, region, language, favorite, play count, play time and last played. Manual/map/achievement availability can be indicated when established locally. Achievement presence does not establish live completion/progress; do not invent it or require network lookups.

| Page | Content and fallback | Presentation rule |
|---|---|---|
| Overview | Logo/title, one strong image, year/genre/players; add developer/publisher when room permits | A useful first image immediately, with a clear title even when art is missing |
| Gameplay | Existing preview; otherwise screenshot → title shot → cover → baked label → title | Preserve full frame by default on the CRT/LCD; retain cropping on existing label previews only |
| Details | Description, developer/publisher, full release date, region/language and rating if present | Wrapped text, fixed readable type, bounded pages; preserve paragraph breaks |
| Gallery | Distinct box front/back, title shot, screenshot, fanart, cartridge art | Contain printed covers/logos so titles and credits are not cropped; crop decorative fanart deliberately |
| Your library | Favorite, last played, play count/time; local manual/map/state availability | Label rating versus personal statistics; hide absent fields and scraper sentinel defaults |

Do not blindly assume `{game:image}` is a screenshot: an ES scrape may use a composite or cover there. Resolve semantic media roles with explicit metadata/local conventions, deduplicate identical paths, and record fallback reasons. Use the full resolved title where disambiguation matters; retain a filename suffix/region in the action cue if short names collide. Names and descriptions are text, never markup or shell input.

Overview appears when seating ends. Keep the existing **three-second, silent preview policy**: count from the new inserted game becoming stable; browsing other games must not restart this timer. Returning to an already inserted game may resume its preview; user toggles still apply. A page switch away from gameplay freezes or hides the live surface without recreating the decoder merely to show a static cover.

For manual pages, prefer L1/R1 only after verifying existing mappings and page-jump behavior on the target. Do not take Up/Down or Left/Right away from their agreed actions, or steal X/Y/options/search functions. Provide a visible page indicator; if the shoulder keys conflict, use an explicit display-focused information action that preserves existing defaults. Slow automatic gallery cycling may be optional, pauses on user interaction, and must not take a description away while it is being read.

## 5. Replace the bottom placeholders with recognizable models

The current generator positions each full render below the panel, then crops only `y=422..480` into `band-console-<model>.png`. The inspected GBA result shows little more than the top of the SP lid. Most paths therefore already point at newer artwork while the composition still resembles a placeholder. PS1 uses a separate disc/console path and needs the same endpoint audit.

Deliver a new **transparent browse-stage render** from the current model source, with a camera and uniform scale chosen to show each console's characteristic silhouette, controls, loading bay or lid. Prototype a 96–140 px visible stage, allowing a taller silhouette to rise behind rather than cover the cartridge. Test the shallow PSP and tall SP/DS independently. Rebalance the cartridge's vertical position only as needed; its label and existing preview must remain readable.

Create distinct empty, loaded and loading poses from one model/profile. The browse endpoint must match the first insertion pose, and the loaded endpoint must match the live-display pose. Export foreground occluders for slot lips/lids and screen openings, so media cannot sit visibly over closed plastic. Keep the legacy 58 px band as an explicit compatibility layout if needed, not the default solution to this request.

Resolve model/region from the **inserted profile** while loaded. Browsing a USA SNES cartridge must not morph a seated PAL console. On a real swap, coordinate the region/model change with the empty transition. Replace the current scattered filename heuristics with one shared region/media resolver rather than adding a third divergent rule. Respect special cartridge variants even where they use the same console housing.

This integration reuses the existing newer models; it does not certify them as physically exact. [The reference cards](HARDWARE_REFERENCE_CARDS.md) still identify approximation and printing issues. Do not delay a useful framing fix until every model has been rebuilt, or call reframing a completed accuracy pass. Keep editable GLB/mesh sources and original-asset licensing boundaries intact.

## 6. Action and idle animation direction

Use specific mechanical beats and quiet material motion. Motion must clarify where a cartridge went, which console owns it and whether the screen is ready. It should not make the whole interface continuously restless.

| Event | Proposed motion | Starting timing range, to test |
|---|---|---|
| Selection settles | Small rigid tilt/settle, shadow tightens, light settles on the label | 120–220 ms after carousel movement |
| Selected idle | Gentle rigid rock or slow highlight drift, separated by long rests | Start after 4–6 s idle; a 1–2 s phrase every 8–14 s, roughly 1–2° / 1–2 panel pixels maximum |
| Manual insertion | Align → enter → seat/latch → settle; lid/drive follows the real mechanism | About 0.7–1.4 s for simple carts; 1.4–2.0 s for rear/door mechanisms |
| Display activation | LED/contact cue, brief CRT warm-up or LCD backlight rise, then readable image | 150–300 ms; overlap with seating settle |
| Manual ejection | Screen off → unseat/spring → withdraw → return to shelf | About 0.6–1.2 s; longer only where physical motion needs it |
| Swap | Eject old → fit new region/model if needed → insert new; one coherent display change | Target under 2.5 s simple / 3.5 s hinged; validate physical readability |
| Play already inserted | Confirm cue / display pull-in → ordinary launcher | No second loading animation |
| Return from game | Restore loaded front pose and display; brief settle once input/resources are ready | Readiness-driven; no decorative fixed hold |

These are proposed tuning ranges, **not measured performance promises**. Today's 2.1 s eject was lengthened to cover emulator/frontend recovery. Manual Up has no such recovery to conceal; copying that delay would make this feature needlessly slow. Keep the actual return path separate.

Family-specific actions: top-loader contact and spring release; NES flap/tray motion; DS push-click and correct label-down feed; PSP UMD door, holder and latch; PS1 lid/spindle and a brief disc spin-down hidden correctly by the closed lid. Do not idle-spin a visible game disc through the console lid or float a cartridge whose feet/shadow imply contact.

Apply motion to the **whole cartridge group**: backing, shell, printed label, fallback art/text, projected video, shadow and selection marker. Independent layer rotation would expose cutouts or make the preview slide off the label. Begin with rigid 2D motion; any 3D rocking needs consistent perspective mapping for every surface. No squash/stretch of game imagery.

Only the highlighted non-inserted cartridge idles. An inserted game's shelf marker does not impersonate a second physical cartridge. Pause idle on input, modal views, launch/return, hidden/offscreen views, sleep and screensaver. Start a fresh idle delay afterward. Reduced-motion mode keeps clear state changes and mechanical endpoints while disabling idle, CRT flicker and large camera travel. Sound remains muted unless existing theme/system volume permits it; sync one sound to each mechanical event, without duplicate hook playback.

## 7. Architecture and feasibility gate

### Options considered

| Approach | Strength | Critical weakness | Recommendation |
|---|---|---|---|
| Theme XML only | Easy distribution; works with current engine | Can animate/react to exposed bindings, but cannot own the required directional state and independent inserted identity | Use for model framing, idle and appearance; insufficient for the complete feature |
| External evdev watcher plus persistent SDL helper | Reuses some native graphics code | Competes with ES for input/display, lacks authoritative UI focus and metadata, creates duplicate launch/overlay risks | Reject as the default architecture |
| Frontend extension plus theme assets | ES owns input, identity, media lifecycle and launch; clean scene stays interactive | Requires a maintained firmware-specific build and rendering integration | Preferred path, contingent on an on-device prototype |
| Replace the entire frontend with Pegasus/custom launcher | Full programmability | Migrates library/options/collections/launch/recovery and abandons the theme add-on premise | Out of scope for this request |

### Preferred boundary

Add an opt-in slot controller and presentation component around `CarouselGameListView`, leaving stock views unchanged. Example **new API proposals**, not existing XML capabilities: a `slot` context with phase, inserted game, highlighted game, pending target and display page; explicit `slot-insert`, `slot-eject` and `slot-ready` events. Keep game metadata fields on the resolved game object rather than inventing duplicated title fields.

The frontend remains the single input and launch authority. The theme supplies layout, art, screen styling, motion parameters and help presentation. Reuse the existing `FileData` library, normal launch-option checks and launcher. No shell launch on Up/Down, fake launch entries, `/tmp/game.xml` writes, play-counter changes or save/state operations are part of manual slotting.

Keep inserted bindings outside the cursor-driven details container: its normal scrolling/clearing updates must not hide the loaded display, blank its title or rebind video `enabled` on every highlight change. Any new slot context must be explicitly passed to the relevant subtree; merely renaming `{game:...}` fields does not create an independent binding lifetime.

First render with generated static housings/occluders and native frontend media/text. For movement, test compact pose layers plus projected cartridge planes generated from the current model/timeline. **Rendering choice remains a prototype decision:** compare that bounded asset path with a small frontend-native GLES mesh component if sprite poses cannot preserve the accepted loading motion. The current C/SDL renderer cannot be dropped unchanged into ES's renderer/context. Share pure transforms/profile data where useful, not its SDL window or display layer. Do not build both engines fully before choosing.

The preferred long-term result is a reproducible source patch with a versioned feature capability and matching theme assets. Keep base theme compatibility explicit. Do not advertise independent slotting on a stock binary that lacks the feature. Unsupported firmware falls back to the ordinary shelf and existing real-launch behavior. Installation must support verified binary/resource compatibility and rollback; a theme zip alone cannot deliver this extension.

Knulli's [build guide](https://knulli.org/development/building-knulli-with-docker/) describes a Linux/Docker firmware build and more than 180 GB disk for that route. First determine whether an existing matching SDK/build tree permits a frontend-only package. Do not assume the small native-helper build is sufficient, or start a full firmware build as part of this planning task.

### Screen rendering and one decoder

Compose the inserted game's static art and metadata in screen-local coordinates, then map that surface into the CRT/LCD opening. Use the same camera/profile landmarks for the housing, masks and media projection. Apply glass/scanlines subtly to imagery, with readable text contrast protected. An expensive bloom chain or severe CRT curvature is optional after the baseline passes.

Keep **one live preview decoder**. When a game is inserted, the existing highlighted-cartridge video must yield to the inserted screen; other highlighted cartridges use static artwork. With an empty console, today's delayed label preview can remain. This tradeoff avoids decoding one game on the TV and another on a selected label simultaneously.

For DS, one stacked source texture can feed two screen quads in the new component. This needs demonstrated shared-texture access or a single multi-window shader; two XML video elements do not establish a single decoder. Detect/record source layout: stacked, side-by-side, single screen, borders and aspect ratio. Do not apply today's portrait heuristic to arbitrary footage. Start with stills on both screens before proving live split video. If layout is unknown, show the complete source safely and keep facts on the other screen.

Keep uniform source scaling. CRT/LCD gameplay defaults to contain/letterbox; boxes/logos contain; decorative backgrounds may crop. Source sample-aspect corrections remain necessary on Scarab, as recorded in [the existing video evidence](IMPLEMENTATION_PROGRESS.md). Introduce a screen surface/profile instead of reusing the label shader's meaning implicitly. Validate opaque plastic, open PS1 bore, UMD enclosure and screen masks independently.

### Launch/return integration

The current watcher still observes an actual launch and would run another insert unless coordinated. Add a one-shot launch transaction containing source game ID, view/session generation, scene endpoint and an unguessable per-attempt token. Consume the bypass only for that committed launch, clear it on failure/exit, and retain ordinary hook fallback when the extension is absent. Do not suppress hooks using only a ROM name or age-based marker.

Confirm on an already inserted game reuses the loaded endpoint; Confirm on another captures and swaps its target before launching once. During actual game execution the scene releases its decoder/render resources. Return resolves the game again, rebuilds any invalidated graphics resources and presents the inserted endpoint before exposing controls. Validate rapid replay and launch failure.

Prefer an explicit frontend-ready signal for the new path: view restored, required textures available, first frame presented, input dispatch unlocked. The native holder's historical screenshot/pixel tests are compatibility behavior, not a sufficient state contract for a TV full of moving video. If a helper overlay is retained during real return, keep one scene owner, bounded cleanup and a readiness handshake; verify it cannot cover a newly launched game. Never mark an inspection as a play session.

## 8. Resource and responsiveness budgets

Record the baseline on the actual device, matching library, power-saving mode, assets and capture conditions. Initial acceptance targets below may be revised with evidence; they are not achieved measurements.

- Input to visible acknowledgment: p95 ≤100 ms for manual commands and ordinary browsing, including while another game remains inserted. No “input is disabled until animation ends” policy.
- Active animation: aim for 60 Hz, with p99 presented-frame intervals ≤33.3 ms and no repeatable new >50 ms stall attributable to the feature on cached navigation. Report cold loads and video swaps separately rather than excluding them from the experience.
- Provisional incremental resident-memory budget: ≤48 MiB for the current system's scene/animation assets. Establish total frontend headroom first; reduce the feature budget if the baseline cannot afford it. Bound the cache to the active system plus a small upcoming working set, not all consoles/games.
- A 720×480 RGBA frame is about 1.32 MiB; 60 full frames are about 79.1 MiB before textures and double buffers. Even 30 frames at 360×240 are about 9.9 MiB. These calculations favor layered poses or meshes over full-scene animation atlases. Compressed PNG size is not GPU memory cost.
- No per-selection subprocess fork, full gamelist parse, network request, full-ROM CRC or image rebake. Do not restore the removed `game-selected` launch watcher; it caused the measured scroll stutter.
- Static/hidden screens stop decorative updates; idle is sparse. Compare normal power-saving behavior with idle disabled and enabled, including a 20–30 minute heat/battery observation. Do not globally disable power saving just to animate a light.

Existing Skraper encodes were sized for small cartridge labels, often ≤240 px. They may look soft on a much larger TV. Retain/use original higher-resolution local media when available, and generate larger derivatives only where the new output needs them. Do not upscale a 240 px clip and claim added detail, automatically rescrape the library, or duplicate thousands of clips per display mode. Estimate storage from a representative sample before changing the preparation policy.

The pinned VLC stop/release remains a risk when changing inserted games. Newer [Knulli source](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/components/VideoVlcComponent.cpp) contains an asynchronous release approach. Review its context lifetime and backport compatibility rather than copying a thread around the old call. If decoder churn breaks input targets, resolving that is part of the frontend feasibility work.

## 9. Work packages and stop/go gates

| Order | Work package | Concrete deliverable | Gate before broad rollout |
|---|---|---|---|
| 0 | Reconfirm environment and protect test state | Firmware/binary/resource versions, clean baseline captures, existing user-work inventory, snapshot/restore audit | A matching frontend build/install route and recoverable device test setup exist |
| 1 | Correct browse-stage model presentation | GBA, PSP and one home console comparison at 720×480, then all existing families/variants; matching entry endpoints | Hardware is immediately recognizable; labels/status fit; no model jump when inserting |
| 2 | Prove independent state and input | Opt-in frontend slice using a simple console and still display; Down/Up, browsing while inserted, auto-swap Play | 50 mixed command cycles: no launch on Up/Down, one launch per Confirm, no cursor/inserted identity drift, no leaked held input |
| 3 | Prove the screen and renderer path | One home-console CRT plus GBA front/reading pose; timed sprite/mesh comparison | Text is readable at native size; masks/occlusion/endpoints work; choose one rendering path within memory/frame budgets |
| 4 | Add media lifecycle and hooks | One-decoder preview, stable inserted binding, DS split prototype, matched launch token and return-to-inserted path | Browse another game without resetting the playing TV clip; no duplicate insert, covered launch, save/stat side effects or return-input regression |
| 5 | Add information pages and fallback quality | Overview/details/gallery/library pages with real local mixed-completeness examples | Long titles, descriptions, missing art and sparse metadata remain useful without tiny text or fabricated fields |
| 6 | Add motion language | Selected idle, mechanical beats, screen activation, coherent swap/eject, reduced motion and sound | Sparse idle feels alive without obscuring art; commands still acknowledge promptly; no extra decoder or continuous decorative redraw |
| 7 | Roll out platform families | Top-loader → front-loader/PS1 → GBA → DS/PSP → GB/GBC native LCDs → remaining variants/Pico-8 | Family-specific loading, screen mapping, region ownership and missing-art cases pass on the device |
| 8 | Package and document | Capability-aware theme, reproducible patch/build manifest, install/rollback, supported-version matrix, test evidence | Stock fallback works; upgrade/uninstall clears owned runtime state; no stale hooks or overlays |

The ordering is deliberately evidence-driven. Model framing can ship independently. State/input and one readable CRT/LCD must work before expanding every scene. Do not promise the full experience as a small XML tweak. Do not mix unrelated scraper completion or a complete hardware-accuracy rebuild into the first interaction prototype.

### Expected files and ownership

| Area | Likely change |
|---|---|
| `tools/themebuild/consoles.py`, `tools/consolebuild/models.py` | Browse-stage renders, camera/screen landmarks, loaded/empty poses and region/model outputs |
| `tools/themebuild/shelves.py`, `_slot/shelf-common.xml` | Two compositions, grouped selected motion, inserted shelf marker, action hints and capability fallback |
| `tools/themebuild/video.py`, `_slot/shaders/` | Separate screen surfaces/source layouts, perspective-safe video/text composition and decoder ownership integration |
| New small scene/profile data beside current console/shape specs | Versioned endpoint, screen quad, occluder and motion information; reuse existing region/media identity rather than parallel hand-written registries |
| Knulli frontend source, maintained as a pinned patch/build recipe in this repository | Slot state, scoped input, independent inserted bindings, presentation component, launch and ready integration; exact patch packaging decided in package 0 |
| `_slot/launch/`, `tools/slotlaunch/` | Matched launch/return contract and compatibility fallback; avoid adding an always-running input watcher |
| Focused tests and `tools/dev/` probes | State transitions, generated geometry contracts, real input/frame timing and recovery evidence |

The existing working tree contains unrelated uncommitted scraper/video work. Preserve it; do not overwrite regenerated files or deploy the whole dirty tree as part of this plan.

## 10. Validation that actually establishes the experience

Use meaningful state tests and device evidence, not tests that merely assert XML contains a new element.

1. **Independent selection:** insert A, browse B/C, verify A's title/art/preview/page/console stay stable; press Up while B is highlighted and verify A returns to its position; press Down on B and verify a real swap; Confirm B launches B once.
2. **Identity and input:** held Down/Up, diagonal hats, analog dead zones, rapid reversal, commands during each mechanical phase, controller unplug/reconnect, mapped buttons, short/long Confirm and multiple identical names/subfolders. An inserted marker stays navigable and does not duplicate physical media.
3. **Launch integrity:** normal BIOS/options/netplay/save-state dialogs; cancel and missing-ROM failure; no change to play count/time/last-played or save/config/state files after inspection-only cycles. Real launches retain normal frontend updates. Confirm once creates one launcher process and one scene transition.
4. **Lifetime:** filter/search hides inserted A; delete/reload its entry; leave a system; open/close modal menus; theme switch; sleep/resume; screensaver entry/exit; game exit, failed launch and immediate replay. No stuck overlay, wrong title or stale pointer.
5. **Physical mechanisms:** NES door/tray; SNES regions; MD variants; DS orientation/latch; SP loading then front display; PSP full UMD behind closed cover; PS1 bore/rims/spindle and opaque lid. Review empty/loading/loaded at native panel size.
6. **Media:** missing/broken image/video; long/Unicode titles and descriptions; same video shared across games; 4:3, 3:2, wide, portrait, stacked DS and non-square-pixel fixtures. Circle/grid fixtures establish aspect ratio; covers retain printed edges. Unknown layouts fail visibly and safely to useful stills.
7. **Performance:** identical navigation traces with empty, inserted-still, inserted-video, reading page and idle; cold/warm caches; capture on/off; p50/p95 input acknowledgment, p95/p99/max frame intervals, RAM/decoder count, return readiness and heat/battery observations. Average fps alone cannot establish smoothness.
8. **Fallback/recovery:** missing feature capability, incompatible binary/resources, missing mesh/pose, texture allocation failure and interrupted transition. Return to a usable stock shelf; keep a known-good install and reversible package.

Acceptance requires: no emulator launch from Up/Down; responsive browsing around a stable inserted game; truthful, readable display content; recognizable current console models; additional motion with no new routine stutter; correct launch and return; and documented platform limits.

## 11. Critical decisions and remaining uncertainty

- **Settled:** independent browsing and inserted identities; Left/Right leaves the current cartridge seated; Confirm targets Highlighted and swaps before launching; GB/GBC use their own LCDs with a reading zoom.
- **Recommended:** frontend-native ownership; visible current models; one decoder; local data; paged information with screen zoom; return to the inserted presentation.
- **Must prove:** matching build/installation path; scope of frontend patch; sprite layers versus integrated GLES; projected text readability; DS shared texture; video-swap latency; launch/return coordination and resource headroom.
- **Before final control mapping:** verify shoulder/page/system mappings so metadata navigation does not displace existing functions.

The first implementation milestone should be intentionally small and reviewable: **one recognizable console, independent Down/Up, a stable inserted-game still display, continued browsing, and exactly-once Confirm with swap.** That demonstration settles the expensive architectural uncertainty before richer art, every platform and idle polish are built on top of it.
