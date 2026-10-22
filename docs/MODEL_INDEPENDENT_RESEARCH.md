# Independent hardware research — 16 October 2026

This follows the initial [research audit](MODEL_RESEARCH_REVIEW.md). The user
asked for sceptical checks **and independent research**, so this pass obtained
original model archives, inspected and rendered their actual geometry, assembled
the supplied CAD, read manufacturer manuals and ran a controlled native shader
experiment. It resolves several earlier unknowns and changes the PS1 source
recommendation. It is research, not a claim that the requested models are done.

All persistent project work stayed in `Slot_ESDE-next-models`, branch
`models/gbc-gba-exemplars`. Production meshes, renderer, scraping pipeline and
handheld were unchanged. Large original archives and scratch evidence are local,
ignored files under `research/hardware-review/independent/` and
`build/research-review/`. The original external package remains unchanged.

## Findings that change the implementation

### PlayStation: inspect one complete source before combining models

Downloaded the actual originals through Sketchfab's normal download UI, then
opened them in Blender 4.5 with automatic scripts disabled. Neutral Workbench
views use one grey material and no image textures, so geometry is visible
without the source's texture and lighting presentation.

| Original source, CC BY 4.0 listing | Actual inspection | Decision |
|---|---|---|
| [dark_igorek, Sony PVM-1341 / PlayStation](https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245) | Whole scene: 24 mesh objects, 240,414 triangles. The `ps1` collection alone: **7 objects, 64,717 triangles**. Separate `ps1_cap`, `body_inner`, `laser_disc_rotor` and `laser_plate`, plus housing/details/ports. | Leading candidate to evaluate as one coherent source. The supplied report's claim that it lacks an interior is false. No need to assume a second source must supply it. |
| [Juan Galindo / Sheyk940, PlayStation 1 with Crash Bandicoot Disc](https://sketchfab.com/3d-models/93dbf6c499d84ae2ae2c7b07aa537a11) | Original FBX: **262 mesh objects, 737,772 triangles**, including accessories. Two animation actions; neutral mid-animation render shows the open lid and disc in the well. | Useful alternate and motion reference. Its much larger scene is not proof of greater hardware accuracy, nor is it the only candidate with an interior. |

These are source triangle counts before production processing, not device cost
estimates. dark_igorek's source is static with its lid open. Its separate cap is
useful for rigging, but object origin, open pose and grey render do not certify a
real hinge axis, stop angle, closed fit or exact hardware revision. Neither
candidate is approved for direct unexamined export. Ceki and krittsky originals
were not acquired in this pass.

Independent primary reference: Sony's **SCPH-5500/5501/5502/5503 service manual**,
PU-18, manufacturer-authored and [archived here](https://psx.arthus.net/docs/service_manuals/SCPH-5500_5501_5502_5503.pdf).
The saved 99-page scan was visually checked, rather than relying on empty OCR:

- **PDF page 2** confirms **270 wide × 60 high × 188 deep mm** for the 550x
  variants. The external report's envelope is correct here.
- **PDF page 65, printed page 67**, shows the exploded main block, including
  upper cabinet, disc-lid assembly and optical assembly. Its regional part list
  distinguishes cabinets and PIO covers. Use this to check one selected variant;
  do not mix exterior details from different revisions without documenting it.
- These illustrations are not dimensioned pivot drawings. They do not verify
  the report's precise lid centre, angle or travel timings.

Next source check: compare neutral front/rear/underside and closed-lid geometry
against the selected 550x variant; verify port layout, vent pattern, buttons,
lid outline, spindle and laser placement. Register the closed lid to its rim
before deriving its motion. Then optimize and measure the native result at
720 × 480. Keep source textures and game art out of the production conversion.

### N64: usable existing source parts, unverified bay dimensions

The existing Joseph Rohm source already contains **`slot_cover_1` and
`slot_cover_2`, 20 triangles each**. Our importer explicitly omits them. In the
de-rotated console frame they form two mostly horizontal adjacent leaves; the
older MODEL_N64.md description of them as parked open was inaccurate.

Measured in the project's existing physical registration, each unwarped source
leaf is approximately **97.819 wide × 13.762 deep × 1.690 thick mm**. The shared
top is near y = 10.872 mm and their seam near z = -61.7 mm. These are **file
measurements**, not OEM dimensions. They inherit the source's undersized bay
and cannot simply be restored unchanged for the current 116-mm Game Pak.

The current **118.5-mm opening, 120.5-mm bay floor and seating assumptions remain
fit estimates**. The external package repeats them; that is not independent
confirmation. Correct the bay and establish the leaf axes/clearance together.
Drive door opening from cartridge contact and keep both leaves clear while the
Pak is seated; exact spring timing and maximum rotation still need evidence.

The [replacement doors listing](https://www.printables.com/model/220163-n64-replacement-cartridge-doors)
was independently opened in a browser: **HumbleBazooka, CC BY-NC-ND 4.0**, not
the author/licence in the deep dive. The supplied front/rear STLs each form one
connected component. Their full widths, 147.4 and 139.4 mm, include protruding
features; they are not blade widths. Do not use those full bounds to set the
console opening or derive production meshes from this restricted replacement.
The already selected Rohm source is CC BY 4.0; its flap geometry is available
for examination under that source's existing attribution.

The [pdaxrom N64cart repository](https://github.com/pdaxrom/N64cart) explicitly
describes a custom RP2040 flash cartridge. Its supplied shell's 116 × 65-mm
face plane is not evidence for the OEM NUS-006 crown height. This resolves the
reference-type uncertainty in the first audit.

### GBA SP and Game Pak: measurements without false OEM precision

Nintendo's [SP technical data](https://www.nintendo.com/en-gb/Support/Legacy-system/Technical-data-619375.html)
confirms the closed envelope **84.6 deep × 82 wide × 24.3 high mm**. Preserve the
manufacturer envelope and the already correct label-down insertion.

The [Dave Parker / Dave replacement CAD listing](https://www.printables.com/model/190861-gameboy-advance-cartridge-gba-cart)
was independently checked in the browser: **CC BY 4.0**. The author describes
fit tests in GBA, SP and DS Lite; those are useful replacement-fit claims.
The linked [BOSL dependency licence](https://github.com/revarbat/BOSL/blob/master/LICENSE)
is BSD-2-Clause. Neither establishes Nintendo's mould dimensions.

Using the SCAD's own commented fit-test assembly—top rotated 180 degrees about
Y, then translated to z = `(2 - 1.3 + 3.8) + 1.4 + 1.8 = 7.7`—the two supplied
STLs combine to **60 × 34.400002 × 7.7 mm**, 2,360 triangles. The report's 9.4-mm
assembled thickness does not follow from that transform. The label cutout is
44 × 23 × .4 mm with `fillet=1`; that is the replacement design's feature,
not a verified OEM label radius. No shelf label boxes were changed.

Also obtained the original [Vxcl cartridge](https://sketchfab.com/3d-models/gameboy-advance-cartridge-38c1e6702e5d4f21af1d0930689b1d10):
three mesh objects, **1,524 triangles** (1,370 shell, 44 PCB, 110 screw).
Neutral views confirm an actual label recess and bevel geometry. They also
show visibly simplified bevels; the creator acknowledges the missing wordmark.
It is a reference candidate, not an accurate drop-in answer. Its unregistered
Blender units must not be treated as millimetres. The ewaldc2028 original remains
uninspected; its listing alone cannot settle which candidate is better.

The existing prepared AGS source has separate display and large/small hinge
parts, but its flattened mesh origins are zero. The report's pivot coordinates
cannot be copied into those objects. Derive the hinge from its cylindrical
geometry and register lid/base in a closed pose, then check the slot lip and
cartridge clearance. A new cartridge should be judged by silhouette, stepped
thickness, grip/crown, recess, seams, back and connector, in neutral views.

No numeric SP lid detent angle is promoted to verified hardware data here.
[iFixit's reshell guide](https://www.ifixit.com/Guide/How+to+Reshell+Your+Game+Boy+Advance+SP/137582)
provides first-hand hinge/cap disassembly context, not a dimensioned rig. The
precise angles and motion timestamps in the supplied package remain unverified.

### DS Lite: a renderer restriction is a demonstrated contributor

Nintendo's official [DS Lite instruction booklet](https://assets.nintendo.eu/image/upload/v1635390384/NAL/Support/DSLiteInstructionBooklet.pdf),
**PDF page 9, printed pages 14–15**, confirms:

- DS cards insert **label down** until they click; removal uses another push
  until a click, after which the spring partially ejects the card.
- GBA Game Paks face towards the bottom and are withdrawn by hand. This is a
  different loading mechanism.

Nintendo's [DS loading instructions](https://en-americas-support.nintendo.com/app/answers/detail/a_id/3906/~/how-to-insert-and-play-a-nintendo-ds-game-card)
place opening the screen after card insertion. Lid movement can therefore be
scene choreography without pretending the lid mechanically operates Slot-1.
These sources do not establish the report's exact push/eject millimetres,
hinge stops or pivots. Keep those values unverified. The current card already
feeds label-down and the console already has twelve actual speaker holes.

Controlled experiment, **scratch copy only**:

1. Compile the current native preview harness, warning-clean with `-Werror`.
2. Copy `tools/slotlaunch` below ignored `build/research-review/`; add only `nds`
   to that copy's `console_appearance_ready()` list. Do not alter production.
3. Render the same 61 insertion poses plus their composed frames: **122 PNGs
   per capture**, same geometry, palette, camera, inputs and desktop software GL.

| Comparison | Different PNGs / 122 |
|---|---:|
| Current Cel vs current Realistic selection | **0** |
| Scratch Cel vs current Cel | **0** |
| Scratch Realistic vs current Cel | **121** |

The current DS Realistic selection falls back to Cel. Enabling the existing
smooth shader and removing outlines makes its moulding and shading more legible
in the controlled views. This is evidence for enabling and evaluating that path
first; it does not prove a complete material solution or handheld frame rate.
There is no experiment here supporting the report's assertion that a new acrylic
clear-coat shader is necessary. Lid articulation remains separate model work.

The all-model Realistic request also reaches PS1's bespoke renderer in `psx.h`.
Changing this readiness list alone will not complete that request. Separate
style support from enclosure paint eligibility, preserve accepted geometry and
check regenerated idle bands, bodies, native scenes and shelf hand-off together.

## Shader evidence and remaining unknowns

The [Khronos GLSL ES 1.00 specification](https://registry.khronos.org/OpenGL/specs/es/2.0/GLSL_ES_Specification_1.00.pdf),
section **4.5.2, printed pages 34–35**, directly supports the precision concern:
assigning an expression with medium-precision operands to a high-precision
destination does not by itself require that expression to run at high precision.
The specification's example explicitly demonstrates this. Review input and
intermediate precision, not just destination declarations.

[Arm's precision paper](https://documentation-service.arm.com/static/5eff5d5edbdee951c1cd5f20)
is useful background, not a benchmark of this animation on RG34XXSP. GPU family
numbers cannot establish our sustained frame rate. Keep material constants as
tunable hypotheses and measure on-device once deployment can safely resume.
The received UV/texture shader still does not match our position/normal/colour
mesh interface; untinted ambient and local-axis cavity terms remain unresolved.

Still missing: traceable OEM N64 bay/door dimensions, GBA slot lip/seated depth,
original-shell cartridge section measurements, and registered SP/DS hinge axes
and stop angles. Neither a replacement STL nor a precise spreadsheet fills
those gaps. Use explicit tolerances and labelled fit assumptions until there is
an actual measurement record. Animation durations are product choices unless
supported by recorded hardware observations.

## Local evidence and reproduction

Source archives are retained without modification. These names are local
research labels, not production selections:

| Archive below `research/hardware-review/independent/` | SHA-256 |
|---|---|
| `ps1-exterior/original.zip` (dark_igorek) | `0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845` |
| `ps1-sheyk940/original.zip` | `541d007e99a2e472ceea7d72e0878485d0af7abba50a75732b08e179617919a5` |
| `gba-vxcl/original.zip` | `a3a245bc89f422d4e9fe323d3d715b8c9a6507237aadfaac501008a8d0b854c8` |
| `sony-550x-service.pdf` | `eb05dcddece60abe594355bfa84cdcb240e57ab2f2a5de7f9745cc481c3f4818` |

`source-records.json`, `additional-originals.json`, `primary-documents.json` and
`primary-followup.json` record provenance, primary-document hashes and failures.
The separate SCPH-5501 user-manual fetch returned 403 and was not used as evidence.

- `build/research-review/independent.py`: supplied STL assembly and component
  measurements; results in `file-measurements.json`.
- `build/research-review/inspect_blender.py`: original mesh inventories and four
  neutral views in each `*-inspection/` directory; PS1 alternate also has
  animation sample renders. Run in WSL with
  `~/slot-tooling/blender-4.5.0-linux-x64/blender -b -t 1 --disable-autoexec --python-exit-code 1 --python build/research-review/inspect_blender.py -- KIND`,
  where KIND is `ps1-exterior`, `ps1`, `gba-vxcl`, `n64` or `ags`.
- `build/research-review/shader_probe.py`, then WSL
  `sh build/research-review/shader_probe.sh`: reproduce the four DS captures.
  `ds-shader-comparison.json` and `ds-shader-comparison.png` record the comparison.
- `primary_followup.py` and `independent.py` retain primary-reference fetches;
  PDF page images were rendered locally and visually inspected.

The device's unexpected installed `labels.py` hash is unchanged as a blocker.
No SSH, frontend stop, installation, library rebake or device performance claim
belongs to this research pass. Continue with local source preparation and native
validation; follow MODEL_HANDOFF.md before any device work.
