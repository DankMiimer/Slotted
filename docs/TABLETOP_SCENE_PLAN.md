# Tabletop cartridge scene plan

18 October 2026. Accepted implementation plan; see TABLETOP_HANDOFF.md for the
verified prototype and deployment checkpoint.

## 1. Agreed experience

### Latest Slotted clarification: one persistent room (20 October)

The user's latest correction is recorded in
[SLOTTED_THEME_PLAN.md §11](SLOTTED_THEME_PLAN.md#11-latest-user-clarification-one-persistent-room-20-october).
For the finished Slotted frontend, home console selection and TV channels share
one table. The latest answers replace the earlier Up/Down focus switch with
**four-direction spatial selection** for consoles and cartridges, and a vertical
TV channel list. **A inserts, a separate A launches, B ejects a slotted game**;
the old directional insert/eject shortcuts are superseded. Each table model has
one fixed place in the room; rearrange layouts there and travel between table
positions when required. Both endpoint tables may briefly be visible in travel.
Keep the whole TV front and its top system/status UI visible for TV interfaces.
Collections can include modelled games; choosing one opens its saved cartridge
layout with that game selected. All frontend browsing stays in the room without
loading screens; games/external apps run full-screen after launch. First app/media
scope is Ports, MPV and every main-menu submenu. The Room editor must expose
positions and paths with suggested spacing. A on the spatially selected TV enters
its controls; B returns to table selection. Channels are home-only. Directional
edge movement reveals further cartridges, L2/R2 keep switching systems, and R3
cycles authored cameras. Leaving a console layout opened by a collection returns
to that collection and selected game after ejecting. Random has Shuffle/Open
actions. Start with simple floor/walls and consistent lighting. The older
table-replacement and full-screen carousel descriptions
below record the installed prototype, not final Slotted behavior. Preserve all
existing saved layouts and cameras.

The final three answers keep each console's game inserted across navigation and
gameplay return until explicit eject/replacement. Startup opens the home table
with remembered console/channel focus. When moving to another table model,
the camera follows the flying selected console to its exact saved landing.

### Seamless system changes (20 October)

The user requests no black loading screens between consoles. Keep the live
table and shared TV/status/system information visible; fly outgoing console and
cartridges away, and bring the destination hardware into its exact saved layout.
Use the destination layout's TV when it differs, grouping its glass/status with
the cabinet. Preserve saved cameras and all selected source detail. Prepare likely
next systems and bounded labels, and retire unused resources within measured
memory limits. Rapid navigation must prefer the newest destination and remain
responsive. This is distinct from normal validated, exactly-once game launching.

System changes now have a whimsical lift-and-flight in waves, followed by a
small damped settling wiggle. Related console parts and TV/glass/status travel
as rigid groups. Incoming hardware lands in the author's everything camera;
only then does the camera pan to the specified saved browse view. Upright
cartridges keep their authored orientation during selection hover; the flat-card
label tip must not be applied to standing cards. Saved JSON/cameras are never
rewritten to implement these runtime effects.

When the two saved layouts use different tables (Panasonic rooms use `table`,
PVM rooms `wooden-table`), the user chose a sideways slide (20 October): the TV
and status leave with the hardware, the old table slides off one side while the
new one follows it in from the other, and the hardware then streams in from that
side. The tables never overlap and no frame is empty; a table never glides
through empty space between two poses.

Switching responds at once (20 October, after n19): the hardware starts its
lift, in the same waves, on the input frame while the destination is still being
prepared, holds that lift still until the destination is ready, then flies off
with the same stagger (a destination ready within the lift keeps the original
timeline). GPU uploads stay off during any motion and run during the still hold;
the worker decodes the request's images while the lift plays. Returning to the
current room before the flight lowers the lifted waves again. The everything
view is still reached exactly; the pan to the saved browse view starts as the
last wave touches down, while its landing wiggle settles, and lasts at most
0.5 s. The profile's own transition time still governs ordinary camera pans.

See [measured research and design](SYSTEM_SWITCH_RESEARCH_20261020.md) and the
current [implementation checkpoint](TABLETOP_HANDOFF.md). n17 installed the
persistent native streaming/session pipeline, n18 the wave/hover/camera increment,
n19 the table slide and n20 the responsive switch above.

### Selected cartridge replacements (19 October)

The six selected sources are prepared, active locally and **installed/hash-verified
on the device**. Host/device rendering and measured scene timings are in the
[validation report](CARTRIDGE_VALIDATION_20261019.md); true physical clearance,
authored framing and full performance acceptance retain explicit limitations.
Current counts, exact selected MD nodes, GBC completion and retained alternatives
are in [the implementation checkpoint](CARTRIDGE_ASSET_QUEUE.md).
The selection discussion below records the original queue decision. The user
subsequently authorized implementation and explicitly **held GitHub publication
until a fitting N64 replacement is found**; keep the current N64 unchanged.

The user selected satchii_'s **Nitendo DS Cartridge Super Mario 64** (CC BY 4.0)
after the Socket research and requested it be queued for theme implementation.
Their follow-up also selected **thegraphicsgeek's Pokemon Fire Red GBA cartridge**,
**dark_igorek's Battletoads NES cartridge**, **Bob/MeBob's low-poly GB cartridge**,
and **Wikiti's Game Boy Color source**. Wikiti's retained source was previously
found to include only the exposed seated half of its cartridge; a complete loose
card requires original reinspection and documented completion, not an automatic
substitution. For **Nerd_Sp's Mega Drive scene**, use **one of its three freestanding
cartridges**, explicitly excluding the cartridge seated inside a game case.
See [the asset queue](CARTRIDGE_ASSET_QUEUE.md) for the source, status and exact
integration sequence. This is a queued source choice, not a completed integration
or installation. Preserve all current cards/sources and the user's authored
layouts; acquire the creator's original rather than copying Socket's derivative.
The user also explicitly reaffirmed that the **current N64 cartridge is perfect
and must not be changed**. Preserve its exact assets, materials and registration;
its license is only a release-packaging consideration, not a replacement task.

### Slot/launch cameras, device import and layout export (19 October, latest request)

"After slotting a game, pan smoothly to the 'everything - overview' camera view. When a
game is started, pan to the handheld console and then into the handheld's screen (for
TV consoles ... pan to the TV and pan into the TV screen)." Plus an editor button to
import the current layout from the device, and to save the current layout for all TV
consoles or all handheld consoles. A camera picked by hand (Select+R3) is kept after
slotting; launches always use the console/TV sequence. Device import never writes to
the device; export never overwrites without a confirmation and history copies.

### Close cameras and frame rate (18 October)

"When scrolling through the games the carts clip away when the camera gets too
close. Smartly fix this", plus research into better frame rate with barely any
quality loss. Accepted behaviour: no model is ever sliced by the camera (the
near plane follows the closest geometry in view, editor and device alike); in
the cartridge view, carts in front of the selected one that would hide its label
fade to a quarter while it is selected. Speed work must keep pixels identical
unless the user chooses a listed trade-off (see the handoff's frame-rate notes).
Their authored cameras and layouts are not changed.

### Scene editor object tools and manual cameras (18 October)

Add an easy two-object position/rotation swap, multi-object move/rotate around a
shared pivot, and explicit manual position/look-at/FOV controls for each camera
view. Preserve model sizes and hierarchy, including the TV's status child; swaps
use world transforms. Add selection feedback and Undo/Redo. Manual camera input
must remain independent for each view and must not be overwritten by an active
pan. Preserve existing authored JSON and newer browser drafts while testing.

### Scene editor upload (18 October)

**20 October startup correction:** editor uploads must survive a device reboot.
Retain the selected compatible frontend by SHA-256 on userdata and activate it
from Knulli's synchronous post-share hook before ordinary frontend startup.
Preserve the firmware binary and any existing startup script, normal settings,
all authored layouts, and exact recovery copies. Boot ends process-only preview
overrides; it must retain tabletop support. Hash/firmware mismatch falls back to
the firmware frontend. Verify with an actual reboot and a fresh data/runtime audit.

The user authored a GBA/PVM layout and requested device testing plus an editor
**Upload to device** button for future layouts. The action saves the current
scene, uses a fresh hash-verified snapshot and narrow owned manifest, then opens
that console/TV on the device. Preserve normal preferences with process-only
preview overrides, retain recovery evidence, block uploads during gameplay and
roll back failures. Do not reframe the authored camera or replace selected models.

### Scene editor expansion (18 October)

The editor covers every currently integrated home console and handheld, with
Panasonic, PVM and Old TV profiles. Preserve each authored overview and browser
draft. Add independent editable cameras for overview, straight-on TV, selected
hovering cartridge, console, and L3 free inspection, with adjustable smooth pans.
The user chose a device chord to cycle views: **Select + R3**, in the order
overview / TV / cartridge / console. R3 alone remains the carousel; L3 remains
inspection. Ordinary Select options/favorites actions remain available.

Expose separate TV and handheld LCD metadata settings: visibility, field toggles,
artwork/text layout, text scale, padding and colours. Handheld LCDs start blank,
preserving the previous decision; the author can now opt into metadata there.
Use registered LCD geometry, including both DS screens and the chosen local SP.
Keep one video decoder and normal validated, exactly-once launch ownership.

Add table width/height/depth scaling with optional linked proportions and two
source furniture choices: Qu3st10n's TV stand (CC BY-NC-SA 4.0) and AndreyUEDev's
wooden table (CC BY 4.0). Preserve original downloads, source quality and licensing.
Furniture changes and camera presets never automatically alter the overview or
the hardware/cartridge placements. The narrower furniture needs an authored
layout or explicit scale/placement edits to support the existing arrangement.

The normal game browser becomes one live 3D tabletop scene. Home consoles, TV,
and up to twelve loose game cartridges occupy the same physical surface
(increased from eight at the user's request during scene editing).
The TV sits forward on the right. Both console and loose cartridges occupy the
front-left group. These are the user's latest composition revisions: the earlier
north/behind carts, centered foreground rows, and back-left console are
superseded. Start with two staggered columns of four cartridges on the left,
keeping labels and the console clear of the TV. Bring the camera closer and
minimize unused table above/below; use the horizontal space of 3:2 and 4:3
handheld viewports. A shallow arc/stagger can be tuned per system.

The selected loose cartridge lifts slightly above the surface, settles into a
restrained idle motion, and returns gently when selection changes. Selecting
another cartridge does not change the metadata of the slotted game.

Confirmed controls and behavior:

| Action | Result |
|---|---|
| Left/Right | Browse the existing sorted/filtered game list and move focus between physical cartridges |
| A on a loose cartridge | Insert it; if another game is loaded, eject that game and insert the highlighted one |
| A on the slotted game | Animate power, show authentic BIOS boot when supported, zoom into the display, and launch normally |
| Up | Eject without launching; retain the existing explicit eject action |
| L1/R1 | Change the slotted game's metadata page, as today |
| R3 | Temporarily open/close the existing full-screen cartridge carousel |
| L3 | Inspect the highlighted loose cartridge (D-pad turns it; L3 or B puts it back) |
| Right stick left/right | Small clamped camera orbit, easing back on release |
| B in full-screen carousel or inspection | Return to the tabletop |

R3 being a toggle is the planning assumption following the user's choice of
button. Returning from the full-screen carousel preserves the cursor and loaded
game. Its A behavior matches the tabletop; opening it never launches or ejects.
Down can remain an insert-only alias for compatibility, with A shown as the
primary action. Ordinary Back, menus, search, favorites, and game options retain
their existing entry points outside the temporary modes.

After insertion, focus remains on the loaded game's identity, so another deliberate
A press launches it. When its list position is visible, its empty table position
gets a small 3D slot marker; focusing that position highlights the physical loaded
cartridge/console instead of drawing a duplicate cartridge. The same game never
appears twice in the twelve-position window. Small libraries show only their real
entries. Larger libraries use a moving twelve-position window, with bounded
prefetch rather than loading the complete library into GPU memory.

**User decision, 18 October (supersedes the earlier own-LCD choice): "I want all the
handhelds using the same table view with a TV like the consoles."** GB/GBC/GBA/DS/PSP
and PICO-8 stand or lie on the same table as their media, the TV shows their metadata
and the launch zooms into the TV, exactly as for the home consoles. Their own LCDs stay
blank in the tabletop view.

## 2. Current implementation and reusable parts

This is an extension of the existing pinned Knulli frontend, not a theme-XML-only
change. The relevant baseline is:

- `tools/frontend/apply.py`: patches the pinned frontend, including carousel
  input, the small strip, and validated launch deferral. The strip is currently
  hard-coded to the top 120 pixels of the 720 x 480 logical view.
- `tools/frontend/SlotState.h`: independent highlighted/desired/inserted/launch
  identities, safe-boundary swaps, optical closing, and exactly-once launch.
- `SlotPresentation.cpp`: immutable metadata snapshots, pages, one VLC preview,
  display textures, native console scene, and reading transitions.
- `SlotNative.c` and `tools/slotlaunch/console-gl.h`: existing GLES2 geometry,
  textured meshes, physical registrations, and insert/eject mechanisms. Their
  camera/projection is specialized and depth attachments are owned per mesh;
  both need adaptation for a shared scene.
- `SlotTelevision.h` and `tools/themebuild/television.py`: the TV is currently a
  rendered PNG plus a registered live-glass quad. Prepared TV GLBs already exist
  under `third_party/models/` for Panasonic, Retro, and Sony PVM.
- `SlotHomeLayout.h`: current relative physical scale and floor contacts, useful
  as starting registrations. Its screen-space placement will be superseded.
- `theme/art-book-slot/_slot/status.xml`: live 2D battery, Wi-Fi, and clock,
  including Raster Forge font and icon artwork.

Keep the working metadata resolution, one-preview-decoder policy, model choices,
finish/paint settings, per-game labels, registered hinges/slots, normal launch
validation, and launch ownership guard. Reuse their data and behavior while
changing the presentation and the primary A action.

## 3. Shared 3D scene and asset quality

Introduce a tabletop scene renderer behind the existing presentation component.
It owns one camera, common world units, one scene color target and shared depth
attachment, and nodes for table, TV, console parts, cartridges, shadows, display
surfaces, and status objects. Each node has its own world transform. Camera view
and perspective matrices apply to every object and live screen together.

The renderer must clear depth once for the scene, not between objects. Refactor
the native draw path to accept the scene camera and depth target while retaining
the standalone helper's existing behavior. Hardware parts and labels must
occlude correctly during insertion, orbital camera movement, and inspection.
Keep the frontend's window, event loop, input ownership, and final presentation.

Use full 3D TV housings with live display material on the registered glass mesh.
Metadata, preview video, and BIOS output remain textures on real screen geometry;
their UVs and perspective must stay attached throughout camera changes. Replace
the current bilinear screen-space projection with normal perspective-correct
mesh texturing, preserving the curved screen shape where available.

Preserve source models, UVs, textures, and full-detail editable masters. Audit
each runtime derivative against its source before making it larger in view;
some earlier derivatives deliberately reduced geometry or texture resolution.
Recover detail from the original files where the new view exposes that loss.
Do not enlarge cached console/TV PNGs or upscale source textures to claim extra
detail. Render geometry at the final display size, with existing supersampling
where its measured cost is acceptable. Preserve nearest-neighbor treatment of
intentional pixel artwork.

Share cartridge geometry and plastic textures across visible instances; load
their per-game labels separately. GLES2-compatible repeated draws are sufficient
initially; do not depend on hardware instancing. Split large indexed meshes into
supported batches when necessary, preserving geometry instead of silently
decimating it. Inspect reverse sides and thickness so 360-degree inspection does
not expose missing faces or labels attached to invisible placeholder planes.

### Table source

Use the requested [Wooden Table by lena-wachs](https://sketchfab.com/3d-models/wooden-table-e4a9129ea0114d3e8d1989971eca53ef).
Its [public model metadata](https://api.sketchfab.com/v3/models/e4a9129ea0114d3e8d1989971eca53ef)
was checked on 18 October: downloadable, 276 vertices, 536 faces,
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Obtain its normal licensed download, preserve the original archive and source
hashes, and prepare a runtime tabletop using its actual mesh/material parts.
Register the top surface as the world contact plane; retain suitable edges/trim
and omit legs or other parts outside the planned view. Fit its dimensions to the
hardware arrangement and preserve sensible wood grain rather than stretching
the texture arbitrarily. Record all changes and attribution in `CREDITS.md` and
the shipped model credits. Downloadable metadata does not establish that its
archive has already been acquired; acquisition is an implementation prerequisite.

## 4. Composition and camera

Keep the TV farther forward on the right and BOTH console and cartridges in the
front-left group, following the latest user steering. Use a tighter, more frontal
view of the TV and two staggered cartridge columns on the left. Tune physical
positions and camera distance together. Preserve believable proportions rather than
independently scaling each object until it fills a rectangle.

Use the entire scene height after removing the permanent cartridge strip and
flat status bar. Move the camera closer and frame the TV's screen plus complete
front frame; the rear cabinet and some top casing may extend off-screen. Keep
the original mesh intact. Leave a visible top-front ledge for the status objects.
The full screen/frame and status must remain visible over the allowed browsing
camera range; also reserve clearance for open lids and insertion paths.

Create per-console/per-TV layout profiles with world-space contact, slot, label,
power control, status ledge, and display anchors. Optimize for perceived size and
readable labels/metadata at 720 x 480. Compare projected display area to the
current Panasonic 222 x 159, Retro 184 x 143, and PVM 155 x 108 baseline; seek a
clear increase for each model rather than fitting the whole cabinet.

### User-authored layout tool (requested during implementation)

Provide a local interactive editor using the actual 3D assets: model translation
and rotation gizmos, group manipulation for cartridges, free orbit/pan/dolly and
numeric camera/pose/FOV controls, 3:2/4:3 previews, undo/redo, table contact, and
save/export. Saved JSON outside temporary build data is authoritative; the native
renderer must reproduce its transforms/camera without automatic reframing.
The first working editor covers the SNES/Panasonic prototype; expand by system
profile alongside the frontend rollout. Preserve the user's authored layouts.

Provide a small, clamped user camera orbit and smooth return to its default
position. Initial tuning range: about +/-8 degrees yaw and +/-4 degrees elevation,
subject to screen/frame visibility. Implemented bindings (18 October, after the
input audit found L2/R2 already switch systems): the right stick's free horizontal
axis orbits, clamped per side so the screen, status and console are never cropped
more than in the authored view; L3 (the user's choice, replacing the tabletop's
save-state shortcut) toggles inspection. Inspection lifts the selected cartridge
into clear space and allows a full 360-degree turn with the D-pad; B or L3 restores
its table pose. R3 remains dedicated to the carousel.

Handheld profiles frame their own screen or screen pair instead of adding a TV.
Their 3D status cluster attaches above the handheld display area, with a separate
registered anchor so it cannot cover the LCDs. Home-console status sits on the
TV's top front as requested.

## 5. Selection, slotting, power, and launch choreography

Suggested motion values are starting points for device review:

- Select: rise roughly 2-3 mm over 150-220 ms, with a small eased tilt that keeps
  the label readable. Unselect: settle over 180-250 ms without passing through
  the table. Selected idle begins after the existing quiet delay and uses a
  much smaller motion than the initial lift.
- Slot: move the same cartridge node from its actual table position into the
  registered insertion path, then use the existing seating/hinge/flap motion.
  There must be no jump to a separate full-screen insertion scene.
- Swap: finish the safe part of the current operation, return the old cartridge
  to its table home, then insert the requested cartridge. Capture immutable game
  identity; rapid browsing must not substitute a different ROM or label.
- Power: close optical lids first, then depress the real registered power button
  or move its switch, and turn on the power indicator where present. Split or
  register a source model's power part when it is currently baked into a housing.
- Boot: replace metadata/preview with authentic BIOS video and audio on the TV
  or handheld screen. Suspend preview decoding/audio while this surface is owned
  by boot playback.
- Zoom: after boot completes, smoothly bring the display to the game viewport,
  reducing its perspective skew. Preserve aspect ratio and retain the last boot
  frame through the normal emulator handoff to limit visible flashing.
- Return: restore the loaded cartridge, powered-off presentation, metadata, and
  browsing camera; optical lids return to their established reading behavior.

Extend state phases with Powering, Booting, and Zooming before Launching/Running.
Keep optical Closing where needed. A first press only inserts; it must not run
launch validation or increment playcount. A new deliberate press on the loaded
game requests Play through the ordinary frontend validation/options path. Only
after validation succeeds should the power/boot/zoom transaction begin. Ignore
held-button repeats and launch input during that transaction. A queued swap must
never turn into a queued launch.

Before actual emulator handoff, B may cancel the power/boot/zoom sequence and
return to the inserted metadata view. Missing content, boot failure, interrupted
playback, screensaver/window suspension, and process exit all need a bounded
recovery path. Actual game launch and playcount happen exactly once, using the
existing ownership guard so standalone launch hooks do not insert a second time.

## 6. Authentic BIOS boot: early feasibility milestone

A BIOS binary is executable firmware, not a video. The current frontend has no
generic facility for executing it or embedding an emulator's boot framebuffer.
Do not promise that an arbitrary BIOS file will work across all systems/cores.

Prototype a small isolated libretro boot helper, initially with PCSX ReARMed.
It runs the user-supplied BIOS through an installed compatible core and supplies
boot frames/audio to the presentation. Its save, memory-card, firmware-write, and
configuration directories are private scratch copies; user content/BIOS are read
inputs and the helper never registers a normal game launch. Where boot depends
on inserted content, provide that content read-only and stop at a verified
system/core-specific boundary before gameplay. A universal timer or a black
frame is not sufficient boot-completion detection.

Support a local boot cache only after the real execution path is proven. Key it
by BIOS hash, core/version, region/hardware mode, relevant settings, and content
identity when required. Capture it locally from the user's firmware; never ship
a substitute boot movie as though it came from the supplied BIOS. Cache creation
should be an explicit preparation step or bounded background work, not an
unexpected long pause every time A is pressed. The initial prototype must measure
cold preparation, warm playback, memory, audio sync, and transition behavior.

After the tabletop boot, apply the chosen emulator's boot-skip setting for that
one normal launch, keeping BIOS use enabled where the core requires it. Verify
the effective setting after Knulli config generation and higher-precedence
game/core options. Use a private merged configuration or supported per-process
override; avoid persistent edits to the user's core options. On exit, crash, or
cancel, remove transaction-owned temporary files. Honor games that require the
original boot behavior rather than forcing an incompatible fast boot.

Examples from current primary documentation, to verify against the installed
core versions before implementation:

| Core | Boot capability / likely normal-launch override |
|---|---|
| [PCSX ReARMed](https://docs.libretro.com/library/pcsx_rearmed/) | Real BIOS boot logo can be enabled for capture; `pcsx_rearmed_show_bios_bootlogo=disabled` suppresses the repeated logo on normal launch |
| [Gambatte](https://docs.libretro.com/library/gambatte/) | Official bootloader support; `gambatte_gb_bootloader=disabled` is a possible per-launch suppression, with hardware/content matching checked |
| [mGBA](https://docs.libretro.com/library/mgba/) | Keep `mgba_use_bios=ON`, set `mgba_skip_bios=ON` for the normal launch after the captured intro |
| Other cores / standalone emulators | Audit actual firmware behavior, frame/audio access, completion boundary, and temporary skip support individually |

The [libretro API](https://github.com/libretro/libretro-common/blob/master/include/libretro.h)
provides video/audio callbacks, but this alone does not prove every installed
core is compatible with the proposed helper. Hardware-rendered cores need their
own context support or a different adapter. Core option precedence also needs
testing; see the [RetroArch override documentation](https://docs.libretro.com/guides/overrides/).

Maintain a capability manifest per system/core: firmware requirements, source of
boot frames, audio, completion detection, cache key, and safe boot-skip support.
Systems without an authentic boot animation use power then zoom. If a BIOS/core
is unavailable or reliable suppression is impossible, fall back to normal launch
and let the actual emulator handle its boot after the zoom; clearly record that
this system does not yet support the full boot-on-the-table sequence. Do not
invent firmware, silently change the selected core, or play the same boot twice.

## 7. Voxel battery, Wi-Fi, and clock

Convert the existing Raster Forge glyphs and icon masks into real extruded
geometry. A lit source pixel becomes a short rectangular solid; merge adjacent
faces and remove internal faces so each glyph/icon is a small mesh rather than
hundreds of separate draw calls. Keep the source pixel shapes and restrained
depth so their front faces read like today's font while side faces show volume.

Create cached meshes for digits, colon, percent, battery fill/charging states,
and network states. Place them as standing objects on the registered top-front
TV ledge with small contact shadows, facing forward with the TV. Update from the
frontend's existing battery/network/time providers only when displayed values
change. Use the current local clock format; handle unavailable battery or network
information without fabricating a value. Check 100%, charging, disconnected Wi-Fi,
and the widest supported time string in the layout.

In the tabletop view, hide the old 2D status children to prevent duplicates.
Keep the current status rendering in other frontend views and during the
temporary legacy full-screen carousel. On handhelds use their own registered
status cluster described above. Status objects participate in the same camera
and lighting; they are not screen overlays.

## 8. Implementation order and review gates

1. **Record baseline and prove the two risks.** Preserve the dirty workspace,
   current source/model registrations, and reference captures. Verify source
   archive access. Build an eight-cartridge + live 3D TV/table render prototype
   and the PSX BIOS helper/skip experiment. Measure both on the RG34XXSP before
   committing to the full rollout. Produce the initial capability manifest.
2. **Build the scene and import the table/TVs.** Add shared world/camera/depth,
   source-derived runtime assets, glass materials, contacts, and layout profiles.
   Get one SNES + TV arrangement readable at final device resolution, then
   cover all three TV choices and other console footprints/open lids.
3. **Move the carousel onto the table.** Implement bounded twelve-position list
   binding, per-game 3D labels, selection/unselection, idle, exact table-to-slot
   continuity, swaps, and explicit loaded-game focus. Remove the permanent strip.
4. **Add R3 mode and camera/inspection controls.** Preserve list/filter identity
   and loaded state between views. Add clamped camera movement and full cartridge
   inspection, including correct reverse faces and restored poses.
5. **Add physical status objects.** Generate/cache voxel meshes, attach TV and
   handheld anchors, connect live values, and remove duplicate scene overlays.
6. **Integrate power/boot/zoom and normal launch.** Extend the state machine,
   implement the tested PSX adapter first, add local cache and transaction-only
   config handling, then add GB/GBC/GBA and other supported adapters. Resolve the
   chosen core/options before choosing the boot provider. Publish unsupported
   combinations instead of treating prototype support as universal support.
7. **Finish all device profiles and regression.** Test optical, front-loader,
   top-loader, and handheld scenes, both GBA SP choices, finishes/paints, source
   quality, metadata pages, previews, actual launch/return, and saved settings.
   Package only owned paths, source notices, registrations, and new runtime files.

Suggested implementation ownership: keep list/input integration in `apply.py`,
presentation coordination in `SlotPresentation`, pure transitions in `SlotState`,
and scene rendering behind `SlotNative`. Add focused camera/layout, voxel-status,
and boot-provider components rather than growing the source patch script into a
second renderer. Extend the current owned-file package/deploy manifests to include
new mesh/texture formats, adapters, and runtime data; never package private BIOS,
per-user boot caches, or local-only model sources.

## 9. Acceptance checks

- **Final view:** up to twelve distinct cartridges on the table; label readability;
  visibly larger hardware and display; complete TV screen/frame and status at
  every permitted browse-camera position; only the cabinet back/top may crop.
- **3D integrity:** shared depth/contact on table, cartridge bottoms, screen UVs,
  shadows, slots/flaps and moving lids. No billboard TV or cartridge substitutes.
  No source-resolution degradation concealed by enlarging a raster cache.
- **Input/state:** first A inserts only; another A on loaded launches; A elsewhere
  swaps; holds do not launch; R3 toggles cleanly; Up ejects; pages/options work;
  one/two/seven/eight/eleven/twelve/more-than-twelve games and list changes remain consistent.
- **Boot/launch:** known BIOS/core/region and missing/wrong firmware; cold and warm
  cache; canceled/failed boot; correct audio and completed intro; one real launch,
  no repeated boot on supported adapters, and the right ROM regardless of rapid
  browsing. Preserve saves, playtime, achievements behavior, and user settings.
- **Performance:** measure GPU/CPU frame time, memory, texture uploads, selection
  latency, preview/boot decode, and camera/idle animation with twelve high-detail
  cartridges. Aim for at least steady 30 fps (95th-percentile scene frame time
  within 33.3 ms) on the target. Treat this as a prototype acceptance target, not
  a measured promise. Optimize shared resources, batching, texture residency,
  hidden voxel faces, and unnecessary redraws before considering quality tradeoffs.
  Keep only the active preview/boot decoder and no per-frame framebuffer readback.
- **Device evidence:** extend existing meaningful input/state/layout probes and
  add final-resolution captures/short motion grids plus actual Play/return tests.
  Record the framebuffer/viewport behavior during emulator handoff; a seamless
  final frame is subject to the real emulator/display path, not guaranteed by a
  frontend zoom alone. Use the established snapshot/restore/audit development
  workflow so the user's saves/configuration and unrelated work are preserved.

First reviewable milestone: one real SNES scene with eight physical cartridges,
the requested table and one fully 3D TV, together with a measured PSX BIOS
proof-of-concept. This establishes composition, source quality, performance,
and boot feasibility before expanding the complete system matrix.
