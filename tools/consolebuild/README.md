# Cel-shaded console models

Slotters' DMG-01/Game Pak and PSP-3000/UMD exemplar source, dimensions and
remaining discrepancies are in [MODEL_EXEMPLARS.md](../../docs/MODEL_EXEMPLARS.md).
The complete source-search, preparation, integration and validation recipe for
future families is [MODEL_WORKFLOW.md](../../docs/MODEL_WORKFLOW.md).
The next completed pair is [CGB-001 / dedicated CGB media](../../docs/MODEL_GBC.md)
and [AGS-001 / GBA Game Pak](../../docs/MODEL_GBA_SP.md). Their CC BY 4.0
recreations use `import_handhelds.py` and `handhelds.py`; the complete CGB shell
fills a missing source part with original MIT geometry. Physical corrections
precede the uniform 168/78 and 224/82 presentation scales.
Their physical authored recreations are credited under `third_party/models`.
The remaining cartridge systems (SNES PAL/US, NES, N64, Genesis/Mega Drive
Western/Japanese/EA, DS card, Pico-8) have original physical media from
`media.py`; see [MODEL_MEDIA.md](../../docs/MODEL_MEDIA.md). Both SNES consoles now
use authored sources; see [MODEL_SNES.md](../../docs/MODEL_SNES.md), `import_snes.py`
and `snes.py`. The N64 uses Joseph Rohm's recreation; see [MODEL_N64.md](../../docs/MODEL_N64.md),
`import_n64.py`, `n64.py` and `n64-evidence.sh`. Other remaining consoles retain
their procedural housings. Build those
consoles with `blender -t 1` (enforced): multithreaded EXACT booleans are not
repeatable. `check_media.py`, `review_media.py` and `media-evidence.sh` are
the media slice's clearance, neutral-review and complete evidence tools.

SNES review uses `snes-evidence.sh` (148 forward/reverse/repeat asset hashes,
all-media clearance, hero repeats, unit suite and ARM64 build) and `snes-review.sh`
(neutral before/after, native poses/timed scenes, green label probes and accepted
family regression). Freeze `3a177a4` source/assets in `build/snes/before` first.
`compose_snes.py` produces blank-media sheets and correctly timed GIFs. Use
`SLOT_NEUTRAL_VERSIONS=after` only when the unchanged baseline views already exist.
The native harness's optional `timed` argument includes the production top-loader
spring and hold; mechanical endpoint captures remain its default.
`SLOT_SNES_DETAIL=detailed` is the selected profile (US 17,161 triangles).
`balanced` retains the earlier sub-15k profile; `full` retains the entire source
detail but failed repeated handheld tests. `benchmark-snes.sh` only builds an
isolated ARM64 production-scene timing wrapper. It does not connect to the device.
Shelf faces are the 3D models: `hero-shells.sh` renders every cartridge mesh at
the native hero pose into `tools/themebuild/assets/hero/`; rebuild the twelve
cartridge shapes with `tools.themebuild.shells.build` afterwards.
The six supported cartridge shapes use Realistic shelf captures; other cartridge
shapes explicitly use cel, and PSP is untouched. Baked faces retain their finish
when the animation's style option changes. `realistic-faces-evidence.sh` repeats
the GBA export, hero captures and six affected shape/shell/backing builds, runs
the shelf/scene contracts and full suite, and builds ARM64 from cached libraries.
The offline harness accepts `first` to capture just the first scene frame for
the native hand-off test. See MODEL_APPEARANCE.md for results and device status.
Prepared image-free GLBs rebuild offline; `import_authored.py` records the
source adaptation. Geometry keeps CC BY 4.0 (DMG/Game Pak) or CC BY 3.0 (PSP);
processing code and our ECMA UMD stay MIT. Preserve `_slot/MODEL_CREDITS.txt`.
Millimetre/motion anchors live in `exemplars.py`.
The exporter protects their housings, LCDs, keys, slot rails and hinges;
secondary details alone are decimated. `model-master.glb` / `media-master.glb`
retain authored detail, and `*-physical.glb` use real metres for cross-system
comparison (1 mm = .001 glTF units). Runtime files use uniform per-scene
presentation scales. DMG/PSP have .4-unit hulls and .65/.83/1 shadow bands,
with small authored glass highlights; other families retain their finish.
Exemplar GLB node extras preserve `printed`, `hinged`, `hinge_mm` and any
`dimension_critical` flag. Scene extras state the project axes, native scale
and conversion to metres. Retain these when importing/editing an exemplar.
The PSP pivot and native footprint share the definitions in `exemplars.py`.

## Offline exemplar review

Work in an isolated checkout. Freeze the receiving commit's `tools/slotlaunch/` and
`theme/art-book-slot/_slot/{consoles,shells,shapes}` into
`build/exemplars/before/` with `git show` or `git archive`. References belong
only in ignored `research/`.
DMG/PSP originally compare against `fba7ffe`; the CGB/AGS slice compares against
`65ceb24`, preserving those completed exemplars and the UMD turn.

1. Rebuild `gb psp` with Blender, then call only
   `tools.themebuild.consoles.build(Path('theme/art-book-slot/_slot'))` to
   refresh console packaging. This does not regenerate shelf XML.
2. Reuse cached `build/native/lib` plus pinned SDL headers for
   `sh tools/slotlaunch/build.sh`. Do not use `build.ps1` for offline review:
   it fetches libraries from the device.
3. Run `sh tools/consolebuild/offline-preview.sh` in WSL with x86-64 SDL2,
   SDL2_image and Mesa EGL/GLES2. `SLOT_DESKTOP_IMAGE_LIB` can point to their
   local library directory; otherwise locally extracted libraries in
   `build/native/desktop/usr/lib/x86_64-linux-gnu` are used.
4. Render matched neutral views with
   `blender -b --python tools/consolebuild/review.py`, then compose the sheets
   with `python tools/consolebuild/compose_review.py`.
   `SLOT_REVIEW_VERSIONS=after` avoids rerendering the frozen baseline;
   `SLOT_REVIEW_SYSTEMS="gbc gba"` selects the new pair in all three review tools.
   Use `--python-exit-code 1` in automated Blender commands so Python assertions
   produce a failing process exit status.

`check_handhelds.py` checks every exported native triangle at 101 aligned feed
positions plus deliberately colliding controls. It includes physical short-normal
faces. Run the native capture with `gba ASSETS OUTPUT_DIR insert diagnostic` to
verify that the free label is visible and the aligned label faces the underside
as shown in Nintendo's AGS manual. CGB's equivalent diagnostic checks the 33.4-mm
rear lip. `gbc ... compatible` captures the notched DMG Game Pak mesh in the CGB bay.

The capture harness includes the actual C renderer and scenes and reads only
local original/blank media. It explicitly selects GLES2 under SDL's offscreen
driver, and never calls hooks, device framebuffers, ION, audio or display-layer
entry points. Each PNG is 720x480. Mechanical poses omit the final fade to show
seating; timed sheets/sequences also show the production fade and holds.
Desktop software rendering is visual evidence, never handheld fps evidence.
For the DMG lip check, run the freshly compiled `build/exemplars/native/after`
with `gb ASSETS OUTPUT_DIR insert diagnostic`. The output directory must exist.
This uses a solid-green face in the offline harness only, checks the seated
case against the independently projected 45.5-mm lip, and writes
`clip-check.json`. Normal captures retain blank original media. Neutral review
also renders `after/gb/rear-loaded.png` with the physical cartridge mesh.
On Windows invoke WSL executables with `wsl --exec` so shell quoting and
environment expansion do not change the arguments.

`models.py` assembles all console exports. DMG/PSP/CGB/AGS and both SNES regions use the separately credited
authored geometry above; the remaining procedural geometry and processing code
are MIT. Reference photographs and source textures are excluded. Printed legends
use original paths or the project's Open Sans font, whose OFL notice ships with
the theme.

The models cover DMG Game Boy, Game Boy Color, open Game Boy Advance SP, PAL/Japanese
SNES, North American SNES, NES, N64, Western/Japanese Mega Drive Model 1, open DS Lite,
PSP-3000 and an original Pico-8 fantasy console.

With Blender 4.5 installed, run from the repository root:

```sh
blender -t 1 --background --python tools/consolebuild/models.py
python -m tools.themebuild
```

Pass system names after `--` to rebuild a subset. Generated `model.glb` files are
editable complete 3D models with vertex colours. `model.mesh` files contain bounded
16-bit indices and interleaved positions, normals and colours for the GLES renderer.
The native shader applies three light bands and an inverted-hull outline. Each
variant normally targets 15,000 triangles or fewer. SNES also has measured higher
detail profiles; see `docs/MODEL_SNES.md`. Native format limits are 65,535 split
vertices and 600,000 indices. The NES flap and PSP UMD door use separate
index ranges, rotated around their physical hinges at runtime. Thin mouldings are
retained if mesh reduction would stretch vertices outside their original bounds.

`body.png` uses the same camera and initial pose, for the idle shelf and software
fallback. Packaging computes each model's idle height from its rendered bounds,
keeping the full housing below the shelf edge before it rises.

Native motion uses the actual ROM's baked face. GB/GBC first show the front, turn
180 degrees around the tilted model's vertical axis, then receive the cartridge
through the rear bay. The SP receives its cartridge through the front edge, NES
opens its flap and loads horizontally, and the home top-loaders receive upright
cartridges. All consoles turn in 3D with their selected media and fade as one scene.

DS Lite shows the open front, turns to the rear Slot-1 bay, and receives the game card
label-down. Its upper and lower screens, hinge barrels, speaker perforations, controls,
rear charging socket, stylus and Slot-2 dust cover are complete geometry. The card's
opposite face shows the connector fingers; a short spring compression seats the latch.
Loading orientation follows [Nintendo's official guide](https://en-americas-support.nintendo.com/app/answers/detail/a_id/3906/~/how-to-insert-and-play-a-nintendo-ds-game-card).

For isolated device diagnostics, `SLOT_PREVIEW=1` disables shelf capture and uses a
plain background. Run the helper with a fictitious ROM path in a supported ROM
folder to exercise its model without launching an emulator or changing game data.
Regular hooks do not set this variable. Model rendering requires SDL's GLES2
renderer; the preview sprite remains available on unsupported renderers.

The DS Lite refinement uses a 145-degree open lid, six speaker holes per side,
a slimmer white LCD surround, a continuous cross-shaped D-pad, low-profile button
caps, and a long central lid knuckle between short fixed base pivots. Narrow hinge
collars, end caps, microphone and right-side indicator windows follow the hardware.
Shoulder keys have their own seams and L/R legends. Volume-track grips, charger
contacts, a wrist-strap bridge and the embossed dual-screen lid emblem. The turn
adds a 15-degree tilt to expose the rear lid and Slot-1. The game card has a 10-pixel
edge that fits the 11-pixel mouth, and both card faces follow the tilted console.

PSP-3000 has a complete curved front/back shell, silver perimeter, 16:9 LCD,
separate directional keys, textured analog nub, four action glyphs, curved shoulder
keys, system buttons, LEDs, USB/DC/headphone ports, battery cover and UMD drive.
It shows the front, turns to the rear, opens the bottom-hinged cover, feeds the
whole case into the holder, then closes. A 12-degree free-case twist straightens
before the feed; withdrawal reverses it. The case, rails and stop then move
with the same rigid hinge. The door is drawn once after the SDL media plane,
so depth-tested cover geometry hides the complete UMD after seating.

Hardware references are [Nintendo's DS Lite booklet](https://assets.nintendo.eu/image/upload/v1635390384/NAL/Support/DSLiteInstructionBooklet.pdf),
[Nintendo's product dimensions](https://www.nintendo.com/en-gb/Support/Legacy-system/Product-Information-242119.html)
and [Sony's PSP-3000 quick-reference manual](https://www.playstation.com/content/dam/global_pdc/en-gb/corporate/support/manuals/psp-docs/psp-3004/PSP-3004-QR%24en-gb.pdf).
DMG/PSP authored geometry has the separate credits above; source images are excluded.

The all-system accuracy pass replaces overlapping GB/GBC/SP D-pad bars with continuous
cross mouldings. DMG has its broad lower-right corner and a 160:144 LCD; GBC has a
perforated speaker, curved battery housing and its own side controls/infrared window. SP has a 240:160 LCD,
EXT.1 and EXT.2 connectors, power/charge LEDs, volume/power sliders and a battery cover.
Controller sockets keep their physical proportions independently of the housing's
vertical scale. The procedural N64 described here was replaced by the authored model
(MODEL_N64.md); Mega Drive has trapezoidal 5+4 contact bays. Model 1 controls are grouped on
the left, alongside the single vent bank, with the circular deck offset to the right.
Genesis uses a white reset button; Japanese Mega Drive uses blue. Rear connectors and
NES side RCA sockets are modelled. PS1's procedural model includes stacked memory-card
and nine-contact controller bays; its source is `tools/discpreview/preview.py`/`psx.h`.

Printed lettering and PSP glyphs skip the inverted black hull. Native normals of length
0.25 mark ink; physical surfaces retain unit normals. The outline pass clips ink in the
vertex shader, retaining early depth tests without a per-pixel discard. Degenerate triangles are omitted
and missing corner normals use the triangle normal. The Blender preview excludes ink
from Freestyle outlines too, so white details remain legible in both rendering paths.
Cartridge mouldings add original font outlines to the GB/GBC/GBA headers. The DS card
has its side latch clearance, asymmetric lower corner and recessed 17-contact rear bay.
Cache revisions include the freshly generated rear face and remain stable on rebuild.

Additional references: [Nintendo's SP booklet](https://csassets.nintendo.com/noaext/image/private/t_KA_PDF/agsmanual_english?_a=DATAg1AAZAA0),
[Evan-Amos's original Game Boy Color photograph](https://commons.wikimedia.org/wiki/File:Nintendo-Game-Boy-Color-FL.jpg),
[Genesis Model 1 photograph](https://commons.wikimedia.org/wiki/File:Sega-Genesis-Mod1-Bare.jpg),
and [DS card photograph](https://commons.wikimedia.org/wiki/File:Nintendo-ds-cartridge.jpg).
These are inspection references, not shipped textures or downloaded models.

Pico-8 has an original red deck over a charcoal lower housing, upright cartridge bay,
eject lever, ventilation banks, controller sockets, pixel-eight plaque, rear sockets
and rubber feet. Its 12,692 native triangles use the existing home top-loader renderer and
1.15/1.05-second insert/eject motion. This is invented hardware for the fantasy console.
Pico-8 cartridge RGB and credits come from the user's local ROM at bake time; generated
model files and theme assets contain no game artwork.
