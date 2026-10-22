# Slotters model integration brief

The complete worked sourcing/adaptation process is in
[MODEL_WORKFLOW.md](MODEL_WORKFLOW.md); use this file as the copyable technical
contract for an external modeller.

Give this brief to an external modelling agent together with the current
`tools/consolebuild/models.py`, `tools/themebuild/consoles.py`,
`tools/slotlaunch/console-specs.h`, `cartridge-console.h`, `psp.h`, and
`console-gl.h`. Target the branch that will receive the model; dimensions and
hinges can change between branches.

## Copyable instructions

- Prefer original geometry; the user has now also approved licensed authored
  recreations. Record the creator, source, exact licence and modifications,
  retain attribution, and exclude separately licensed assets from the MIT grant.
  No actual scans, unlicensed meshes, source textures, downloaded logo paths or
  GPL-era Slot assets. Reference
  photos may guide measurements, but keep them in ignored `research/`; they
  must not become textures or committed files. Keep identifying Nintendo/Sony
  marks minimal and author their paths ourselves.
- Specify the exact hardware revision and region. Model in millimetres from a
  source-linked dimension/landmark card. Mark published values, photograph
  estimates and unverified details separately. Do not exaggerate thickness or
  change proportions for the camera. Apply one uniform presentation scale.
- Make the result reproducible in `tools/consolebuild/models.py` and its
  procedural helpers. Supply an editable full-detail master plus a runtime
  derivative, rather than only a rendered picture or an opaque final GLB.
- Project coordinates are **x right, y up, z towards the front**. Authoring maps
  them into Blender as `(x * .01, -z * .01, y * .01)`. Home-console top surfaces
  therefore use project y as elevation. The `.01` factor is presentation units
  to Blender units, not a promise that one existing presentation unit equals
  one millimetre. DMG and PSP exemplars use 168/90 and 480/169.4 presentation
  units per millimetre respectively.
- Apply transforms before native export. Use finite, consistently outward
  normals; no negative/mirrored object scales, coincident surfaces, degenerate
  triangles or disconnected accidental fragments. Keep required object names
  used in `tests/test_consoles.py`, or update their contracts deliberately.
- The handheld runtime is GLES2 at **720x480**. Its current asset format is
  indexed position + normal + RGB vertex colour. It has **no UVs, image
  textures, PBR materials, normal maps, alpha materials or Blender shader
  graph support**. A textured GLB will not automatically work. Use physical
  geometry and flat original vector printing unless a renderer extension is
  explicitly part of the task.
- Export through our pipeline to `model.mesh` (SCTOON2), `model.glb`,
  `mesh-info.json`, and `body.png`. A native vertex is nine little-endian floats:
  xyz, normal xyz, RGB. The header is `<8sIII`: `SCTOON2\0`, vertex count,
  index count, hinged-range first index. Indices are little-endian uint16.
  Use **15,000 triangles per mesh as the default performance budget**; a measured
  family-specific profile may exceed it when the user accepts its handheld frame
  rate (see MODEL_SNES.md). Stay within 600,000 indices and at most 65,535 native
  vertices. Hard edges/colours can duplicate vertices. Keep the file format
  intact; use the exporter rather than constructing a different GLB-only path.
- Mark flat printed path objects with `obj['printed'] = True`. The exporter
  gives ink a normal of length .25 so the native outline hull skips it;
  physical surfaces have unit normals. Rear printing needs outward-facing
  triangles and legible orientation. Do not model every printed line as a
  raised bevelled solid with a thick black border.
- Preserve characteristic silhouette curves, LCD/bezel outlines, control
  spacing, slot rims and hinges during simplification. Spend fewer triangles
  on concealed interiors, screws and small secondary bevels. Keep screen glass,
  plastic and metal visually distinct using supported colours and small local
  highlights. The desired finish is accurate hardware with restrained cel
  shading, thin outlines and controlled shadow bands.
- **Media and console must use the same physical scale.** State the media's
  width, height, thickness, connector edge, label-facing direction and seated
  centre. Keep the complete opaque case around cartridge labels and UMD prints.
  An UMD has a rear spindle opening but no open hole through its printed front.
  Shelf art is a separate presentation contract: preserve its placement and
  masks, and transition to physical dimensions during native alignment if needed.
- Keep motion parts separate. For PSP set `obj['hinged'] = True` on every door,
  liner, ring, rail and stop object that moves with the door. They are exported
  as one contiguous native index range, not a glTF skeleton. Preserve the
  existing NES flap contract too. Read the target branch's hinge, seat and
  slot coordinates; do not bake the launch pose into the mesh. Update source
  specs and native choreography together when physical accuracy changes them.
  The exemplar GLBs retain `printed`, `hinged` and `hinge_mm` as node extras.
  Preserve those extras when importing/exporting through Blender or another
  authoring tool. `hinge_mm` uses project axes (x right, y up, z towards front),
  even when the authoring tool uses different axes. PSP's pivot is
  `(0,-33.6,-8.5)` mm; the generated C header derives its native coordinates
  from that same source. Scene extras `slotters_native_units_per_mm` and
  `slotters_glb_to_metres` describe scale; physical masters have the latter
  set to 1. The native renderer still reads the mesh index range and normals.
- Keep existing scene timing, media orientation, slot clipping, fade and
  physical wall occlusion. For DMG the visible rear lip is y=45.5 mm; the
  internal connector floor at y=13.5 mm is a different landmark. The loaded
  label plane is z=-13 mm. Model the rounded rear shoulders, deep screw wells,
  recessed plate, latch and continuous grip ribs from rear references too.
  Compare both unloaded and loaded rear views against hardware before accepting
  the model: envelope dimensions and triangle counts cannot establish resemblance.
  Preserve
  independent display-layer behaviour. DMG/PSP insert motion is 1.85 s with a
  .10 s hold; eject is 1.75 s with a .35 s hold. Prove that the case clears the
  slot through travel, reaches the connector/holder and fits behind the closed
  PSP door. Do not declare success from only a front screenshot.
- Rebuild only the affected systems. Refresh packaging with
  `tools.themebuild.consoles.build()`; this creates the cropped `body.tga`,
  idle band, `specs.json` and `console-specs.h`. Do not casually regenerate
  shelf XML or the media baker. Do not hand-edit generated specs without
  changing their source.
- Deliver matched neutral front/rear/side/top views, native GLES 720x480 pose
  sheets and insert/eject sequences, before/after against the receiving branch,
  triangle counts and numerical remaining discrepancies. Repeat the build and
  compare hashes to prove determinism. Run
  `python -m unittest discover -s tests`; run POSIX-only gates in WSL.
- Work in an isolated branch/worktree. Never use the handheld, deploy, launch
  games, fetch libraries from it, push or merge unless separately authorized.
  Reuse existing cached ARM64 SDL libraries for a WSL cross-build. Record real
  device fps, composed-layer capture and return checks as follow-ups.

## What to bring back

The procedural source, editable master, runtime assets, dimension card,
before/after review images, tests/build results and a short discrepancy list.
If the external tool cannot export our native format, an original Blender
scene with named parts, applied transforms and vertex colours is a useful
handoff; it still needs the project's exporter and loading verification.
