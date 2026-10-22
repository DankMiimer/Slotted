# Physical cartridge media for the remaining cartridge consoles

**Latest 16 October cartridge work:** user-selected textured PAL SNES, optional
Tzakol style, Vxcl GBA, sunnychow PICO-8 and Chris Sweetwood N64 supersede the
corresponding historical media below. See [MODEL_CARTRIDGES.md](MODEL_CARTRIDGES.md)
for sources, licences, source-surface labels and reproduction. The US SNES and
other original media remain available.

**16 October GBA follow-up:** the GBA Game Pak now uses Dave Parker's fit-tested
two-half CAD, with original photo-referenced moulding details and a complete
board/contact strip. Its 60 × 34.5 × 7.7-mm envelope replaces the old 9.4-mm
thickness stretch. The 44.3 × 23-mm label well and hero JSON coordinates are
unchanged; label overlay moves to the new physical face at z=3.53 mm. Regenerated
GBA shape, shell and backing use Realistic. Read [MODEL_GBA_SP.md](MODEL_GBA_SP.md)
for provenance, registration, native feed/lid checks and documented uncertainties.
This changes the GBA shape revision. The library rebake and installation are
now complete, including all 198 GBA faces; see the deployment record below.
No pipeline code is changed.

The subsequent [DS lid slice](MODEL_DS_LITE.md) changes the console and its
closed idle derivatives. DS card geometry, label-down rear feed, hero image,
label JSON, shape revision, shell and backing stay unchanged. Combined native
card/lid triangle checks cover seating while the lid closes. Shelf-face rebaking
is not needed for this DS-only follow-up.

15 October 2026; branch `models/gbc-gba-exemplars`; receiving commit `a41b5ff`
(appearance options). User request: make all the new cartridges now; keep the
remaining consoles until their own accurate models are made. Nine physical
media replace the extruded shelf-outline slab for every remaining cartridge or
card system. They are original reference-measured geometry, not scans, and are
not claimed 100% accurate.

SNES console follow-up: [MODEL_SNES.md](MODEL_SNES.md) replaces both procedural
SNES housings with licensed authored geometry and physical slot mouths. Their
cartridges retain these original physical envelopes, now at the console's uniform
1.6 / 1.55 native units/mm with no vertical stretch. Other remaining console
housings keep their earlier fit corrections until their own accurate model slice.

| Variant | Console / mesh | Hardware |
|---|---|---|
| `snes` | `snes/media` | PAL / Super Famicom Game Pak |
| `snes-us` | `snes-us/media` | North American SNES Game Pak |
| `nes` | `nes/media` | NES Game Pak (front-loader) |
| `n64` | `n64/media` | Nintendo 64 Game Pak |
| `md` | `md/media` | Western Genesis / Mega Drive cartridge |
| `md-jp` | `md-jp/media` | Japanese Mega Drive cartridge |
| `md-ea` | `md/media-ea` | Electronic Arts cartridge (taller, yellow grip) |
| `nds` | `nds/media` | Nintendo DS Game Card |
| `pico8` | `pico8/media` | Pico-8 fantasy cartridge (invented hardware) |

## Source decision

The CGB cartridge and UMD precedent applies: complete original geometry where
no suitable licensed authored recreation exists. Searches of Sketchfab,
OpenGameArt, Printables/Thingiverse and Wikimedia found no downloadable, CC BY,
complete authored recreation for these cartridges. A CC BY 4.0 OpenGameArt
"SNES-inspired" cart is a 216-triangle textured prop, not this hardware;
Sketchfab's SNES/NES entries are a controller and a photogrammetry scan (scans
are rejected); 3D-print shells were found only for NES/Famicom with unverified
fit. Sketchfab downloads would also need the user's sign-in. No downloaded mesh,
photograph, scan, texture, logo or game art is used or shipped.

Inspection references (viewed only, never shipped or traced): Wikimedia Commons
[PAL SNES rear/bottom](https://commons.wikimedia.org/wiki/File:SNES_Cartridge_PAL.jpg),
[Super Famicom front](https://commons.wikimedia.org/wiki/File:SFC_Super_Mario_World_cassette_20090828.jpg),
[PAL/US bottoms](https://commons.wikimedia.org/wiki/File:SNES_Cartridge_Comparison_bottom.jpg),
[US front](https://commons.wikimedia.org/wiki/File:MACS_version_1994_cartridge.jpg) and
[rear](https://commons.wikimedia.org/wiki/File:MACS_version_1994_cartridge_rear.jpg),
[N64 front](https://commons.wikimedia.org/wiki/File:N64-Game-Cartridge.jpg) and
[rear](https://commons.wikimedia.org/wiki/File:MajorasMaskBack.jpg),
[NES Game Pak](https://commons.wikimedia.org/wiki/File:NES-Cartridge.jpg) and
[DS card rear](https://commons.wikimedia.org/wiki/File:Nintendo-ds-cartridge.jpg).
Commons has no standard Genesis/Mega Drive cartridge photograph; those shells
follow the shelf drawings, which were checked against LaunchBox cart photos.

Each front silhouette and label well is the project's **own shelf drawing**
(`tools/themebuild/assets/*.svg`, MIT, previously checked against reference
photographs), mapped onto the published physical envelope. The shelf face and
the 3D shell therefore share one outline and one label crop, and the baked ROM
label lands exactly in the recess. Thickness, edges, grips, seams, screws, rear
recesses and connector openings are original geometry from the card below.

## Reference card

Physical mm; x right, y up, z towards the label face. A manufacturer/standard;
B calculated; C published secondary or photographic estimate; D concealed or
unverified fit. Exported precision does not promote a C/D value.

| Variant | Envelope W × H × T | Confidence and source |
|---|---|---|
| snes | 130 × 86 × 20 | C: [Wikipedia SNES Game Pak](https://en.wikipedia.org/wiki/Super_Nintendo_Entertainment_System_Game_Pak) PAL/JP; PAL and Japanese shells "nearly identical" |
| snes-us | 136 × 88 × 20 | C: same article, NTSC |
| nes | 120 × 133 × 19 | C: 120 × 133 from [iFixit](https://www.ifixit.com/Device/NES_Cartridge) / Wikipedia; thickness sources give 17–20 mm, 19 used (±1.5) |
| n64 | 116 × 76.6 × 18.5 | C: [Wikipedia N64 Game Pak](https://en.wikipedia.org/wiki/Nintendo_64_Game_Pak) (iFixit's 89-mm height conflicts and is not used) |
| md / md-jp | 109 × 70 × 17 | C: hobbyist caliper measurement (Western); JP footprint assumed equal (D) |
| md-ea | 97 × 89 × 17 | C: hobbyist caliper measurement of an EA cartridge |
| nds | 33 × 35 × 3.8 | B/C: [Wikipedia Nintendo Game Card](https://en.wikipedia.org/wiki/Nintendo_Game_Card) |
| pico8 | 60 × 76.875 × 6 | Original: invented hardware at the 160:205 cartridge aspect |

Landmarks (positions C ±1 mm after mapping; forms from the photographs):

- SFC/PAL: curved top, five edge notches per side, two lower front seams, a long
  finger slot with a raised middle third, two front screws; rear framed label
  area with two side seams and two moulded holes; 4 + 23 + 4 edge contacts.
- US: centre spine 2 mm proud of the side wings, six grip bands per wing, a
  small boss under the label, the broad lower finger recess with two vertical
  ridges, two screws on the wings; rear full-width bands, label recess, embossed
  oval wordmark and the two lower lockout slots; 23 edge contacts.
- NES: ribbed grip channel with its deeper upper pocket, lower grip recess,
  insertion arrow, top notches, stepped connector end; rear label recess and four
  top finger ribs; 36 contacts.
- N64 (refined 16 October 2026 against the Evan-Amos front photograph and a
  NUS-EUR-1 rear): arched crown, two parting lines framing the side strips, a
  label recess filling the panel between them (65.7 x 61.7 mm), short shoulder
  notches at the lower outer corners; rear embossed oval wordmark under the
  crown, two hex screws at the tops of the parting lines, an 86 x 42 mm label
  recess and two corner notches open to the lower edge; 25 contacts. The
  earlier tall front finger recesses and raised rear grip band are not on the
  real shell and were removed.
- Western Genesis rounded side grips; Japanese grip rails with ribs; EA left
  shoulder rail and recessed yellow grip; 32 contacts each.
- DS: side notch, front arrow and groove; rear embossed oval wordmark and the
  17-contact bay with separators, open to the connector edge.
- Pico-8: rear grip ridges and an open 16-contact edge (invented hardware).

Original details, all D (concealed or unverified): label recess depths .5 mm
(.2 DS, .18 Pico-8); rear label recesses .3–.4 mm; connector openings and
board/finger counts (SNES 31, NES 36, N64 25, MD 32 per side; Pico-8 16);
2-mm connector walls; screw sockets.

Front mapping distortion (physical vs drawing aspect): SNES PAL 2%, US SNES
6%, DS 3%, the others ≤1.4%. Round features keep the mean scale.

## Native integration

`tools/consolebuild/media.py` builds every variant and generates
`tools/slotlaunch/media-specs.h`. `models.py` exports `media.mesh` (or
`media-ea.mesh`), `media.glb`, `media-master.glb`, `media-physical.glb`
(metres) and `*-info.json`. One uniform presentation scale per console:
the seated width matches the existing slot target (`232/130`, `226/136`,
`196/120`, `222/116`, `224/109` units/mm), DS uses 2.75 so the 3.8-mm card fits
Slot-1, Pico-8 2.2. EA keeps md's scale and is genuinely narrower.

`cartridge_media_prepare()` chooses the shell from the **baked face's own
alpha contour**, as CGB already does for its notch: the US tab (row 1 narrower
than 85% of the widest), EA's narrow body (widest < 88% of the canvas) and the
Japanese lower edge between its grips (second-last row < 92%). The baker and the
native ROM-name rules differ slightly (World, North America), so the outline is
the reliable source. The reserved shell colours `(.5,.5,.5)` / `(.36,.36,.36)`
are tinted with plastic sampled from a plain area of the baked face, so per-game
cartridge colours (grey, black, gold, coloured N64 shells) carry over.

`cartridge_scene()` gains one branch for these variants; the DMG/CGB/AGS and
PSP paths are untouched. The hero pose matches the baked body's width and
interpolates uniformly to the physical size; positions use the physical
height. Top-loaders centre the cart's thickness on the slot; the NES Game Pak
rides 0.6 units above the tray and presses down; the DS card's face sits at
−70.4. The baked label crop is drawn in the recessed well and clipped at the
same planes as before; Pico-8 maps its complete PNG cart, credits included.
All physical media use the exemplars' finish: thin .4-unit hull, the softer
.65/.83/1 bands and the outline index subset, even on the older consoles.
Recess and groove floors take a reserved darker plastic tone (.36, tinted to
72% of the cart colour) so mouldings read head-on, where cel bands are uniform;
planar faces keep exact normals so no smoothing gradient crosses a panel.
Identifying marks are minimal original paths (the hand-authored wordmark used
on the DMG) in that darker tone: US SNES rear, N64 rear, DS rear.

## Always the 3D model: shelf and animation

User request: every cartridge is always its 3D model. Since then:

- **Shelf faces are renders of the 3D models.** `tools/consolebuild/hero-shells.sh`
  renders each cartridge mesh alone at the exact native hero pose with neutral
  plastic, 4x4 sub-pixel jitter averaged for smooth silhouettes, and measures the
  label rectangle with a green probe. The PNG/JSON pairs are committed theme-build
  inputs in `tools/themebuild/assets/hero/`. `shells.export_model()` turns them
  into the silhouette mask and one multiplicative `model.png` moulding layer; the
  on-device baker (`slotcart/render.py`) multiplies it into each game's plastic,
  so per-game colours, clear boards, glitter and EA's yellow accent still work.
  Twelve shapes: DMG (also used for GB-compatible carts), CGB, GBA and the nine
  new media. PS1 and PSP disc/UMD posters are unchanged.
- **The animation starts and ends on that pose.** The flat first/last frame is
  gone for cartridge consoles; seat 0 draws the 3D scene. The hero body fills the
  shelf body box (per-axis), then eases to the uniform physical envelope as it
  aligns. The initial cel evidence measured a mean difference of 0.2-1.1 levels
  (CGB's clear-plastic blend 3.5); current Realistic evidence is below. NES and AGS now join the console's turn as
  they align, so their hero is face-on.
- **GB-compatible carts in a CGB are the DMG Game Pak mesh**, not the old
  extruded slab, with clearance checked (zero pairs, offset control 377 pairs).
- **Every Game Pak takes the baked cart's plastic**, coloured DMG shells too
  (sampled from plain areas; clear shells sample off the board).
- The licensed Game Paks' recess is a few pixels inside the old 2D well, so their
  shapes carry a separate `label` box (baker and native crop share it, measured in
  the render). The theme's video window still uses the well: on DMG/CGB/AGS the
  delayed video preview overlaps the recess rim by up to 6 px. Updating the video
  window needs the shelf XML generator and is left for the integration branch.
- Baked faces on a device must be rebaked; the changed shape revisions trigger
  that for exactly these twelve shapes on the next baker run.

### Realistic shelf finish, 16 October 2026

**Later all-model request, implemented and installed:** all twelve cartridge heroes
now use Realistic, including NES, MD/MD-JP/EA, DS and Pico-8. Their shapes,
shells and backings are regenerated; all twelve hero JSON files and label boxes
are unchanged. This supersedes the six-shape scope in the historical evidence
below. PS1 and PSP optical art/posters and every scraping module are unchanged.
The new PS1 console and all-family style support are described in MODEL_PS1.md
and MODEL_APPEARANCE.md. Baked faces stay Realistic under a Cel animation choice.

The user approved Realistic shelf faces and their installation. Six hero shapes
now use the Realistic shader: **gb, gbc, gba, snes, snes-us and n64**. The other
six still use cel; PSP is untouched. Shapes, shells and backings for those six
are regenerated. Every hero JSON, including each label box, stays byte-identical.
No label-selection, scraping, preview or shelf-XML pipeline file changed.

First, `handhelds.ags_media()` fixes the GBA shell's normals after its label-well
boolean. Rebuilding smooth moulding normals and holding planar faces flat removes
the lower-edge diagonal gloss stripe. The shader, triangle positions and material
colours are unchanged. Across 61 insert/eject samples and their composed scene
frames, 4,392 PNGs for the other families match the baseline byte for byte.
The GBA changes 243/244 PNGs in each finish. Its panel regression rejects the
old normals; its 2,682 triangles and physical envelope are unchanged (1,954 split
vertices after the normals correction).

`sh tools/consolebuild/realistic-faces-evidence.sh` proves 113 generated files
identical across forward, reordered and repeat builds, runs the full WSL suite
and builds ARM64 from cached dependencies. All 127 tests pass in WSL; Windows
passes with four platform skips. `test_cartridge_media` independently recaptures
all twelve heroes with the intended shader (exact pixels and label boxes) and
checks the first in-scene frame against the baked shelf using Realistic for
these six. Mean absolute RGB error across each cart's canvas: GB 3.98, CGB 6.52,
GBA 1.17, SNES PAL 5.75, SNES US 5.36, N64 3.25; the cel shapes range 0.04–2.57.
The 8/255 bound allows multiplicative baking, plastic sampling, clear-board
layers and resampling. It does not claim an exact match for every coloured shell.
Logs, hashes, before/after native PNGs and `handoff.json` are in ignored
`build/realistic-faces/`.

**Baked faces stay Realistic even when the user selects Cel shaded** in theme
options; only the supported animated models change with that setting.

**Installed 16 October after “install and continue”:** all **3,613 cartridge
faces**, their backings and nine plan manifests are rebaked from cached plans.
Only each plan's `[render.VERSION, shape revision]` stamp changed; chosen art,
plastic, finish and source records are preserved. Preparation uses the latest
N64 pattern generalized to all twelve shapes, including SNES's `snes-us` → `snes`
and MD-variant → `md` cache mappings. Own-label fitting uses the installed
pipeline's existing rule. Embedded Pico-8 artwork retains its special path.
There is no scan, scrape or art-network fetch. PS1/PSP optical faces are untouched.

The inspected installed pipeline files, including the differing `labels.py`,
remain byte-identical; none was shipped in the payload. Fresh snapshot with all
nine affected roots, atomic verified copies, install audit, three warm-ups,
56 installed previews, a real launch/return, preserved test data, original-data
restoration and final verification all pass. Details and exact hashes are in
MODEL_HANDOFF.md and [deployment evidence](evidence/models-install-20261016.json).
Scripts/logs are in ignored `build/deploy-models-20261016b/`; the older
`deploy-realistic` staging is superseded. Nothing was pushed or merged.

## Console fit corrections (not remodels)

The physical media are much thicker than the old consoles' thin slits, so each
receiving opening is corrected to fit, using the same uniform scale. Nothing
else about these consoles changes, and appearance options are not added to them.

Both SNES regions and the N64 have since received authored consoles with their
real openings (MODEL_SNES.md, MODEL_N64.md); this list describes the others.

- Genesis/Mega Drive (both), Pico-8 (and formerly SNES/N64): a cavity through every
  housing it crosses, 1 mm clearance a side over the thickest media envelope
  (grips/rails included), reaching below the seated cartridge, lined dark. The
  old shallow well and dust flaps, which the seated slab passed through, are gone.
  FAST booleans keep the shells' existing shading (EXACT re-triangulated the
  PAL deck's rounded shoulders and drew stray contour lines).
- NES: an internal tunnel under the cover, from the front mouth to the back,
  dark lined, so the Game Pak slides completely inside and presses down. The
  front mouth now opens down to the tray; the top door opening is unchanged.
- DS Lite: Slot-1 deepened to take the full 35-mm card, its height raised to
  12 units, the upper lip moved up 1 unit and the connector moved to the cavity end.

## Budgets

| Variant | Runtime triangles / vertices |
|---|---:|
| snes | 4,696 / 4,302 |
| snes-us | 5,716 / 4,944 |
| nes | 3,381 / 3,899 |
| n64 | 3,584 / 3,600 (refined 16 Oct; was 4,178 / 3,861) |
| md | 2,660 / 3,924 |
| md-jp | 3,514 / 5,176 |
| md-ea | 2,308 / 3,250 |
| nds | 1,944 / 2,019 |
| pico8 | 1,004 / 1,313 |

All media stay far below 15,000 triangles and within uint16. Corrected console
meshes in the original media-only slice stayed at 12,562–13,785 triangles. The
subsequent SNES replacement has its own measured detail profiles (MODEL_SNES.md).
Masters retain authored detail; no
decimation was needed for media.

## Evidence (ignored `build/media/`)

- `clearance.json`: every native media triangle against every native console
  triangle at 101 feed positions per variant (NES: slide then press; door
  excluded while open, included when closed). **Zero intersecting pairs for all
  nine variants**; deliberately offset copies collide (177–1,065 pairs). This
  does not certify hidden hardware tolerances between samples.
- `diagnostic/*/label-check.json`: bright-green label probe. All nine pass:
  visible before alignment (21,560–89,232 px), visible above the deck when seated
  on top-loaders (6,731–15,811 px), **zero pixels below the independently
  projected entry plane**, and hidden once inside (NES, door shut) or label-down
  (DS).
- The always-3D rerun preserves all **244 PSP native PNGs byte for byte**.
  DMG/CGB/AGS intentionally change 242/240/242 of 244 each for the 3D hero,
  measured recess crop and DMG tint. The earlier media-only slice matched all
  976 accepted-family captures; that earlier result is not the always-3D result.
- Determinism: all **86** generated files for the eight consoles (console and
  media meshes/GLBs/renders, info JSON, `media-specs.h`) are byte-identical
  across forward, reverse-order and repeated `-t 1` builds (`hash-*.txt`).
- Hero capture determinism: all **24** committed PNG/JSON inputs repeat byte for
  byte (`hero-hash-before.txt`, `hero-hash-repeat.txt`). The full evidence log
  ends with **exit=0**; both triangle checkers preserve their actual exit status.
- Tests: all **111** pass in WSL including POSIX gates (Windows: three POSIX
  skips); `tests/test_cartridge_media.py` covers envelopes, budgets, colours,
  the generated header, the 3D shelf masks/recess crops and shell selection. The
  ARM64 helper builds warning-clean with `tools/slotlaunch/build.sh`.
- Sheets: `before-after.png` (receiving slab vs physical shell),
  `poses.png` (insert/eject 720×480), `neutral.png` (front/rear/side/top/
  bottom/three-quarter/seated), `after/<variant>/{insert,eject}.gif`.
- One command: `wsl --exec sh tools/consolebuild/media-evidence.sh` (needs the
  receiving tree frozen in `build/media/before` with `git archive a41b5ff`).

## Rebuild

```sh
blender -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/models.py -- snes snes-us nes n64 md md-jp nds pico8
python3 -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
blender -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/check_media.py
sh tools/slotlaunch/build.sh
```

`-t 1` is required (the build refuses otherwise): multithreaded EXACT booleans
return slightly different geometry between runs. Run the packager in WSL so
generated text keeps LF line endings.

## Remaining discrepancies

1. Envelopes are secondary/caliper sources (C); Japanese Mega Drive footprint
   and every thickness detail are estimates. Not certified against hardware.
2. Physical fronts inherit the original drawings' proportions, stretched up to
   6% (US SNES) to the envelope. Shelf faces now render those meshes directly;
   the native hero matches the shelf body box before easing to physical aspect.
   Rear faces have less detail than the fronts.
3. Only three rears carry the minimal oval wordmark; no other moulded text,
   serials or regional markings. EA's yellow grip has no manufacturer mark.
   Genesis/Mega Drive shells lack photographic verification on Commons.
4. Apart from the subsequent accurate SNES and N64 replacements, the old consoles stay
   approximate (thickness stretch, generic deck). Only
   their openings were corrected; the cavities are fit corrections, not hardware
   measurements. N64 now has contact-driven spring doors (MODEL_N64.md);
   the SNES cartridge flaps remain omitted.
5. While the NES door is open the Game Pak plastic is visible inside, but its
   label is clipped at the front plane as before.
6. The original media-only slice was offline. Subsequent permanent deployment
   refreshed 3,613 cached faces, checked all media through installed blank
   previews and passed eleven real launch/return tests. See MODEL_HANDOFF.md for
   the installed helper hash, audits and rollback snapshot. This does not add
   calibrated measurements of every label-video overlay or sustained thermal fps.
