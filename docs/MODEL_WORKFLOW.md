# Finding and adapting console models for Slotters

Recorded 15 October 2026 from the DMG/Game Pak and PSP-3000/UMD work. Use this
workflow for the remaining families. The external modeller's copyable contract
is [MODEL_INTEGRATION.md](MODEL_INTEGRATION.md); the actual first-family
dimensions, licences, corrections and evidence are in
[MODEL_EXEMPLARS.md](MODEL_EXEMPLARS.md).
Copy [MODEL_FAMILY_TEMPLATE.md](MODEL_FAMILY_TEMPLATE.md) to start the next
family's source record, reference card and verification report.

The practical shortcut is a good, complete **authored recreation** with an
editable source and a usable licence, followed by measured adaptation. Downloading
a mesh is the start of that process. A convincing product render does not prove
correct dimensions, a usable rear shell, native materials or cartridge clearance.
Do not describe an asset as 100% accurate without measurements supporting that.

## What worked in this project

| Component | Selected source | What we retained | What we changed |
|---|---|---|---|
| DMG-01 + Game Pak | [Let's Do 3D, Sketchfab](https://sketchfab.com/3d-models/gameboy-dmg-01-29849a15fe0a40a6a18e01c9d544a0ed), CC BY 4.0 | Complete front/rear housing, mouldings, controls, ports and cartridge | Overall dimensions, cartridge thickness, rear bay/lip, panel normals, native colours and our identifying paths |
| PSP-3001 | [JSJetStream14, BlendSwap](https://blendswap.com/blend/14767), CC BY 3.0 | Curved housing, fittings, controls and separate UMD cover/ring | Envelope, LCD/aperture, ring roundness, opaque key surfaces/glyph placement, shared hinge and native detail budget |
| UMD | Our original geometry from ECMA-365; source linked in the reference card | Dimensioned case, rear apertures and blank print surface | Native loading fit and label mapping |

The earlier procedural models had recognizable colours and controls but missed
characteristic mouldings and proportions. Adding details to those approximations
did not establish the right shape. Actual scans were also tried and rejected by
the user. They are not the chosen source route and must not enter shipped assets.
The user's rear DMG photograph was particularly useful for the slot, rounded rear
shoulders, screw wells, battery cover, latch and grip ribs that a front-only review
misses. Reference photographs remain research, never model textures.

## 1. Define one hardware family before searching

State the exact console revision, region and matching media. For example:
DMG-01 with standard Game Pak, PSP-3000/3001 with UMD, AGS Game Boy Advance SP,
DS Lite, PAL/Super Famicom versus US SNES, or Japanese versus Western Model 1
Mega Drive. Treat variants as explicit requirements rather than silently mixing
features from different revisions.

Start its reference card with published width/height/depth, LCD size/aspect,
media envelope, connector edge, slot mouth and seating direction. Add front,
rear, both sides, top/bottom and an open/loading view. Mark each number:
manufacturer/standard, calculated, photo/recreation estimate, or unverified fit.
Use the A–D convention in MODEL_EXEMPLARS.md. A precise exported coordinate does
not upgrade the confidence of a photo estimate.

## 2. Find a small shortlist of authored sources

Sketchfab and BlendSwap supplied the selected exemplars. Useful search terms
combine the exact revision with `3D model`, `recreation`, `Blender`, `download`,
and the matching cartridge/disc. Record a shortlist in ignored
`research/<family>/candidates.json` with these fields:

| Field | What to establish before investing in adaptation |
|---|---|
| Identity | URL, creator, exact revision/region, authored recreation rather than scan |
| Permission | Exact geometry licence and an archived copy of its notice |
| Download | A real source download, its format and any account requirement |
| Completeness | Rear, side ports, bottom, media and separate opening parts |
| Editability | Geometry carries the shape; important details are not only texture/normal maps |
| Proportions | Envelope and a few screen/control ratios against the reference card |
| Budget | Main housing versus detail triangle costs, after needed subdivision |

Inspect geometry with neutral front/rear/side/top views before choosing. Reject
the wrong revision, front-only props, stylized proportions, damaged scans,
unknown permissions and models whose identity disappears without textures.
Prefer a source that includes the matching media or leaves its bay accessible.
Do not choose solely by a polished thumbnail or an advertised polygon count.

For the actual downloads, the user signed in to Sketchfab and BlendSwap in the
browser. Passwords stayed in the browser. Keep archives, source `.blend` files,
licence-page copies, screenshots and candidate renders under ignored `research/`.
Record the source-file SHA-256 so a later preparation run can identify its input.
Do not make normal builds depend on those accounts or expiring download URLs.

## 3. Resolve provenance before vendoring

The user approved licensed authored recreations in addition to original geometry.
The selected CC BY models keep their own licences; they do not become MIT when
processed by our code. Store creator, source URL, exact licence, source hash and
all adaptation steps in `third_party/models/<creator-family>/source.json`.
Retain attribution in `_slot/MODEL_CREDITS.txt` and the asset exclusion in LICENSE.
Check the licence of each future source independently; this is not blanket
permission to import arbitrary models or textures.

Source game screenshots, decals, UV images and downloaded logo paths are excluded.
Minimal Nintendo/Sony identifiers are our own vector paths. No GPL-era Slot
assets are imported. Cathode was investigated as a UI/layout reference; it did
not supply editable console meshes for this work and none of its assets were used.

## 4. Prepare an image-free physical source once

`tools/consolebuild/import_authored.py` is the precedent. Its `gb` and `psp`
adapters are deliberately source-specific: object names, source axes, material
groups and modifiers differ. Add a new adapter for a new source; do not run the
DMG mapping against another creator's scene.

Open source scenes with auto-execution disabled. Evaluate only the subdivision
needed for the chosen housing, remove unrelated scene objects, split named
physical parts and replace materials with our palette. Exclude embedded images,
source text/decal geometry, cameras and lights from the prepared output. Keep the
downloaded source untouched as the research input.

Measure the source at a uniform scale first and record the discrepancy. Our DMG
source at 148 mm tall was 89.184 mm wide and 35.012 mm deep; the published target
is 90 × 148 × 32 mm. The PSP source at 169.4 mm wide was 73.946 mm high and
15.485 mm deep, versus the 71.4 × 18.6 mm housing target. These required explicit
geometry corrections, followed by local landmark checks. They were not solved
by distorting the camera. After physical correction use one uniform presentation
scale; never leave a nonuniform runtime scale hiding a thickness error.

Prepared `third_party` GLBs are physical assets in metres, image-free and
offline-buildable. Preserve custom properties for palette, creator/licence,
`printed`, `hinged`, `hinge_mm`, `dimension_critical` and any outline exclusion.
Project landmark axes are **x right, y up, z front**. Blender's internal axes
differ; use the explicit transforms in the adapter and `models.xyz()`, and check
the exported front/rear and dimensional envelope rather than guessing axes.

The preparation commands used for these sources, from the repository root with
Blender 4.5 available, are:

```sh
blender --background --disable-autoexec --python tools/consolebuild/import_authored.py -- gb "research/authored-models/gameboy-dmg-01/source/Skectfab gameboy.blend"
blender --background --disable-autoexec --python tools/consolebuild/import_authored.py -- psp "research/authored-models/psp-3001/Playstation Portable(PSP 3001).blend"
```

Those filenames are the actual downloaded names. Re-run preparation when the
source adapter changes. Routine model builds use the committed prepared GLBs
and need neither these research files nor an Internet connection.

## 5. Adapt the console and media together

Import through `models.py`, map the prepared palette to the supported vertex
colours, and add original identifying paths. Keep full-detail editable exports,
physical-scale exports and runtime derivatives separate. Native GLES2 accepts
position, normal and RGB per vertex; it does not load the source's PBR graph,
normal maps, alpha materials or a glTF animation rig.

Match the console, physical media, label plane, slot/connector floor and seat in
the same millimetre frame. Record each explicitly. An exposed retaining lip is
not the connector floor. For a hinge, tag every moving part and use one pivot
for the shell, liner, ring, rails, stop, label and media basis. The native exporter
uses a contiguous hinged index range, not Blender bones.

The first adaptations exposed problems worth checking on every family:

- The DMG recreation's approximately 6.9-mm cartridge did not prove clearance
  for the corrected 7.8-mm case. Its concealed wall and rear mouth needed changes.
- Removing source modifiers left unstable housing normals. Rebuild hard
  boundaries and face-area-weighted panel normals, then inspect a neutral turn.
- PSP's transparent key covers hid glyphs once rendered opaque. Put printing on
  the visible surface; do not assume source alpha transfers to our renderer.
- PSP's rear ring was elliptical and its LCD/aperture mismatched. Correct both
  the opening and glass; changing only the glass creates overlaps.
- In-plane UMD adjustment belongs to free approach/withdrawal. Finish aligning
  before entering the rails; verify the reverse motion and closed cover too.

Protect silhouette, screen/bezel contours, control spacing, slot rims and hinges
before simplifying. Reduce coplanar tessellation and small fittings individually.
Avoid a whole-console decimate pass. Retain a component when reduction moves its
vertices beyond its original bounds. **15,000 triangles is the default performance
budget, not a fixed renderer limit.** The user authorized challenging it with
handheld evidence, initially at 60 fps and subsequently accepting about 50 fps for
SNES. Choose detail per family against the agreed target and record both profiles
and results; never infer handheld performance from desktop previews or triangle
counts. The renderer accepts at most 65,535 exported vertices and 600,000 indices;
hard normals/colours split vertices, so source vertex counts are insufficient.

Dense moulded seams can look worse with an expanded outline hull. The DMG case
omits that expansion while controls/media retain it. Printed details use short
normals to skip the hull. The native renderer also avoids submitting triangles
that the outline shader would clip anyway; that optimization preserved all 488
review captures byte for byte and substantially improved DMG insertion fps.

## 6. Build only the affected slice and prove it offline

The executable exemplar recipe is:

```sh
blender --background --disable-autoexec --python tools/consolebuild/models.py -- gb psp
python -c "from pathlib import Path; from tools.themebuild.consoles import build; build(Path('theme/art-book-slot/_slot'))"
sh tools/slotlaunch/build.sh
sh tools/consolebuild/offline-preview.sh
blender --background --disable-autoexec --python tools/consolebuild/review.py
python tools/consolebuild/compose_review.py
python -m unittest discover -s tests
```

Run the shell/ARM64 commands under WSL with cached `build/native/lib`, pinned SDL
headers and desktop GLES dependencies described in the consolebuild README.
`build.ps1` fetches libraries from the handheld and is unsuitable for offline
work. On Windows use `wsl --exec` to avoid accidental argument expansion.
The packaging call above refreshes console assets/specs without invoking the
shelf XML generator or media baker. Review its generated diff before committing.

Freeze the receiving commit's source/assets under `build/exemplars/before/`
with `git archive`/`git show` before overwriting outputs. For this slice that
commit is `fba7ffe`. Render neutral front/rear/side/top and loaded-rear views;
render actual 720×480 GLES insert/eject poses and timed sequences separately.
Mechanical endpoints omit the fade to expose seating; production endpoints
include it. A deliberately black fade endpoint is not a useful fit check.

The current offline harness/review scripts are specialized to `gb`/`psp`.
Extend their system dispatch, physical axes and media setup for the next family;
passing a new name alone does not establish equivalent coverage. PS1 additionally
has its own `discpreview`/`psx.h` path. Home-console adapters must address the
existing `yscale` thickness stretch before claiming accurate physical envelopes.

Check actual exported-triangle clearance, not only approximate boxes. Add
targeted tests for measured envelopes, preserved contours, label recesses,
hinge metadata and important rear apertures. Use an independent bright-media
diagnostic plus a visible positive control: the DMG label must not leak below
the lip, and UMD must disappear completely behind the closed cover.

Rebuild twice, including reversed family order, and compare SHA-256 for every
affected GLB/mesh/PNG/TGA/JSON and generated header. Exclude logs/captures with
timestamps. The first exemplars produced 29 identical generated files. A valid
build, a triangle count or a front render alone is not visual acceptance.

## 7. Validate on the handheld when authorized

Keep device work separate from offline authoring. Use a fresh hash-verified data
and runtime snapshot with ES stopped. Verify the installed helper's baseline
before replacing it, stage a manifest of only the intended files, and verify
each installed hash. Do not replace a whole theme to install two models.

Test blank-media previews first, then a real launch and return for each affected
family. Measure normal observation and composed-display capture separately;
offscreen desktop fps is not a handheld benchmark. Check slot travel, label
mapping, closure, physical-screen readability, return layers and actual accepted
input. Keep scene durations unchanged when correcting geometry or motion.
Do not hide recovery delay by making the animation longer.

Input probes use a temporary selection hook that adds navigation overhead.
Remove it afterward. Prefer one tap per return around motion completion; a
multi-tap callback trace only supplies a conservative readiness estimate.
`tools/dev/return_input_probe.py OUTPUT.json --offset .2` records one actual tap
and frontend descriptor changes without pixel reads; run it on the handheld
alongside `esdev.py` after the game has started. Its output still includes the
probe's observation overhead and does not prove an exact readiness boundary.
Preserve test-created/changed saves, then restore the fresh data snapshot and
audit it. Confirm intended model hashes and no unrelated runtime changes before
restarting ES. Keep captures and personal game art in ignored `build/`.
Verify executable permission separately from byte hashes after copying a rebuilt
helper. Require fresh insert/eject log timestamps and an actual post-eject input
event; a successful game boot with an old animation log does not validate motion.

## Handoff for the next family

User preference for future accurate models: every completed replacement must
support both **Cel shaded** and **Realistic** (the same accurate geometry with
smooth lighting and no outlines), and the shared **Console color** selector with
**Original** plus the common paint colors. Apply paint to enclosure parts; retain
screens, controls, trim, identifiers and ROM art. Keep shelf, fallback and moving
model appearance consistent. See MODEL_APPEARANCE.md for the implementation.
The current supported set is DMG, CGB, AGS, PSP, both SNES regions and the N64. Leave the other consoles'
existing models alone until each family receives its new accurate recreation;
then add its semantic paint mapping and matching appearance derivatives as part
of that model slice. This is an explicit user scope decision.

Physical media for the remaining cartridge systems are done (MODEL_MEDIA.md):
original shells from the shelf drawings, mapped to published envelopes. When a
family's accurate console arrives, keep its media's scale and seat contract or
update media.py's SCALES and the native seat together, and replace the slot fit
correction with the new console's real opening.

Lessons from the media slice: EXACT booleans are only repeatable with
`blender -t 1`; the multithreaded result changes slightly between runs, which
canonical sorting cannot fix. On already-bevelled procedural shells, EXACT also
re-triangulates rounded shoulders and draws stray contour lines; FAST kept the
original shading. Run the console packager in WSL to keep LF endings. A
before/after native comparison needs the receiving branch's own compile flags
(the CGB/AGS tint); otherwise every accepted CGB/AGS frame falsely differs.

Lessons from the CGB/AGS slice: imported scene bounds can remain stale until
mesh and view-layer updates; bake parent transforms before deleting empties.
Collada and glTF split corners differently. Weld coincident positions before
loose-island dispatch or housing reduction, then restore sharp/weighted panel
normals. Keep dimensional cavity cuts after runtime reduction. Exact booleans
may enumerate identical triangles differently; canonicalize cyclic index order
without reversing winding, scoped to newly introduced families.

Clearance checks must include short-normal physical housings, even when those
faces suppress outline expansion. Require a deliberate collision control and
an exposed label control; a hidden seated label alone does not establish correct
orientation. Check the actual loading illustration: the SP receives a connector-
first cartridge with its label toward the underside. Check crop aspect against
the real recessed well, including a floor behind thin source shells.

For automated Blender checks use `--python-exit-code 1`; the default can exit
successfully after a Python assertion. Freeze source as well as assets for the
native before/after harness, dispatch physical footprints/timings explicitly,
and compare previously accepted families byte for byte after shared scene edits.

Deliver one reviewable family slice containing its reference card and confidence
levels, selected-source/provenance record, preparation adapter, prepared physical
source, full-detail and runtime exports, console/media/label/hinge contract,
before/after neutral and native motion evidence, budgets, deterministic-build
results and numbered remaining discrepancies. Keep licence/source, model/native
integration and validation/documentation in focused commits. Work in an isolated
worktree; never push or merge without the user's instruction.

Start with one remaining family and its matching media. Approve the neutral
shape and native loading sequence before repeating the process across variants.
