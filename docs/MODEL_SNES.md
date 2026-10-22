# PAL/Super Famicom and US SNES console models

15 October 2026, `models/gbc-gba-exemplars`, receiving commit `3a177a4`.
Hardware: full-size SNSP/SHVC-001 rounded PAL/SFC family and SNS-001 US family;
standard 130 × 86 × 20 and 136 × 88 × 20 mm Game Paks. No controller is included.
The two consoles share the existing top-loading native scene. These are measured
adaptations of authored recreations, with the uncertainties below.

## Sources and permission

| Console | Selected source | Licence | Selection |
|---|---|---|---|
| PAL/SFC | [quick_loop, “Super nintendo”](https://sketchfab.com/3d-models/super-nintendo-d42c35b117974ade8842f0964f5fd59e) | CC BY 4.0 | Separate housing, inset, controls, sockets, feet and underside; shape survives removal of decals |
| US | [Steven H. Tran (@ibbqcats), “Super Nintendo Console”](https://sketchfab.com/3d-models/super-nintendo-console-41c9dd1f5a53493cbe2e00a190150e93) | CC BY 4.0 | Editable geometry-only Rhino/STL recreation, including stepped shell, ports, bottom and controls |

The user signed in themselves in the app browser and approved each original-format
download separately. The PAL dialog advertised original DAE, 13 MB; its archive
is 14,003,400 bytes. The US dialog advertised original STL, 1 MB; its archive is
1,439,034 bytes. Original archives, extracted files, approval/license screenshots,
neutral source views and inspection scenes remain in ignored `research/snes/`.
Alternates gozdemrl and lazercar were not downloaded after both selected originals
proved usable. Neither selected source is a scan.

| Input | SHA-256 |
|---|---|
| `quick-loop-original.zip` | `834cf321deac297462ba340870ce04d5997d4330dd8e9f4e66d341bc81062438` |
| PAL `model.dae` | `6da3db0f87e7adea08654b6c4972e0ce3aeaad5b5181280c390d9584d374598e` |
| `ibbqcats-original.zip` | `4c293edea4755c597a6508cc3163bf5f855e3e2536c677c926f6b7a0be86fd63` |
| US `Super Nintendo Console Mesh.stl` | `b41d0d31496ad9a64495fdcdf3b70068382643944102e823d687134b728bd3d6` |

Prepared, image-free physical sources and full provenance are in
`third_party/models/quick-loop-snes/` and `third_party/models/ibbqcats-snes/`.
CC BY remains attached to the derived console assets through `MODEL_CREDITS.txt`
and the LICENSE exclusion. The original cartridge geometry, connector floors,
liners, replacement text paths and processing code remain MIT. No source game
textures, downloaded logos, photographs or UV images ship.

## Reference and correction card

Project axes: x right, y up, z front; physical dimensions below are millimetres.
A manufacturer/standard; B calculated; C published secondary/photo/recreation
estimate; D concealed or unverified fit. Exact exported coordinates do not improve
the confidence of a C/D measurement.

| Landmark | PAL/SFC | US | Evidence / confidence |
|---|---|---|---|
| Overall W × H × D | 200 × 72 × 242 | 203.2 × 68 × 254 | PAL A: [Nintendo technical details](https://www.nintendo.com/en-za/Hardware/Nintendo-History/Super-Nintendo/Technical-Details/Technical-Details-627042.html); US C: [dimension drawing](https://www.dimensions.com/element/super-nintendo-entertainment-system-snes), secondary target awaiting physical confirmation |
| Source at uniform target width, W × H × D | 200 × 68.6683 × 236.6405 | 203.2 × 70.6481 × 253.6595 | B from source vertices |
| Physical correction, width/height/depth | 0 / +4.8518 / +2.2648% | 0 / −3.7484 / +0.1342% | B; applied to geometry before presentation |
| Uniform native units/mm | 1.6 | 1.55 | Presentation choice; all axes including media use the same scale; `yscale=1` |
| Slot centre z / entry y | −22.7315683 / 33.67 | −18.132 / 34 | C, source opening and top surface; ±1 mm |
| Open mouth W × D | 138.4 × 22 | 139 × 22.5 | C/D; source openings about 138.4 × 21.64 / 137.5 × 20.48, slightly widened/deepened for physical travel |
| Cartridge W × H × T | 130 × 86 × 20 | 136 × 88 × 20 | C, inherited [media card](MODEL_MEDIA.md); standard shells only |
| Seat depth below entry | 30 | 32 | D, concealed fit; not a measured PCB connector |
| Connector floor top | 2.42 | 0.75 | D, original liner floor 1.25 mm below cartridge bottom |
| Seated cartridge centre y / front plane z | 46.67 / −12.7315683 | 46 / −8.132 | B from media envelope and seat |
| Controls, mouldings, vents and ports | Source positions retained | Source positions retained | C, estimated ±1–2 mm; no caliper survey |
| Shell corners and local curves | Original rounded shell/inset retained | Original stepped shell retained | C, authored recreation; no claim of measured radii |

Six neutral source views were checked before integration. External inspection
references include Evan-Amos's [PAL console](https://commons.wikimedia.org/wiki/File:SNES-Console.jpg),
[US console](https://commons.wikimedia.org/wiki/File:SNES-Mod1-Console-Set.jpg),
[rear-right](https://commons.wikimedia.org/wiki/File:Nintendo-Super-NES-Console-BR.jpg)
and [rear-left](https://commons.wikimedia.org/wiki/File:Nintendo-Super-NES-Console-BL.jpg)
photographs. They remain references, never textures. The rounded PAL/SFC family
shares geometry here; region-specific printed legends and electrical labels are
not represented separately.

## Preparation, slot and rendering

`import_snes.py` has separate source-specific DAE and STL adapters. It bakes parent
transforms, centres the physical envelope, removes source images/UVs/printing,
assigns semantic parts and restores panel normals. Four engraved US text regions
(rear wordmark, both switch legends, EJECT lettering) are replaced by blank
planar patches; each patch must sit on a source plane inside its own rectangle.
The US STL is welded at one millionth of its envelope around those patches, and
its parts are whole mouldings bounded by 30° creases (`US_CONTROLS`), never boxes
of triangle centres. PAL's fixed closed flap is omitted in its
open position. Open source skins are triangle-clipped at the existing slot;
solid booleans produced false caps on those skins and are not used here.
Original black liners and a floor complete the concealed cavity.

Prepared GLBs are metres, x right/y up/z front. `models.py` imports them, adds our
small POWER/RESET/EJECT and identifying text, and uses one uniform scale from
`snes.py`. It exports editable masters, physical GLBs and native derivatives.
The old SNES 1.7 height stretch and cartridge-width fit correction are removed.
Console specs, media scales, label planes and native seat all use the same anchors.

The cartridge approaches above its real slot, aligns before descent, then travels
connector-first vertically. Its label faces front. Exported label quads clip at
the entry plane and remain visible above the deck after seating. The original
cartridge mouldings/recesses and baked plastic colour are retained. Shelf faces
remain native 3D hero renders. Scaling the SNES media changed two hero PNGs by
subpixel rasterization; their JSON label boxes and all other hero inputs stayed
unchanged. Both SNES shapes/shells/backings are regenerated from those captures.

Production motion is unchanged: insert 1.15 s plus 0.10 s hold. The base top-loader
eject value remains 1.05 s, but the receiving code already overrides it to **1.75 s
plus 0.35 s hold**, including a 0.60 s unseat beat and 22% spring release. This slice
preserves that override, the 0.063 s eject fade-in, insertion fade and independent
display layers. `offline-preview ... timed` samples the actual override; default
captures expose mechanical endpoints without hiding the seat behind black.

Both consoles support Cel shaded / Realistic and Original plus seven console
paint colours. PAL enclosure/inset panels and US upper/lower enclosures take
paint. Shared STL corner coordinates also occur on controls, so masks require
both the semantic enclosure position and its palette colour. Switches, socket
contacts, printing, media and art keep their own colours. Dense shell seams and
every US part omit expanded outline hulls; those hulls produced false creases,
dotted lines through the switches' finger recesses and a large handheld Cel
slowdown. Realistic uses the same geometry.

## Build, budgets and evidence

Blender 4.5, single thread, auto-execution disabled:

```sh
blender -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/import_snes.py -- snes research/snes/quick-loop/source/model/model/model.dae
blender -t 1 -b --disable-autoexec --python-exit-code 1 --python tools/consolebuild/import_snes.py -- snes-us "research/snes/ibbqcats/source/Super Nintendo Console Mesh/Super Nintendo Console Mesh.stl"
sh tools/consolebuild/snes-evidence.sh
```

Normal builds use committed prepared sources and require no account or research
download. `snes-evidence.sh` uses WSL's cached desktop/ARM dependencies. Review
captures, personal game images and device snapshots stay ignored in `build/snes/`.

The 15,000-triangle value is a default performance budget, not a GPU/file-format
limit. Native indices still require at most 65,535 split vertices and 600,000
indices. Three runtime profiles retain the same complete editable master:

| Model | Balanced triangles / vertices | Selected detailed triangles / vertices | Full triangles / vertices |
|---|---:|---:|---:|
| PAL/SFC | 11,382 / 11,844 | 12,535 / 13,567 | 12,535 / 13,567 |
| US | 13,289 / 10,088 | 17,161 / 12,877 | 21,716 / 22,933 |
| PAL Game Pak | 4,696 / 4,302 | Same | Same |
| US Game Pak | 5,716 / 4,944 | Same | Same |

Balanced reduces named fittings individually; it never applies a whole-console
decimate. Full skips those fitting limits and retains the source's small details.
Detailed retains the complete PAL source and gives US lower housing, controller
sockets, rear connectors and two switches limits of 6,500 / 2,500 / 800 / 600 / 600
triangles. Prepared-source budget properties describe the balanced profile;
`snes.py` supplies these explicit detailed overrides. Editable master GLBs retain
12,541 PAL / 21,737 US triangles, including degenerates omitted from native output.

`SLOT_SNES_DETAIL=detailed` is now the default. `balanced` and `full` remain
reproducible alternatives. The first full trial missed the initial 60 fps target.
Even after the outline correction and the user's relaxation to about 50 fps,
full US had a 36.02 fps Realistic eject and a 47.99 fps insert. It is rejected.
The selected detailed profile passed all 24 uncomposed production-scene runs.
These runs measured the pre-correction US model (17,370 detailed / 22,519 full
triangles); the corrected model's on-device A/B is under "US visual correction":

| Model / style | Six runs: min–max fps | Weighted fps |
|---|---:|---:|
| PAL Cel | 56.65–58.87 | 57.97 |
| US Cel | 57.00–58.87 | 58.25 |
| PAL Realistic | 57.57–59.45 | 58.62 |
| US Realistic | 56.99–58.61 | 57.74 |

Three repeats of insert and eject per console/style, with no composed-display
capture. `benchmark-snes.c` wraps only `SDL_RenderPresent` around the actual
production helper; scene, pacing, independent layer, shaders and holds remain
unchanged. These are whole-run present rates, not a promise that every frame
meets 20 ms. Maximum per-run p95 intervals were 18.70–25.35 ms. Raw intervals,
stderr, fresh native logs and audits remain under `build/snes/device-*`;
`benchmark-summary.json` records every trial, including rejected ones.

### Verification record

- `build/media/evidence.log` still ends `exit=0`: the completed always-3D slice's
  86-file determinism, 12 clearance paths, nine labels and PSP regression proof.
- Prepared source GLB/JSON pairs repeated byte for byte (`source-hash-*.txt`).
- `build/snes/evidence.log`: forward/reverse/repeat hashes for 148 generated files,
  including both media, shapes, masks, 64 appearance PNGs, headers and all 24 hero
  PNG/JSON inputs. All-media exported-triangle clearance must have zero pairs
  at 101 feed samples per variant and deliberate collision controls.
- `snes-review.sh`: independent neutral front/rear/side/top/bottom/three-quarter
  and loaded views; native 720 × 480 mechanical insert/eject and timed sequences.
  Bright-green labels expose 32,400 / 22,880 free pixels, 9,176 / 6,654 seated
  pixels, and **zero pixels below entry**. The four accepted families retain all
  **976 native PNGs byte for byte** against receiving commit `3a177a4`.
- Full suites on Windows and WSL: 117 tests (Windows three POSIX skips).
  Cached-library ARM64 production and benchmark helpers build warning-clean.
- The user authorized handheld tests. Every benchmark used a fresh verified
  snapshot with ES stopped; 312 data / 409 runtime files remained unchanged.
  Detailed benchmarks use session `slotters-snes-detailed-20261015a`.
- Real launch/return tests use temporary, hash-verified two-model assets, two
  bands, two cartridge faces and an owned selection hook. The installed newer
  `theme.xml` and scraping pipeline are untouched. Each variant is launched
  twice: uncomposed return-input observation is separate from composed-display
  capture. Actual navigation must change selection **after** the injected tap;
  the frontend's earlier restoration callbacks are not counted as accepted input.
- Fresh data/runtime snapshots preserve test changes before restoring only
  changed files. The original installed helper hash is
  `1dac9f1dfefecb150218df2014103965ff28894ffc0d5988bcf6bb2b54660c14`;
  executable permission is checked separately. Those initial temporary tests
  restored their original installation; the later permanent deployment is below.
- Selected-profile real tests are in session
  `slotters-snes-real-detailed-20261015a`. Uncomposed inserts measured 55.2 PAL /
  55.0 US fps; uncomposed ejects both measured 50.6 fps. Separate composed-display
  captures measured 53.6 / 48.5 fps insert and 52.3 / 54.0 fps eject. Capturing
  display layers is a different workload; all trial values remain recorded.
  Return taps occurred 0.403 s PAL / 0.419 s US after motion completion, with
  selection callbacks 0.111 / 0.087 s after the actual tap. These observations
  include probe overhead and do not establish an exact readiness boundary.
  Final audit: **314 data / 409 runtime files, zero changed/new**; owned selection
  hook removed, original helper executable, ES running and no game active.

### Permanent deployment follow-up

The user subsequently requested installation for normal use. The selected
detailed models, all six models' appearance assets, always-3D helper and
cartridge shapes are now installed. The newer device theme was preserved with
surgical additions for the two appearance controls. 3,613 faces were regenerated
from their exact cached artwork plans, colours and finishes; no label discovery,
network fetch, scraper or protected pipeline modification was involved.

The current helper hash and the fresh rollback snapshot are in MODEL_HANDOFF.md.
Deployment manifests and evidence are ignored in `build/deploy-snes/`. The old
`1dac9f…` helper hash above identifies the pre-deployment test baseline, not the
current installed helper.

The installed helper passed 28 blank insert/eject previews, two blue Realistic
SNES previews and eleven real launch/return checks across all updated systems.
SNES US/PAL ejects measured 53.4 / 53.8 fps in these uncomposed installed tests.
The initial 100-ms synthetic exit was missed; repeating with a longer boot wait
and 250-ms chord passed without production changes. Actual navigation was checked
after the injected post-motion tap, excluding earlier restoration callbacks.
Test data is preserved, original settings/saves restored, temporary hook removed,
and the installed deployment retained. Post-install test audit: 325 data / 640
runtime files, zero changed/new. The style and colour controls were also visibly
verified in the live frontend's Theme Configuration menu.

### US visual correction, 15 October 2026

After the deployment the user reported glitches on the US console's surfaces and
controls. Four causes were found and fixed in `import_snes.py` / `snes.py`:

1. **Flipped faces.** Blank text patches rebuilt the STL as separate triangles,
   and a fixed 1e-8 weld cannot reconnect coordinates in the hundreds. Normal
   repair then oriented single triangles arbitrarily: black slivers on the right
   side and stray outline strokes. The weld is now relative to the envelope. PAL
   keeps the metre-scale weld; its prepared source is byte-identical.
2. **Sawtooth part boundaries.** Parts were boxes of triangle centres on one
   closed skin. Switch inner ends stayed housing grey, controller-socket grey
   spread over the front blocks in teeth, and the whole rear wall was coloured as
   connectors. Parts are now whole crease-bounded mouldings: the complete
   switches, the raised EJECT lever, the D-shaped ports and three rear sockets.
3. **Floating patch.** The fourth blank patch matched a plane elsewhere at
   z = −4.5 and added a quad 2.5 mm above the lever, which carried the red
   "SUPER NINTENDO" text. It now blanks the real EJECT lettering on the lever.
4. **Colours and legends** now follow SNS-001 photographs: POWER and RESET
   share one purple with lavender legends centred on the switches; EJECT is a
   darker grey lever with a light legend; "SUPER NINTENDO" is moulded grey on the
   left of the sloped cartridge-bay front, following that slope.

The switches' outline hull is also suppressed (dotted lines, item above). The
detailed US model is now 17,161 triangles / 12,877 vertices, under the measured
17,370 profile, and draws no outline-hull triangles (previously 1,200).

Installed on the handheld the same evening (38 hash-verified runtime files,
rollback copy in `slot-dev/sessions/slotters-us-fix-20261015`; scripts and
results in ignored `build/deploy-us-fix/`). Ten installed blank previews loaded
the mesh and paint mask in Cel/Original, Cel/Red and Realistic/Blue. An on-device
A/B with the same helper alternated old and new meshes: once warm, new Cel ran
57.0–58.7 fps (old 56.8–58.2) and Realistic 58.9 (old 57.7). Runs in the first
seconds after stopping the frontend dip to 35–41 fps for **either** mesh; let
preview timing settle before comparing. Evidence (`build/snes-fix2/`): 148 files repeat forward/reverse/
repeat; all nine media paths have zero clearance pairs with positive controls;
ARM64 is warning-clean; 118 tests pass in WSL and Windows (three POSIX skips).
All 244 PAL native frames are byte-identical. `test_us_controls_are_whole_source_mouldings`
fails on the previous source (32.5 mm sockets, a 203-mm "connector" wall).

## Remaining discrepancies

1. Slot mouth estimates have about 1 mm uncertainty; seat depth, concealed liner
   and floor are fit geometry. Validate against a measured real console before
   describing them as exact connector geometry.
2. PAL and SFC share shell geometry and generic original identifiers. Regional
   logos, underside electrical legends and serial labels are omitted. Small text
   positions/sizes are C estimates and can be hard to read at 720 × 480.
3. Port interiors, eject mechanisms, screws and local moulding radii come from
   recreations, with no detailed dimensional survey. The US source's planar text
   patch boundaries can leave small shading seams. The fixed-open dust flaps and
   static eject controls do not simulate internal mechanics.
4. Higher detail is accepted only against measured handheld performance. Short
   preview/launch tests do not prove a sustained thermal worst case or locked fps;
   composed-display capture adds overhead and is reported separately.
5. Earlier DMG/CGB/AGS shelf video-well overlap remains the documented protected
   XML-generator issue; no scraping pipeline or shelf XML generator was changed.
