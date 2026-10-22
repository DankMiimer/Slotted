# Nintendo 64 console model and Game Pak

16 October 2026, `models/gbc-gba-exemplars`. Hardware: NUS-001 console with a
standard NUS-006 Game Pak (116 × 76.6 × 18.5 mm). No controller is included.
The console replaces the earlier procedural housing with its 2.3 height stretch;
the Game Pak stays original MIT geometry and was refined against photographs.
This is a measured adaptation of an authored recreation, with the uncertainties
below.

## Sources and permission

| Part | Selected source | Licence | Selection |
|---|---|---|---|
| Console | [Joseph Rohm, “Nintendo 64”](https://sketchfab.com/3d-models/nintendo-64-0bec1e1ed1bf4a96af858008b72437a3) | CC BY 4.0 | Housing, lower shell, memory-expansion door, bay grille, sliders, ports, feet and rear bay are modelled geometry; proportions within 2.5% of NUS-001 once de-rotated |
| Game Pak | Original Slotters geometry (`media.py`) | MIT | User choice; see below |

From the CC BY search, the user rejected all but two console candidates on
sight, approved both original-format downloads (Joseph Rohm 41.1 MB, Ethanboor
26.2 MB) and chose Rohm's after neutral clay views. Ethanboor's archive stays
in ignored `research/n64/` unused. Both bundled cartridges were rejected (a
180-triangle block and a featureless shell). The user suggested Chris
Sweetwood's “Nintendo 64 Cart”, which is **CC BY-NC-SA** with its detail in
photo textures; offered that licence choice, the user chose to refine our own
MIT Game Pak instead. Nothing was downloaded from it.

| Input | SHA-256 |
|---|---|
| Rohm `nintendo-64.zip` (original format, 41,126,874 bytes) | `93ae3ae6e3014e3c9cc1679da3dd9ebe16a44af2e0d00c4f4082a19ac557abad` |
| `N64_with_controller.fbx` | `fe7061e660f2e4f256e1d4956f5065c1310a6e3b4b655128290971321ac7f802` |
| Ethanboor `nintendo-64.zip` (unused, 26,182,768 bytes) | `04e3e80125209d4f423b9bd887a704e4c67f85b0e4f9b260be77a4e60b996ebf` |

The prepared, image-free physical source and provenance are in
`third_party/models/josephrohm-n64/`. CC BY stays attached to the derived console
assets through `MODEL_CREDITS.txt` and the LICENSE exception. The Game Pak, slot
liners, connector floor, front badge and processing code are MIT. No source
textures, normal maps, photographs or logos ship.

## Reference and correction card

Project axes: x right, y up, z front; millimetres. Confidence: A manufacturer or
standard; B calculated; C published secondary, photograph or recreation estimate;
D concealed or unverified fit.

| Landmark | Value | Evidence / confidence |
|---|---|---|
| Overall W × H × D | 260 × 73 × 190 | C, published NUS-001 dimensions |
| Source after de-rotation, at uniform target width | 260 × 71.93 × 185.43 | B; Maya group yaw −16.37° removed |
| Physical correction, width/height/depth | 0 / +1.48 / +2.46% | B, applied to the geometry |
| Uniform native units/mm | 1.5 | Presentation choice; all axes and the Game Pak; `yscale=1` |
| Source dust-flap opening | 97.8 wide × 27.6 deep, centre z −61.7 | B from the source; Rohm's own cart is 87 mm wide |
| Bay floor / slot width after correction | 120.5 / 118.5 | D: widened so the 116-mm Game Pak passes with 1.25 mm a side |
| Slot centre z / entry y | −61.7 / 10.87158 | B/C: entry now follows the actual source flap surface, rather than the old 3.6-mm bay-floor estimate |
| Opening depth | 27.9 | D: clears the 27.636-mm source door pair, with concealed hinge relief below the rim |
| Seat depth below entry | 27 | D: lower edge y −16.128, .5 mm above the new connector floor |
| Multi-out | moved 14 mm rearward | D: the source places it 17–35 mm inside the rear bay, in the widened slot's path |
| Front badge | 44 × 22 plate, in the source's 0.7-mm recess | C, photograph position between ports 2 and 3 |

References, never textures: Evan-Amos's [console set](https://commons.wikimedia.org/wiki/File:N64-Console-Set.png),
[rear-right view](https://commons.wikimedia.org/wiki/File:Nintendo-64-Console-BR.jpg),
[Game Pak front](https://commons.wikimedia.org/wiki/File:N64-Game-Cartridge.jpg) and a
[NUS-EUR-1 rear](https://commons.wikimedia.org/wiki/File:MajorasMaskBack.jpg).

### Bay correction

The source's cartridge bay is about 20% too narrow for a real Game Pak; every
other housing proportion is within 2.5%. `n64.BAY` widens only the bay, in source
units about the slot's centre line: |x| ≤ 3.3 scales by 1.232, the flat shoulders
out to 5.6 take up the difference, and the weight ramps to zero in front of the
bay and below the rear connectors. The warp is continuous and monotonic (tested),
so no seams open. The slot is clipped open through the bay floor without booleans,
and original black liners and a connector floor complete the cavity.

## Preparation, integration and appearance

`import_n64.py` bakes the yawed Maya group into its own frame, drops the
controller, cable and bundled cartridge, retains the two source dust flaps, applies
the bay correction and per-axis physical scale, welds split corners, assigns 15
semantic parts and the N64 palette, and rebuilds panel normals. Images, UVs and
normal maps are removed. The x origin is the slot's centre line; the source
housing is 0.8 mm asymmetric.

Independent reinspection on 16 October found the omitted flaps are two adjacent,
mostly horizontal 20-triangle leaves in the source frame, rather than parked
open as previously described here. Each is about 97.819 × 13.762 × 1.690 mm in
the existing physical registration and inherits the undersized source bay.
The flaps are now widened with the bay and fitted to **118.1 mm** inside the
118.5-mm opening. Their outer-edge pivots and y/z sections are recorded in
`source.json`; the pivot through mid-thickness is a fit inference. See
[MODEL_INDEPENDENT_RESEARCH.md](MODEL_INDEPENDENT_RESEARCH.md) for the measurements,
replacement-source licence check and remaining OEM-fit uncertainty.

`n64.py` holds the physical anchors and adds the liners, connector floor and the
untextured front badge (black plate, white “NINTENDO 64”). `models.py`,
`media.py`, `consoles.py` and `review_media.py` read its specs alongside the SNES
ones. The Game Pak shares the console's 1.5 scale; the native seat comes from the
same anchors. Production motion is unchanged: insert 1.15 s + 0.10 s hold, eject
1.75 s + 0.35 s with the 0.60-s unseat beat.

Cel shaded / Realistic and Original plus seven console colours are supported.
Upper and lower enclosures and the memory-expansion door take paint; sliders,
ports, grille, feet, rear connectors, badge and media keep their colours.
Every part omits the expanded outline hull: on charcoal it only added false
creases at the dense seams, ribs and port mouldings. The shelf band dispatch
includes the `n64h` alias.

Runtime console: 7,082 triangles / 7,880 vertices, well under the 15,000 default
budget, so no detail profile or reduction was needed. Game Pak: 3,584 / 3,600.

### Contact-driven spring doors (installed 16 October)

The visible opening now follows the actual closed door plane. Under its rim,
a 1.2-mm front/rear relief lets the panel thickness swing below the enclosure;
the original black liners sit outside that swept volume. Preparation clips the
final upper-enclosure tessellation after planar dissolve as well: dissolve had
introduced a diagonal spanning the concealed relief, caught by collision checks.

The native mesh keeps two independent hinged index ranges in its existing
`SCTOON2` buffer. `n64-data.h` is generated from their exported ranges and source
sections. `n64-flaps.h` clips each rotated section against the moving cartridge's
side plane and solves for the smallest downward opening that clears its lower
edge. A .25-mm running clearance is a fit choice. The two leaves open to about
74.7/75.0 degrees when seated, close behind the withdrawing cartridge and stay
closed while it is clear of the console. These are contact-fit results, not
claimed OEM stop angles or measured spring timings. Other scene timings stay
unchanged. Both finishes, idle bands and body sprites include the closed doors.

`check_n64_flaps.py` checks the actual exported triangles at **101 feed/reverse
positions**: zero cartridge/body, cartridge/leaf and body/leaf intersections.
Deliberately closed leaves intersect the seated cartridge in **146 / 184 pairs**,
so the check has positive controls. The standard nine-media checker also passes;
its N64 wall-offset control finds 167 pairs. `n64-evidence.sh` repeats preparation
twice and **90 generated files** across forward, reverse and repeat builds.
Native captures for both styles and directions, including actual eject timing,
are under ignored `build/n64-flaps/`. The cart mesh, hero, label boxes and shelf
face are unchanged by this bay/door update.

All **133 tests pass in WSL**; Windows passes with five platform skips. The
ARM64 helper builds warning-clean. The initial full-suite run exposed an old
generic assertion that only NES/PSP could have moving ranges; its registry now
includes N64 and PS1, and both platform suites pass after that correction.
That model slice's local helper SHA-256 was:
`dfc9c7e5a046df43f28cc1d17d4637ad581914f2c1a5bab974e4c1067ea8e2da`.

The complete model rollout is now installed with the later shared helper;
MODEL_HANDOFF.md records its hash and fresh rollback snapshot. All 329 N64 faces
were rebaked from cached plans as part of the 3,613-face library update. Realistic
installed insert/eject previews pass at **56.8/58.1 fps**. The real frontend-API
N64 launch and controller return pass at **55.8/54.0 fps**, with no problems;
test changes are preserved and original data restored with zero audit differences.

## Game Pak refinement

Compared with the NUS-006 photographs, the earlier MIT shell had a narrow front
label recess, tall front finger recesses and a raised rear grip band that the
real shell does not have, and its rear screws and notches were misplaced.

- Front label recess widened to fill the panel between the parting lines:
  65.7 × 61.7 mm (was 55.7 × 61.7). The shelf drawing's label well, the baker's
  crop box and the native label plane all follow it.
- Front lower corners: short shoulder notches at the outer corners (about
  13 × 9 mm), replacing 24-mm-tall recesses.
- Rear: no raised band; the embossed oval wordmark sits under the crown; the two
  screws sit at the tops of the parting lines (±37 mm, was ±47.5); the rear label
  recess is 86 × 42 mm; the corner notches moved to the outer corners (±49.5 mm).

Because the label box changed, every N64 shelf face must be rebaked from its
cached plan when this is installed. The shelf video window still comes from the
protected shelf XML generator and keeps its old rectangle, which lies inside the
new label recess.

## Evidence from the original N64 slice (before spring doors)

`sh tools/consolebuild/n64-evidence.sh` (WSL, Blender 4.5 `-t 1`) prepares the
source twice and compares it with the committed files, builds three times
(including a different console order), checks exported-triangle clearance for all
nine physical media, builds the ARM64 helper and runs the unit suite.

- Prepared source GLB and JSON repeat byte for byte.
- 89 generated files (console, shapes, hero inputs, shell, backing, appearance,
  headers and specs) are identical across forward, reverse (`snes-us n64`) and
  repeat builds.
- Clearance: zero intersecting pairs at all 101 N64 feed positions, with 182
  pairs in the deliberate collision control; every other medium is unchanged at
  zero. The first build collided only when fully seated, which set the 27-mm seat.
- Label probe (`offline-preview … insert diagnostic`): 39,576 free label pixels,
  4,572 visible above the deck when seated, zero below the entry.
- 125 tests pass in WSL; Windows passes with three POSIX skips. `test_model_n64`
  covers the envelope and uniform scale, the open slot across the full Pak width,
  the bay warp's locality and monotonicity, paint isolation, provenance and the
  label recess. ARM64 builds warning-clean.
- Only N64 assets and the N64 rows of the shared headers, specs, appearance
  manifest and shelf dispatch changed; no other family's generated file changed.
- Review images are in ignored `build/n64/`.
- Handheld trial, uninstalled (16 October): the new ARM64 helper and N64 assets
  ran from a temporary `/tmp` tree linked to the installed theme, which stayed
  untouched; frontend restarted afterwards. After three warm-up runs, N64 blank
  previews measured 56.3–58.8 fps (Cel/Original and Cel/Red inserts and ejects,
  Realistic/Blue 57.8–58.8); mesh and paint mask loaded in every run. US SNES with
  the same new helper measured 56.6–58.0 fps (unchanged). Script and results:
  ignored `build/deploy-n64/`.

## Original installation on the handheld, 16 October 2026

At the user's request the N64 was installed for normal use.

- Fresh hash-verified rollback snapshot, taken with the frontend stopped:
  `/userdata/system/slot-dev/sessions/slotters-n64-deploy-20261016a` (972 data
  files including the N64 shelf faces, 640 runtime files).
- 49 runtime targets: the N64 model, Game Pak, paint mask, body and band, shape,
  shell, backing, 32 appearance images, the appearance manifest and shelf
  dispatch, specs, credits and the new helper
  (`97d7fbcd9cbf5cd7c301505e08f50573bbc203af6a18dd23b407da4d12ae2bf2`).
- All 329 N64 shelf faces (292 label scans, 32 text labels, 5 logos) and their
  backings were re-rendered on the device from their cached plans with the new
  shape; no scanning, scraping or network fetch. The plan manifest records the
  new shape revision, so the baker treats them as current. Label scans previously
  squeezed into the narrow portrait well now keep their natural proportions.
- Every target was verified before and after; the audit found no other change.
- Installed blank previews after warm-up: N64 57.5–58.2 fps (Cel/Original,
  Cel/Yellow, Realistic/Original and Realistic/Blue; insert and eject), US SNES
  57.4, DMG 58.4. Mesh and paint mask loaded every time.
- A real launch of 007: The World Is Not Enough (USA) from the frontend: insert
  54.6 fps, eject 54.7 fps on return, no load problems. A separate fresh snapshot
  (`slotters-n64-real-20261016a`) preserved the 5 changed and 2 new test files;
  the original data was restored and audited with zero differences.
- Records and scripts: ignored `build/deploy-n64/`.

## Remaining discrepancies

1. The bay width, opening depth, seat depth and connector floor are fit
   corrections, not measurements of a real console. Validate against a measured
   NUS-001 before calling them exact.
2. The rear power-supply bay is modelled empty and opens into the hollow shell;
   only the slot lining closes the view behind the slot. The removable power
   supply is not modelled. The multi-out position is a fit estimate.
3. Rohm's detail relied partly on normal maps, which are removed: vent ribs,
   side grilles and port mouldings are simpler than the textured original.
4. The badge is a plain plate with lettering; the coloured N cube and the
   POWER/RESET legends are omitted.
5. The shelf video window keeps its old rectangle (protected generator).
