# Slotted: plan for a standalone 3D theme

20 October 2026. **Accepted direction, with a later one-room clarification.**
The original decisions are recorded in §10; the user's latest correction and
answers are in **§11 and take precedence wherever the earlier plan conflicts**.
Four-direction navigation replaces the earlier Up/Down selector switch. All
24 design answers are recorded in §11. **Implementation is in progress; verified
phase status is in TABLETOP_HANDOFF.md.** Read
`AGENTS.md`, then `docs/TABLETOP_HANDOFF.md`, before starting. Record progress in
the handoff, following AGENTS rule 5, and keep this plan current when a decision
changes.

Resume checkpoint: Phase 0 spikes and Phase 1 mixed room/home/console batch plus
forced rollback are device-tested. The persistent room, TV host, input/session
ownership and editor are implemented, with host and bounded hardware checks.
Slotted is not permanently installed. Full variant regression, performance,
packaging and user acceptance gates remain open; exact evidence and limits are
in TABLETOP_HANDOFF.md. See SLOTTED_PHASE0_RESULTS.md for measured
memory/frame time and the choice of raster **B (640×480)** for TV hosting.

The Phase 2 full-screen views are intermediate implementation/test artifacts,
not the intended Slotted browsing experience. Do not continue the former phase
sequence without applying the revised requirements and answers in §11.

The work starts from the current overlay sources: the n22 candidate `02547f89…`,
whose files are listed in `owned-source.json`. Whether n22 gets installed is a
separate open decision, and this plan doesn't change it.

---

## 1. What you asked for

1. **Its own theme, called "Slotted".** No runtime dependency on Art Book Next.
2. **A home table for system selection.** Every modelled console sits on one
   table, the same way the cartridges do. This covers the consoles and the
   "All games / Favourites / Last played" style entries. When you select a
   console, the others fly off the screen, and the table, TV, console and
   cartridges move into that console's saved layout.
3. **Lists and every menu on the TV.** Collections, systems without a model,
   Ports, MPV and the main menu with all its submenus use the TV glass. The
   whole front of the TV and its system/status UI on top remain visible.
4. **The editor can edit the home table, TV screen and room.** Room editing
   adds the table positions and travel paths without replacing console layouts.
5. **Batch upload.** The editor can upload several layouts at once. Today each
   upload sends one console/TV layout.
6. **A better TV interface.** It should look much more retro.

## 2. Baseline when this plan was accepted (historical)

| Fact | Where | Consequence |
|---|---|---|
| `art-book-slot/theme.xml` includes Art Book Next's `theme.xml` and points `${themePath}` at it. Art Book Next draws every screen except the shelves. | `theme/art-book-slot/theme.xml` | Slotted needs its own system view, gamelist views, menus styling, fonts, system art and help prompts. |
| The frontend hard-codes `/userdata/themes/art-book-slot/_slot/`. The launch guard and `/tmp/art-book-slot-launch` use the same name. | `SlotPresentation.cpp:26`, `SlotLaunchGuard.h` | It needs a theme-root resolver, with the old path kept as a fallback. |
| About 90 tool files name `art-book-slot`. These include the editor upload's `ThemeSet` check, `DEVICE_LAYOUTS`, `deploy_set`, `package`, `esdev` and `session_data`. | `tools/**` | Use one shared theme-name/theme-dir constant, then migrate the files in stages. |
| The 3D table only exists inside `CarouselGameListView` (`SlotPresentation`). The system view is Art Book Next's carousel, and collections are Art Book Next lists. | `tools/frontend/apply.py` | The system view needs a new host. `ViewController` hand-offs need to cover system view ↔ room and system view ↔ TV. |
| One persistent native session already handles room-to-room switches without black frames. It does the wave lift and flight, the table slide, TV swaps, the hold-until-ready, and the mesh warm-up. | `SlotTabletopStream.inc`, `SlotSystemFlight.h` (n17 to n21) | "Others fly off, then everything moves into the saved layout" can reuse this machinery. It doesn't need a new animation system. |
| TV metadata is already drawn with ES components (`TextComponent`, `ImageComponent`, VLC) into a 720×480 FBO, then textured onto the TV glass. | `SlotPresentation::screenTabletop` | A small version of "2D UI on the TV" already works. The new step is to send ES's whole view and menu stack into that FBO. |
| The `SLOTLAYOUT1` format has fixed node names. The parser **rejects unknown records**. | `SlotSceneProfile.h` | New scene types get their own files and headers, so older binaries never misread them. |
| Each editor upload is one profile, with its own snapshot, audit and frontend restart. | `editor/upload.py`, `device_upload.py` | Batch upload should be **one** transaction for N layouts, not N transactions in a row. |
| The device has 2 GB RAM. The PVM textures alone are about 341 MiB with mips, and the wooden table about 85 MiB. The optional-resource soft cap is 768 MiB, and the stream keeps at most 3 hardware bundles. | `SYSTEM_SWITCH_RESEARCH_20261020.md` | Eleven consoles on one table is the main **memory and performance risk**. It has to be measured first. |
| The tabletop supports 11 consoles: SNES, N64, NES, MD, PSX, GB, GBC, GBA, NDS, PSP and PICO-8. Dreamcast exists only as a legacy shelf. | `editor/server.py` `SYSTEMS` | Dreamcast and other unmodelled systems become TV "channels" unless a model is added later. |

## 3. Target experience

### 3.1 Home table (system selection)

- The **TV** and the **status** sit on one table, together with every console
  that has games on the device. Their poses come from an authored **home
  layout**. Missing systems leave their spot empty. Nothing is reframed
  automatically, and the authored camera is never rewritten.
- **Four-direction spatial selection** (latest answers, §11): all four D-pad
  directions move among physical consoles and cartridges. Up/Down no longer
  switch between table and TV focus or insert/eject a game. The TV is a
  selectable object: A enters its controls and B returns to physical
  selection. Do not reintroduce a conflicting directional mode shortcut.
- **TV channels are a vertical list.** Up/Down chooses a channel once the TV
  owns focus. Channels cover collections and systems/categories without a
  physical console model. A modelled system has no duplicate system channel,
  but collections can contain its games. Remember table, channel and content
  selections independently and retain ES's filtering, ordering and identities.
- **Console selector:** the highlighted console lifts and idles, using the same
  spring and hover as the cartridges. The TV shows that system's card: name,
  game count, last played and a random preview.
- **TV focus:** the camera uses a TV UI view showing the whole front of the TV
  and its system/status UI resting on top. The glass shows the vertical channel
  list at home. A opens the selected channel's list; B returns to channels,
  then B returns to the table. Console-layout TVs show metadata and menus,
  not channels. A channel card is no longer the selector.
- The camera options are the authored overview, plus an optional gentle follow
  of the highlighted console. The follow camera is stored relative to the
  console, the same way the cartridge camera is stored relative to cart 1.
- Startup opens the **home table**, remembering the selected console or channel.
  It does not resume the last console layout/list or inherit another ES start
  entry as the Slotted destination.

### 3.2 Selecting a console (A)

Reuse the existing wave/flight machinery where it fits the persistent world;
the old table-slide substitution is not the target:

1. On the input frame, the **other consoles lift in waves**. The wave order is
   by distance from the selected console. They hold while the room is prepared,
   then fly off the screen with the existing stagger.
2. At the same time, the **selected console rises slightly and glides** along an
   arc, from its home pose to its pose in the saved room layout. The arc keeps
   it clear of the others.
3. **One room position per table model.** If the destination uses the same
   table model, rearrange the hardware on that table. If it uses another table
   model, travel through the room to that table's fixed position. The departing
   and arriving tables may both be visible briefly during travel. Keep a table
   visible and room rendering continuous; do not slide replacement furniture
   through the same location. **The camera follows the selected console as it
   flies to the destination and lands.** A TV change happens at the current table, with
   glass and status kept rigidly attached to their cabinet.
4. The **cartridges arrive in waves** and land in the room's everything view.
   Then the camera pans to the saved browse view, limited to 0.5 s as now.
5. The flight is responsive: motion starts on the input frame, and a request
   for another destination takes over from the current one. GPU uploads only
   happen during still holds. Meshes are warmed before release.

### 3.3 Cartridge actions and Back (B)

- **A on a loose/highlighted game inserts it**, swapping out an already loaded
  different game. A separate subsequent A press on the loaded game launches
  through the ordinary validated, exactly-once path. Holding A never launches.
- **B while a game is slotted ejects it.** The former Up/Down insert/eject
  aliases are removed from the target four-direction browsing controls.
- A console **keeps its inserted game across navigation and gameplay return**
  until the user explicitly ejects/replaces it. Moving to home, a TV collection
  or another system must not clear that state. Separate logical ownership from
  view teardown and the native graphics shutdown used for emulator execution.
- Leaving a console layout returns to the **original home table and remembered
  console selection**: cartridges depart and the other consoles return. Eject
  takes precedence over leaving while in cartridge browsing. TV/menu Back uses
  its content hierarchy, then returns to table selection without another action
  from the same held press.
- If the console layout was opened by a collection, leaving returns to that
  collection with the same selected game, rather than losing that context at home.
- At a cartridge-window edge, directional movement brings more games into view.
  L2/R2 retain system switching. R3 cycles the authored camera views; it no longer
  opens a full-screen carousel. L3 inspection remains a temporary object mode.

### 3.4 TV lists: zoom into the TV

- Opening TV content uses an authored TV UI camera that retains **the whole
  front of the TV and the system/status UI resting on top**, in 3:2 and 4:3.
  Existing saved cameras are not automatically reframed to implement this;
  expose the required UI view separately for authoring. Content appears on the
  registered glass while the room stays visible.
- The ES view runs normally (input, sorting, filters, search, options and
  launch). Only its pixels go into the TV texture. The 3D room is static during
  this, so the existing scene cache reuses the room render. Only the glass
  is redrawn.
- A collection can contain games from any system. Selecting a game whose
  system has a model **opens that console's saved layout with the game
  highlighted**. It does not insert or launch it automatically; the user's
  separate A-to-insert, A-again-to-launch controls apply.
- Games without a console model and launchable Ports/MPV entries retain normal
  validation and exactly-once launch ownership. Games and external apps run
  **full-screen after launch**; actual gameplay/app execution need not stay
  inside the room's TV. The room requirement covers frontend browsing.
- Channel static/launch choreography must not become a full-screen loading
  view or interrupt room rendering. The old direct collection launch and
  black-screen-fill sequence are not assumed to answer the revised route.

### 3.5 Menus

**Every 2D menu renders on the TV** (user decision 3): the main menu, game
options and settings, opened from the home table, a TV list or a console room.
Opening one from a console layout pans to the TV UI view and shows the menu on
the glass. Closing it returns to the prior context. The whole TV front and its
system/status UI remain visible. This covers the main menu and **all** submenus,
including dialogs, search and options; no ordinary full-screen overlay takes
over frontend browsing.

### 3.6 Continuity and recovery

The normal Slotted path never replaces the room with a full-screen 2D fallback.
Keep the last working table live while preparing a destination; a failed
request must not discard that scene. Present recovery information within the
room where possible. Detailed cold-start/error behavior remains to be designed.
The retained legacy theme and transactional device rollback remain available
outside this browsing experience; the tested Phase 2 full-screen views are
intermediate artifacts, not an accepted runtime escape from the room.

## 4. Architecture

The control summary below is the target; it is not a claim that the current
frontend has been wired to it. Its older installed controls remain historical.

| Context/action | Target result |
|---|---|
| D-pad on the table | Spatial selection in four directions among visible consoles/cartridges and the TV |
| D-pad past a cartridge-window edge | Reveal further games in the sorted/filtered library; no directional insertion/ejection |
| A on a home console | Other consoles fly off; present that console's saved layout at its table model's room position |
| A on a loose/different game | Insert/swap; a separate A on the loaded game launches normally |
| B in cartridge browsing | Eject a loaded game first; a later Back leaves for home or the originating collection/game |
| A on the selected TV / B in its controls | Enter TV control / back through TV content, then return to physical selection |
| Up/Down on home TV channels, then A | Choose a channel from the vertical list, then open its game/content list |
| A on a collection game with a model | Open its saved console layout with that game selected, ready for separate insert/launch actions |
| R3 | Cycle authored camera views; no full-screen carousel |
| L2/R2 | Keep switching systems |
| L1/R1 and L3 | Retain metadata pages and temporary cartridge inspection; inspection directions turn the object |
| Start / menu navigation | Open the main menu on the current TV; all submenus/dialogs stay there |
| Random | Separate Shuffle and Open actions; modelled games use the cartridge route |

### 4.1 Theme package

- **Source location** (user decision 1): `Slot_ESDE/theme/slotted/`, next to
  the tools, editor, tests and device scripts. Packaged release builds go to
  `C:\Programmering\SBC\ESDE_Themes\Slotted`. Nothing there is ever edited by
  hand.
- **Name on the device:** the folder is `slotted`, with the display name
  "Slotted". Check whether this ES build shows the folder name in Theme Set. If
  it does, name the device folder `Slotted`.
- **Contents:**
  - `theme.xml` with **no Art Book Next include**
  - `_slot/`: the current runtime assets, moved as-is with their hashes
    recorded
  - `_tv/`: fonts, palettes, icons, noise and CRT textures for the 2D UI
  - `views/`: system, gamelist and menu XML
  - generated per-system folders, from `tools/themebuild --theme slotted`
- **Theme options carried over:** console model style, console colour, TV
  model, SNES cartridge model, GBA SP model, cartridge video and wallpaper. A
  one-time migration copies `art-book-slot.cfg` to `slotted.cfg`. The legacy
  per-system 2D shelf options and the `slot-interaction` subset are removed.
  Slotted always uses the 3D table where it is supported.
- **Assets that must be replaced** (audited in Phase 1): every Art Book Next
  font, logo, colour, icon and help glyph referenced through `${themePath}`.
  System art becomes our own: pixel-font wordmarks plus channel cards rendered
  from our licensed console models. No third-party logo packs are used.
- **Licences:** dropping Art Book Next removes its CC BY-NC-SA runtime
  dependency. The existing non-commercial assets stay listed in the credits
  (the Retro TV and Qu3st10n's TV stand).
- **Side-by-side install:** `art-book-slot` stays installed on the device until
  you accept Slotted. That keeps a known-good theme, and a rollback is just
  switching the theme back.

### 4.2 Frontend (overlay components; `apply.py` stays a thin patch)

- **`SlotThemeRoot`:** resolves the `_slot/` and `_tv/` roots from the active
  theme folder, falling back to `art-book-slot`. This replaces the hard-coded
  paths in `SlotPresentation` and `SlotLaunchGuard`. The launch-guard tmp names
  stay compatible.
- **`SlotHome`** (new): the system-view host. When the active theme opts in,
  it attaches to the **same persistent tabletop session** and renders the home
  table instead of the carousel. It maps ES's `SystemData` list (including
  collections) to console nodes and channels. It owns only the
  console/channel selector state and the remembered position of each selector.
  Physical moves use all four directions and synchronize the focused console
  with ES's system identity. TV channels use vertical list navigation. Keep
  ES's filtering, sorting and hidden-system behavior. The mechanism for moving
  between physical selection and TV focus is a selected TV plus A/B. Channels
  are home-only; console TVs retain metadata and menus.
- **Persistent world ownership** (new, implementation design): one room-level
  owner keeps a fixed anchor for each table model and one active layout per
  table. Apply one common rigid world transform to a profile's objects and
  camera eye/target so its saved table pose maps onto that table's anchor.
  Preserve internal object relationships, authored FOV, geometry, materials and
  labels; do not rewrite source profiles. Normal views render one table;
  cross-table travel can render the departing and arriving tables together.
  Retain the current live layout until destination resources are ready, with
  bounded residency and explicit culling rather than a room teardown.
  This owner also keeps inserted-game identities per console, independent of
  a gamelist's show/hide lifecycle. Native GL shutdown before real launch frees
  rendering resources without forgetting which games remain inserted.
- **Stream extensions** (`SlotTabletopStream.inc`, `SlotSystemFlight.h`): a
  third room kind, "home", next to the console rooms. It adds the home ↔ room
  transition (many-console departure, a selected-console glide along an arc
  instead of a fly-out, and the reverse) and the home ↔ TV-zoom camera move.
  Reuse warm-up, upload gating, newest-request retargeting and rigid hardware
  flights as appropriate. Replace the table-slide substitution with world-space
  travel between fixed table anchors. The existing home renderer/stream
  prototype does not yet establish this behavior.
- **`SlotTvHost`** (new): while a TV-hosted view is shown, `Window::render`
  draws the ViewController view and the GUI stack into the TV FBO instead of
  the screen. The persistent room renderer then draws the scene with that texture
  on the glass; static layers may be cached without stopping room updates.
  The texture is only redrawn when ES content changes or a video frame arrives.
  ES's own slide/fade transitions between views are disabled while hosting.
- **`ViewController` hand-offs:** the patch extends to cover system view ↔
  room, system view ↔ TV list, and room → menu-on-TV, as well as the existing
  room ↔ room. Real game launches keep `shutdownTabletop()` before the emulator
  starts.
- **One video decoder.** A TV list's preview (its picture-in-picture box) and a
  room's metadata video never run at the same time.

### 4.3 Scene files (new, separate from `SLOTLAYOUT1`)

| File (authored → runtime) | Header | Contents |
|---|---|---|
| `scene-layouts/home-<tv>.json` → `_slot/tabletop/layouts/home-<tv>.scene` | `SLOTHOME1` | table asset and scale; TV and status poses; one `console <system> <variant> <pose>` line per console; cameras `overview`, `screen` (TV zoom) and optional `follow`; hover and transition times |
| `scene-layouts/screen-<tv>.json` → `.../screen-<tv>.screen` | `SLOTSCREEN1` | TV UI skin, palette, text scale, safe-area padding, CRT effect strengths, power-on and static timings |
| Separate durable world JSON → separate runtime world file (format not implemented) | New header, to be defined | One anchor per table model, editable travel paths, suggested spacing and the original home-table identity; no duplication of authored console profiles |

Console layouts keep `SLOTLAYOUT1` unchanged until an explicit format migration
is implemented and tested. A separate TV UI camera must frame the whole TV front
and top status UI. Adding that record to console profiles requires a version
bump or compatible separate data; the parser rejects unknown records. Do not
silently change an existing TV camera or treat its current framing as accepted.

### 4.4 Memory and frame time for eleven consoles

- **Measure first (Phase 0):** total triangles, texture bytes with mips, draw
  calls, and the frame time of a static home table with all 11 consoles, the TV
  and the table on the device. Use `texture_inventory.py` and a probe scene.
- **Approach with no quality loss:** in the home overview each console covers
  a small part of the screen, so the sampler only reads small mip levels.
  Upload only the levels that the home cameras can sample. The renderer already
  owns its mip chains. Stream the full levels when that console is selected,
  during the still hold. This has to be proven **pixel-identical** against a
  full-residency render. The table and TV stay fully resident.
- **Rendering:** consoles that are standing still go into the cached scene
  layer. Only the moving, highlighted console is re-rendered each frame. Its
  depth test against the cache needs a check: cache the depth buffer, or
  re-render with depth only.
- **Trade-offs only with your choice.** If it still doesn't fit, I'll list
  options with measured costs, for example console LODs in the home view only,
  or fewer consoles visible at once. No trade-off is applied silently, per
  AGENTS rule 2 and the frame-rate notes.

## 5. Editor

### 5.1 Scene picker

A new **Scene** selector in the header: **Console layout** (today's editor),
**Home table**, **TV screen** and **Room**. Undo/redo, browser drafts, history and
checkpoints work per scene file. They stay separate from existing console drafts.
The Room scene edits one position per table model and travel paths, with suggested
spacing. It references saved layouts and never replaces their authored coordinates.

### 5.2 Home table

- All 11 consoles load as their real models, using the current style and paint
  settings, with a variant picker for SNES PAL/US and MD/MD-JP. The TV, status
  and table use the existing tools: move, rotate, multi-select, swap pair, rest
  on table, and table model and size.
- Preview all four navigation directions among the authored consoles and
  cartridges, plus vertical TV channel selection. Physical movement follows
  the new spatial navigation design rather than the old ES-order-only strip.
  ES order remains the source order for channel lists and game windows. TV focus
  entry uses A on the TV; cartridge-window edges reveal further games. L2/R2
  retain system switching. The editor preview must exercise these same rules.
- Cameras: overview, TV screen zoom, and the optional follow-highlight camera,
  each with the existing numeric, orbit and pan controls and pan times. There
  is also a **"Preview select"** button. It plays the fly-off and room-landing
  sequence in the browser, using the saved room layout of the chosen console.
- A starter layout is generated once from the room layouts (consoles in a row
  behind the TV, for example). It is only a draft until you save it, and it
  never overwrites a saved file.

### 5.3 TV screen

- Pick the TV (Panasonic, PVM, Old TV or Retro). The TV UI camera has editable
  position, target and FOV, with guides showing the whole front and the system
  UI resting on top in both 3:2 and 4:3. Preserve existing saved cameras; author
  the separate UI view rather than automatically reframing another view.
- The glass shows a live preview of a sample list. It uses a canvas rendering
  of the real 2D layout and fonts, plus a WebGL copy of the device's CRT shader.
  The GLSL source is shared, so the editor and the device match. A **"Capture
  from device"** button fetches the real TV FBO frame through a debug dump, to
  compare exactly.
- Controls: skin, colours, text scale, safe-area padding, scanline, mask, bloom
  and vignette strength, power-on and static durations. The current room
  **Display metadata** settings move into this shared look, and each room can
  still override them.

### 5.4 Batch upload (independent; can ship first)

- **Upload…** opens a list of every saved layout: console, home, screen and world. Each
  row shows **Same as device / Changed / Not on device**, from one SSH hash
  read. Changed rows are ticked by default. You also pick what to open
  afterwards: the home table, a chosen room, or normal startup.
- One device transaction covers all of them: one fresh snapshot, one combined
  dependency manifest (each changed runtime model is sent once), one tar, one
  frontend restart, verification of every file, and one audit. If anything
  fails, every file rolls back together. Progress is reported per file.
- "Save for all TV consoles / all handheld consoles" gains a **"…and upload"**
  option. **"Import all from device"** lists device layouts that differ from
  the saved ones, and imports them as undoable drafts. Nothing is written on
  the device.
- Tests: extend `tests/test_editor_upload.py` with multi-profile dedupe,
  unchanged-file skips, partial failure leading to a full rollback, and the
  lock against concurrent uploads. Keep the existing 36 editor, persistence and
  scene-editor tests passing.

## 6. Retro TV interface

The goal is that it reads like a real 1990s TV picture, not a phone UI drawn on
glass, and that it is still easy to read at 720×480 after the zoom.

- **Raster:** a 4:3 picture with square pixels and a title-safe margin, on an
  8 px grid. Phase 0 chooses between two options. Option A renders 720×480 and
  maps only the central 640×480 onto the glass, so the theme keeps everything
  inside that area. Option B gives ES a temporary 640×480 screen size for the
  TV pass. Menus, clip rects and help prompts all need checking for either one.
- **Type:** Raster Forge (CC0, already shipped) for headings and on-screen
  labels. Body text uses a readable pixel font with a permissive licence, for
  example Pixel Operator (CC0), sized so it projects to at least 18 px on screen
  after the zoom. Final text size is measured on the device, not assumed.
- **Skins**: one per TV (user decision 4). The TV screen editor can change
  each TV's skin and colours.
  - Panasonic: **blue on-screen menus** (deep blue field, white and yellow
    text, bar-graph page indicator, "AV1" source tag)
  - PVM: **broadcast monitor** (black field, green and amber text, underscan
    frame, timecode-style clock, colour-bar accents)
  - Old TV and Retro: **teletext** (8-colour palette, block-mosaic headers,
    page numbers such as "P100")
- **Game list as a TV guide:** a channel and title column, the selected game's
  preview in a picture-in-picture box, a teletext-style description panel with
  a slow scroll, and a top bar with the channel name, clock and battery. The
  help bar uses remote-control style button glyphs.
- **The console-room metadata pages get the same restyle.** Overview, details,
  gallery and library keep their L1/R1 pages and field toggles.
- **CRT effects on the glass:** one GLES2 pass, drawn only on the glass mesh:
  - scanlines aligned to the picture rows, weighted by brightness
  - a subtle mask: aperture grille for Trinitron/PVM, slot mask for Panasonic
  - a light bloom from a small blurred copy (the target must be a power of
    two, because GLES2 limits mipmaps on other sizes)
  - a vignette and a slight colour fringe
  - curvature from the real curved glass mesh

  Text readability limits how strong the effects can be.
- **Motion:** TV-only power-on/static/OSD effects may accompany TV content,
  with reduced-motion support. They never replace the surrounding room with
  a loading image. A modelled game chosen from a collection first opens its
  console layout; launch follows the separate insert/launch actions. The old
  direct launch zoom in §10 is superseded where it conflicts with that route.

## 7. Phases and gates

Phases 0–2 retain their historical scope and evidence. **Phases 3–5 below are
revised after the persistent-room/four-direction answers.** Intermediate 2D
views and native probes are not the final browsing experience.

Each phase ends with the handoff updated, following AGENTS rule 5: changed
files, commands run, the device state, and which steps are prototype,
host-tested, device-tested or installed. Device changes go through the existing
snapshot, restore and audit transactions. Nothing is installed without your OK.

| # | Phase | Delivers | Gate |
|---|---|---|---|
| 0 | **Audit and spikes** | Art Book Next dependency audit; inventory for all 11 consoles (triangles, texture bytes, draws); **spike A**: an ES gamelist view rendered into the TV FBO in a host probe and then on the device; **spike B**: a static all-console table frame on the device | Measured memory and frame time for the home table; a working FBO capture of a real ES view; raster option A or B chosen |
| 1 | **Batch upload** (independent) | §5.4 | Two or more layouts uploaded in one transaction on the device; a forced failure rolls everything back; clean audit |
| 2 | **Slotted theme split** | A single theme-name constant in the tools; `SlotThemeRoot`; own 2D views (first version) **full-screen**; settings migration; side-by-side install | With Art Book Next removed from the device test path, every view still works; console rooms are pixel-identical to n21/n22; validated launch increments the play count exactly once |
| 3 | **Persistent room and spatial table browsing** | World ownership and one fixed position per table model; home scene/editor; editable room positions/paths; four-direction console/cartridge selection; A insert/launch and B eject; home ↔ saved layout choreography | Authored home and unchanged console profiles; exact transformed camera landing; current table live throughout preparation; same-table rearrangement and two-table travel; measured transition peak memory/frame time; 30 rapid retargets; native and GUI controls/launch trials |
| 4 | **TV interface throughout the room** | `SlotTvHost`; vertical channel list; collections/unmodelled systems, Ports and MPV browsing; main menu and every submenu/dialog; whole-TV/status framing; per-TV retro skins, glass CRT shader and TV-screen editor | Real device inputs/search/filter/options/dialogs work on the TV; modelled collection games open their cartridge layout; full front/status visible in 3:2 and 4:3; readable native-size captures; editor/device preview match; one decoder; no full-screen fallback or blank frame |
| 5 | **End-to-end integration** | Resolved TV focus/paging/R3/Random controls; origin-aware return per user answer; home/world/screen batch upload/import; startup and reduced motion; interruption and recovery within the live room | All new scene types round-trip with drafts/undo/history preserved; atomic multi-type upload and forced rollback; all navigation origins and launch/return paths tested; uninterrupted room rendering; no action from a held A/B is dispatched twice |
| 6 | **Finish and package** | Performance pass; startup into home or a collection; reduced motion; packaging of only owned files; README and credits; decide whether to retire `art-book-slot` | Full regression on every system, TV and table variant; your acceptance on the device |

Phase 3 uses Phase 0's measurements and the standalone Phase 2 candidate.
Phase 4 builds on that persistent room and the measured 640×480 TV FBO path.
Phase 5 closes cross-feature/editor/device integration; Phase 6 remains the
full performance/regression/acceptance gate. Follow the accepted focus/paging
rules from §11 when implementing their dependent input and editor behavior.

## 8. What "working" means (acceptance)

- **Theme:** Slotted alone, with no Art Book Next present, covers the system
  view, every gamelist, collections, menus, help, splash, screensaver and theme
  options.
- **Persistent room:** one world position per table model; ordinary browsing
  shows the current table and travel may briefly show both endpoints. No
  loading screen, room teardown or full-screen UI substitution. Same-table
  layouts rearrange in place. Full source detail and authored cameras survive
  the common world transform; camera error 0; GL errors 0.
- **Home and cartridge selection:** every console with games is placed as
  authored; all four directions browse physical objects spatially, with no
  directional insert/eject alias. A inserts/swaps; a separate A launches;
  B ejects a loaded game before leaving cartridge browsing. Held A/B dispatch
  at most one action per press. Select/back, rapid retargeting and preparation
  holds stay responsive; remembered selections are restored.
- **TV content:** vertical channel selection and the resolved focus/list rules
  work; no duplicate channel for a modelled system; collections may include any
  system. A modelled collection game opens the saved cartridge layout with that
  game highlighted and no automatic insertion. Whole TV front and top status
  UI remain visible. Ports, MPV, all main-menu submenus, search, filters, options
  and dialogs stay inside the TV. Text is readable at device resolution.
- **Launch:** ordinary validation and exactly-once ownership are retained;
  cancellation preserves browsing context. Only after launch do games/external
  apps run full-screen. Room continuity is verified through frontend browsing
  and launch preparation; external execution is a separate scope.
- **Editor:** home, TV-screen and world scenes round-trip (save, reload, upload,
  import) alongside existing console layouts; undo/redo, drafts and history
  are kept; batch upload is atomic across the supported scene types.
- **Performance:** the existing targets apply (p95 under 33.3 ms when settled,
  no new stall over 50 ms, memory under the 768 MiB soft cap plus the reserve),
  reported against n21/n22 with the existing timing tools.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Eleven full-quality consoles exceed memory or frame time | Measure in Phase 0; mip-limited residency proven pixel-identical; cached static layer; any quality trade-off only with your choice |
| ES GUIs assume they draw straight to the screen (clip rects and scissor flips, help prompts, transitions) | Use the device-proven 640×480 FBO path; test the full GUI stack in the live room; retain the current scene on a failed request |
| Two-table travel raises peak residency/frame time | Share unchanged assets, bound current/destination residency, measure transitions and cull other tables; no silent asset-quality reduction |
| Spatial focus becomes unstable as models hover or the camera pans | Derive neighbors from stable layout anchors, preserve object identity and test authored irregular layouts and camera transitions |
| The frontend patch keeps growing | New logic goes into separate overlay components; `apply.py` only adds hooks |
| Renaming breaks device tools, hooks or recovery | One constant; side-by-side install; legacy path fallback; old binaries and records kept |
| An older binary reads new scene files | New headers and file names; `SLOTLAYOUT1` stays unchanged |
| The 2D UI loses features Art Book Next had | The Phase 2 audit lists every Art Book Next feature in use before anything is removed |

## 10. Original decisions (20 October; later changes in §11 take precedence)

1. **Source location:** `Slot_ESDE/theme/slotted/`. Packaged builds go to
   `C:\Programmering\SBC\ESDE_Themes\Slotted`.
2. **Collections on the home table:** TV channels. When one is highlighted,
   the TV shows a channel card. There are no physical props for collections.
   **Updated:** §11 replaces channel cards with a vertical channel list.
3. **Menus:** every menu renders on the TV, including menus opened from a
   console room.
4. **TV look:** one skin per TV: Panasonic blue on-screen menus, PVM broadcast
   monitor, Old/Retro TV teletext.
5. **Launching from a TV list:** the TV picture turns black and the camera
   zooms into it, then the game launches (§3.4). Flying the matching console in
   to slot the game first may come later; it is not part of this plan.
   **Updated:** §11 now requires opening the saved cartridge layout first for
   a modelled game, with separate A insert/launch actions.
6. **Home table navigation:** Left/Right in ES's normal system order. Up/Down
   switches between the TV channel selector and the console selector (§3.1).
   **Superseded:** §11 uses all four directions for spatial physical selection
   and Up/Down for the focused TV channel list; select the TV and A to enter.

## 11. Latest user clarification: one persistent room (20 October)

This section records the correction and the user's answers after the
recovery/device-test checkpoint. It supersedes conflicting older decisions,
especially Up/Down mode switching, table substitution, channel cards,
full-screen 2D fallback and direct launching of modelled collection games.

### Fixed room requirement

All frontend browsing happens in one continuously rendered room: consoles,
games, channels, apps, media, settings and menus. Different table models have
spaced positions side by side. No loading screen or interruption to room/table
rendering is permitted while browsing/preparing layouts. A on a selected
console sends the other consoles flying off and presents its saved layout.
Keep the chosen assets, authored geometry, saved cameras and browser drafts.

### User answers, round 1 (accepted)

1. **Channels:** collections can contain games from any system, including
   modelled consoles. A modelled system has no duplicate system channel.
   Other systems/categories without a model belong in the channel list.
2. **Table identity:** each **table model has one permanent place** in the
   room. Its TV and console arrangement changes there; there is not one
   separate table per saved console profile or TV combination.
3. **Same table:** rearrange on the current table when home and destination
   use the same table and TV. Preserve the exact requested saved composition.
4. **Cross-table travel:** the departing and arriving tables **may both be
   visible briefly**. Ordinary browsing need only render the current table.
5. **Return home:** leaving a console layout returns to the **original home
   table and remembered selection**. Round 2 adds the collection-origin exception.
6. **Four directions and channels:** the user replaced the earlier selector
   scheme. All four directions move the selector freely among consoles and
   cartridges. TV channels appear as a **list**, with Up/Down choosing a
   channel. Up/Down no longer act as global table/TV mode switches.
7. **Insert/launch/eject:** **A inserts** a game; a separate **A again launches**
   it. **B ejects when a game is slotted.** Down is no longer an insertion
   shortcut. This replaces the premise of the old question 7; do not ask the
   user to choose an Up/Down mode-switch scope again.
8. **TV framing:** keep **the whole front of the TV visible, plus the system
   UI resting on top**, when using its interface. A narrow bezel crop does
   not satisfy this choice. Author a separate UI view without overwriting
   existing saved camera views.
9. **Collection game with a model:** open its console's saved layout with
   that game selected. Keep the separate insert/launch controls; no automatic
   insertion or direct launch from the collection.
10. **Execution boundary:** all frontend browsing stays in the room; **games
    and external apps run full-screen after launch**. Embedding actual emulator
    or app execution in the TV is not required.
11. **First app/media scope:** **Ports, MPV, main menu and all its submenus**.
12. **World editor:** editable table positions and travel paths, with suggested
    spacing. Preserve existing per-layout editing, drafts and history.

### User answers, round 2 (accepted)

13. **TV focus:** select the TV as an object; A controls it, B returns to table
    selection. The physical D-pad directions stay available for spatial browsing.
14. **Channels only at home:** console-layout TVs show metadata and menus.
15. **More cartridges:** moving past a spatial edge brings more games into
    view; L2/R2 retain system switching. Preserve the loaded game's identity
    and independent resident cartridge when the visible window changes.
16. **TV hierarchy:** Up/Down chooses a channel; A opens its list; B returns
    to channels. This is not a two-column guide.
17. **Collection return:** leaving a console layout opened from a collection
    returns to that collection and remembers the selected game. In cartridge
    browsing, B ejects a loaded game before the next Back can leave.
18. **R3 cameras:** R3 alone cycles the authored camera views. The full-screen
    cartridge carousel is removed from Slotted's target interaction. Keep
    installed legacy behavior separate until the candidate is accepted.
19. **Room appearance:** start with a simple floor and walls with consistent
    lighting; additional furnishings can follow later.
20. **Random:** show a random game with separate **Shuffle** and **Open**
    actions. Open routes a modelled game into its saved cartridge layout.

### User answers, round 3 (accepted)

21. **Retain loaded games:** each console keeps its inserted game until explicit
    eject/replacement, including across navigation and return from gameplay.
    The current view-hide reset is incompatible with this; logical media
    ownership must outlive individual views and the native GL session.
22. **Startup:** open the home table and remember the selected console/channel.
    Do not resume the last console layout/TV list or use the existing ES startup
    setting as Slotted's browsing destination.
23. **Cross-table choreography:** the camera follows the selected console as
    it flies to the other table and lands. Combine this with continuous room
    rendering, the permitted brief two-table view and exact authored landing.

### Close-up clarification (accepted 21 October)

24. **Preserve exact saved close-ups**, including console views that put the
    table outside the frame. Keep the room rendered continuously. This is an
    explicit exception to literal table visibility at every camera view; it
    does not change full TV/status framing for menus or continuity during travel.

### Implementation design and current evidence

Use a common rigid world transform for each active saved profile, mapping its
table pose to the table model's fixed room anchor. Transform its objects and
camera eye/target together; keep FOV, materials and authored relative positions.
Keep world placement separate from durable console JSON. Prepare destination
assets while continuing to render the current table; persistent world identity
does not require full residency of every off-screen asset.

Read-only inspection of the ten top-level saved console profiles found two
consistent furniture groups: plain `table` at its default scale/pose and
`wooden-table` at scale 0.7, with matching saved table poses within that group.
SNES omits the furniture override and uses the existing plain-table default.
No authored profile was changed by this inspection. This supports the planned
one-anchor-per-model mapping; it is not a runtime implementation or device test.

Spatial selection based on on-screen positions is the recommended navigation
design. Edge traversal reveals further sorted/filtered cartridges, while
L2/R2 keep system switching. Avoid unstable
neighbor choices caused by hover motion or camera pans; use stable layout
anchors and preserve game identities and sorted/filtered list order.

Initial implementation increment (historical): `SlotSpatialNavigation.h` provides directional
neighbors, opposite-edge entry into a new partial cartridge window and stable
anchor projection. `SlotWorldLayout.h` maps saved layouts to table anchors while
preserving the original camera view basis (rebuilding close cameras from rounded
world eye/target positions causes drift). The native renderer exports stable
console/cartridge/TV anchors via `slot_tabletop_focus_points`; hover and insertion
do not redefine a target's home. These are foundational APIs, not completed
frontend focus handling, a world renderer or a finished phase. Validation and
device state are recorded in TABLETOP_HANDOFF.md.

The native TV UI view now computes a default that frames the complete cabinet
and the widest supported top status cluster, rather than filling the display
with glass. An authored home screen camera still takes precedence; existing
console cameras are untouched. Native host probes checked home and console TV
front/status bounds for Panasonic at 720×480 and PVM at 720×540. This is native
framing evidence with a test pattern, not TV-hosted frontend menus or device
acceptance. Room floor/walls, fixed world ownership, actual frontend TV hosting and separate
room/home editor scenes are now implemented and host-tested. See the 21 October
checkpoint in TABLETOP_HANDOFF.md for precise evidence and remaining gates.
Live continuity was observed on hardware and accepted during the user's replay;
mixed room/home/console upload and forced rollback passed. Broader variant and
performance acceptance still remains; consult the latest handoff rather than
the older intermediate spike status.

### Remaining design follow-ups

All 24 questions are answered. Remaining implementation details include
transition timing, interruption/retarget details and cold-start/error presentation.
Reuse existing accepted behavior where it remains compatible; do not reopen
answered choices without a concrete conflict or treat recommendations as answers.
