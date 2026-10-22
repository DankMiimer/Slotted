# Hardware research review — 16 October 2026

**Subsequent independent work:** [MODEL_INDEPENDENT_RESEARCH.md](MODEL_INDEPENDENT_RESEARCH.md)
resolves the licence/CAD checks, inspects three original model archives, verifies
Sony/Nintendo manuals and records a controlled DS shader experiment. Read it
alongside this initial audit; statements below about unacquired originals and
unverified Printables licences describe the earlier review stage.

Received `SLOTTERS_HARDWARE_RESEARCH_MASTER.md` and its twelve companion files
from `C:/Users/mads1/.gemini/antigravity/scratch/slotters-research-package/`.
The package provides useful asset candidates and real downloaded CAD references.
It is **a research input, not a verified implementation specification**. Preserve
the user's requested improvements; correct the evidence before committing to
specific dimensions, pivots, source combinations or shader constants.

The original research folder is unchanged. An exact copy and nine referenced
downloads are archived in ignored `research/hardware-review/received/` and
`research/hardware-review/downloads/`. `research/hardware-review/audit.json`
records file hashes, measured STL bounds and seven public Sketchfab API responses.
The local inspection script is `build/research-review/audit.py`. No production
model, renderer, scraper or device file changed during this review.

## What is verified and useful

All **nine** referenced downloaded files exist at the separate download path
listed in the package README, and their SHA-256 values match the master report.
That verifies file identity, not dimensional accuracy or redistribution rights.

Public [Sketchfab model metadata](https://docs.sketchfab.com/data-api/v3/index.html)
independently confirms these candidates exist, are marked downloadable, and list
CC Attribution 4.0 at the time of inspection:

| Candidate | Creator | Published scene triangles | Verified scope |
|---|---|---:|---|
| [Sony PVM-1341 / PlayStation](https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245) | dark_igorek | 240,414 | Metadata only; includes a monitor scene, so do not treat this as the console-only cost |
| [Playstation 1](https://sketchfab.com/3d-models/96bed8283f2940d7bb4b1866ab0637a2) | Ceki / ecjhr0awipso | 283,604 | Metadata only |
| [Playstation 1 with Crash Bandicoot Disc](https://sketchfab.com/3d-models/93dbf6c499d84ae2ae2c7b07aa537a11) | Juan Galindo / Sheyk940 | 737,772 | Metadata only; inspect whether the needed interior is complete |
| [Playstation 1 and Controller DualShock 1](https://sketchfab.com/3d-models/a64834af06bf4c569bfec185fc57580b) | krittsky | 30,668 | Whole-scene count; author separately describes a 13,980-triangle console |
| [Gameboy Advance Cartridge](https://sketchfab.com/3d-models/gameboy-advance-cartridge-38c1e6702e5d4f21af1d0930689b1d10) | Vxcl / vxclhd | 1,524 | Metadata only; missing logo acknowledged by creator |
| [Gameboy Advance Blank Cartridge](https://sketchfab.com/3d-models/gameboy-advance-blank-cartridge-d5527f8b66014c17b38c6c299b101a3e) | ewaldc2028 | 2,810 | Metadata only |
| [Current companion cartridge](https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f) | thegraphicsgeek | 5,802 | Confirms the report's 12-triangle claim is incorrect |

No original PS1 or replacement Sketchfab GBA source archive is included in the
received download set. Downloadability and licence metadata do not establish
the report's claimed native formats, topology, part separation, exact revision
or neutral appearance. Obtain and inspect originals before selecting a source.
There is no basis yet to require combining two PS1 models; inspect a complete
source first and compare one coherent hardware revision.

The supplied Dave Parker OpenSCAD file is genuinely parametric and useful. It
defines `width=57`, `depth=34.4`, `bottom_handle_width=1.5`, a 44 × 23 × .4 label
cutout, `fillet=1` on its vertical label corners, and explicit guide/notch details.
Its two STL halves contain 980 / 1,380 triangles and each spans about 60 × 34.4 mm
in the print plane. These are **replacement-CAD properties**, not proof of OEM
dimensions. Its BOSL dependency and source licence still need inspection before
any derived production geometry is selected. Printables pages were unavailable
to this review's web fetch, so their claimed licences remain unverified here.

[Humble Bazooka's own installation guide](https://www.humblebazooka.com/2022/04/22/how-to-install-our-n64-cartridge-doors-and-region-free-bracket/)
provides a useful primary reference for the N64's two doors, their springs and
the retaining bracket. It does not establish the package's numerical slot,
seating or rotation measurements.

## Corrections needed before implementation

| Topic | Finding | Consequence |
|---|---|---|
| Current GBA cartridge | Master/deep dive call it a 12-triangle box; the package's own CSV and Sketchfab metadata say 5,802 source triangles. Our shipped derivative has **2,682 triangles / 1,954 vertices**, a physical recess and no source textures. | Replace/refine it because the user rejects its appearance, not on an invented description of the current asset. |
| GBA SP dimensions | Markdown claims 84 × 82 × 24.4; JSON lists 84.6 × 82 × 24.3. [Nintendo technical data](https://www.nintendo.com/en-gb/Support/Legacy-system/Technical-data-619375.html) specifies **84.6 × 82 × 24.3 mm**. | Retain the previously established manufacturer envelope; explicitly map width/depth axes. |
| GBA cartridge dimensions | Claimed body/crown thicknesses are presented as OEM truth without a measurement record. The actual SCAD has different wall/assembly parameters; a complete assembled result must be derived, not inferred by summing print-half bounds. | Assemble the supplied halves using the source's fit transform, measure the result, and compare it against original hardware. |
| Label corner radius | Markdown says R2; JSON says R1; supplied SCAD's label cutout uses `fillet=1`. | Reconcile the source and OEM reference; do not move baked label boxes speculatively. |
| N64 bay dimensions | Report promotes the exact prior 118.5/120.5-mm integration estimates to verified OEM truth without traceable primary measurements. | Keep them classified as fit assumptions pending actual evidence. A replacement flap's dimensions alone cannot prove the complete OEM bay. |
| N64 flap provenance | Deep dive attributes them to Tetsuo9999 / BY-NC-SA; CSV names Humble Bazooka / BY-NC-ND. | Resolve author, exact licence and intended use. Do not vendor or derive production flaps from the supplied mesh while this is unresolved. |
| N64 flap measurements | Actual full STL spans are **147.400 × 16.176 × 4.750** and **139.400 × 16.076 × 4.750 mm**. They include protruding features, so full bounds must not be confused with blade or bearing spans. | Identify the actual surfaces/pins and show the measurement selection. Distinguish CAD-local pivots from registered console pivots. |
| N64 cartridge reference | Supplied `pdaxrom` halves span 116 × **65** mm in their broad face plane; report calls the shell 75.5 mm high without explaining the discrepancy. | Identify this CAD's cartridge type and intended application before treating it as a NUS-006 reference. |
| DS card axes | Master calls the card 35 wide × 33 high and the mouth 35.6 wide; JSON gives 33 × 35 and a 33.6-wide mouth. | Resolve orientation and source measurements; do not widen the existing slot from the inconsistent table. |
| Hinge pivots and stops | Matrices provide precise coordinates and angles with weak or missing primary references and inconsistent coordinate descriptions. | Require a defined origin, axes, closed pose and at least two independently registered reference features. Source-file coordinates are not console measurements. |
| Insertion orientation | Discrepancy register claims our GBA and DS labels face upward. Current code already feeds them label-down; GBA has a green-label orientation regression. | Preserve current verified orientation while checking hardware evidence; do not apply another blind 180° flip. |
| DS speaker holes | Report proposes adding twelve holes; `ds_lite()` already builds twelve geometric perforations. | Inspect the actual model before duplicating features. |
| Confidence grades | Many replacement-CAD or inferred measurements are marked A, contrary to the requested manufacturer/standard definition. | Grade each scalar by its evidence; precision in an STL is not OEM confidence. |
| Motion timings | Timestamp tables provide no corresponding video links/timestamps or measurement logs. | Treat them as proposed choreography, not observed hardware timing or authority to change production scene durations. |

## Rendering findings against the actual project

There is a concrete first explanation to test for the DS appearance:
`console_appearance_ready()` currently excludes DS. It therefore uses cel even
when the user selects Realistic. This is verified in `appearance.h`, generated
`appearance-data.h` and `console-gl.h`. It does not prove DS needs a two-lobe
clear-coat shader. The user's new request authorizes Realistic across models;
the earlier restriction to completed accurate families is historical scope.

Useful technical leads are correct normal transformation under nonuniform
scales, careful crease normals and restrained material distinctions. Test those
in controlled native views before adding shader complexity or changing gamma
globally. Preserve the accepted NES/GB/GBC/SNES geometry and identifying details.

The package's shader is **not ready to paste into this renderer**:

- It requires diffuse textures and UV attributes; the native meshes currently
  provide positions, normals and vertex colours. A material interface must be
  designed rather than assuming those inputs exist.
- Its ambient contribution is added independently of base colour, and the
  claimed energy conservation is not established by its normalization constant.
  It also requires checking light-facing behaviour and the clear-coat energy
  allocation before calling it a physical material model.
- Declaring a `highp` destination does not by itself demonstrate the precision
  of an expression whose inputs are `mediump`; the proposed precision policy
  needs shader/compiler inspection and actual device measurement.
- `v_cavityDepth` is tied to one arbitrary local z axis and /25 scale. The
  project has several different slot orientations. It is not measured contact
  shadowing or a universal cavity model.
- The assertion that 2D shelf display automatically relights an already lit
  face does not describe our pipeline. The native animation draws actual media
  geometry; shelf images are displayed by ES as images. Our known approximation
  involves multiplicative baking and plastic-colour sampling, not generic 2D
  relighting. **Do not replace the approved Realistic hero captures with unlit
  albedo renders.** Preserve and improve the shelf/native hand-off deliberately.
- Fixed reflectance/exponent numbers, a material diagnosis of the DS shell and
  a promised 60 fps lack supporting measurements in the package. Treat these as
  hypotheses for comparison, not hardware facts or performance guarantees.

## Working order and outstanding research

1. Inspect the original PlayStation candidates and both replacement GBA meshes
   in neutral front/rear/side/open views. Compare them with registered hardware
   photographs; select one coherent PS1 revision and validate the disc bay.
2. Reconcile the GBA cartridge CAD, standard-shell silhouette, slot lip and seated
   position. Use actual geometry to establish lid/base separation and a closed
   hinge pose. Keep the already correct label-down insertion.
3. Establish N64 slot and flap dimensions from OEM references and traceable
   measurements. Build the original independently authored flaps from that
   evidence unless the user explicitly selects a different source/licence.
4. Add controlled Realistic comparisons for the DS and the other previously
   excluded models. Choose material improvements from observed results, then
   benchmark. Independently establish DS lid motion and its existing slot fit.
5. Validate both directions, moving-part clearance, native shelf hand-off and
   unchanged accepted-model geometry. Test performance on-device only after
   the separate deployment blocker is resolved.

`MODEL_RESEARCH_FOLLOWUP.md` is a copyable request to repair the research gaps.
The earlier device `labels.py` hash discrepancy is unchanged. Do not resume
device writes, rebaseline it or modify the protected pipeline on the strength
of this research package. See MODEL_HANDOFF.md for exact hashes and safeguards.
