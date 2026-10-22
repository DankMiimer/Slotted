# PlayStation console — 16 October 2026

Implemented on `models/gbc-gba-exemplars`, installed 16 October. The previous flattened SDL
deck and circular lid are replaced by an authored console with a separate native
3D lid, disc well, spindle, optical assembly, front sockets, side vents and rear
connectors. Both Realistic and Cel shaded work. Geometry is adapted from
[dark_igorek's Sony PVM-1341 / PlayStation](https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245),
**CC BY 4.0**, console collection only. The processing code and identifying
words are MIT. Source images, monitor, accessories and game art are excluded.

## Hardware and source registration

The selected target is the early **SCPH-1001** exterior, not the 5501 proposed
in the received research. Sony's [SCPH-1001 instruction manual, page 18](https://www.manualslib.com/manual/3466089/Sony-Playstation-Scph-1001.html?page=18)
confirms **270 wide × 60 high × 188 deep mm**, two controller ports and two memory
card slots, plus rear video/audio RCA, RFU DC, serial and AV multi-out connections.
The source has this early rear layout. The already inspected 550x service manual
shares the envelope, but does not establish this source's revision.

The source also mixes that early rear with a later right-facing optical unit.
First-hand [SCPH-1001 repair photographs](https://documents.cdn.ifixit.com/pdf/ifixit/guide_1595_en.pdf)
(PDF pages 3–5) place the early pickup behind the spindle. Preparation rotates
the optical pickup and its complete cover 90 degrees in the horizontal plane
about the spindle; it does not mirror their geometry or combine a second mesh.
The photographs are inspection references only and are not shipped or traced.

`import_ps1.py` closes the source lid by removing its explicit -50-degree X
rotation, then measures the complete closed envelope. Physical corrections are
approximately +4.78% width, +2.93% depth and +7.54% height, before one uniform
**1.6 native units/mm** scene scale. The measured source hinge is
(-.618, 16.332, -78.249) mm; the disc label centre is approximately
(0, 17.895, 0) mm, x right/y up/z front. They are **source registrations**, not
manufacturer pivot measurements. `source.json` records exact values, source
hashes, references, corrections and uncertainty. No external pivot spreadsheet
is used. Sony/PlayStation and button identifiers are original font geometry
placed onto ray-tested supporting surfaces; they are not source image decals.

The image-free full prepared source is in `third_party/models/darkigorek-ps1/`.
The original archive SHA-256 is
`0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845`.
Preparation uses Blender 4.5, `-t 1 --disable-autoexec --python-exit-code 1`, and
opens the original scene with `use_scripts=False`. Rebuilds use the prepared
source offline, with no account or network required.

## Native rendering and motion

`ps1.py` defines the physical envelope, palette, source registration and generated
`ps1-data.h`. `models.py -- psx` exports the full editable master, physical GLB,
runtime GLB, native mesh and body sprite. The runtime is **13,725 triangles**;
separate per-part fitting budgets preserve the body, lid, well and drive. The
hinged native index range includes the lid and its two printed identifiers.

`ps1-scene.h` draws the static body with depth testing, the existing optical disc
projection and rim, then the actual native lid against the same depth buffer.
This follows the existing UMD composition method. The disc's physical seated
diameter is 120 mm and thickness 1.2 mm; its transparent bore exposes the spindle.
The seated centre comes from the source registration. The lid's **78-degree
scene opening is choreography**, retained from the previous animation, not a
verified hardware stop angle. Insert closes after seating; eject opens and holds
while the disc spins down, then reverses the loading path. Existing PS1 disc
posters, art, loading sound schedule and disc data processing are retained.

The new `kind=6` console participates in generated body/band assets and the
Realistic/Cel and paint variants. Paint includes enclosure and lid, keeping the
drive, well, sockets and print original. Native renderer failure falls back to
the prepared body sprite. Device frame rate has not been measured for this model.

## Validation and limits

- Exported-triangle vertical rays around a 120-mm disc footprint verify that
  the body is below the disc's underside and the closed lid covers it.
- A native green-disc regression has visible free/open positive controls,
  requires no green after closure and checks that the open lid rises at least
  70 screen pixels above its closed position. This rejects a wrong hinge sign
  that would otherwise rotate the lid down through the case.
- Native insert/eject and timed captures are under ignored `build/ps1/`; inspect
  `insert/insert-33.png` for the open disc well and `insert/insert-60.png` for
  closure. The production preview harness drives the actual scene function.
- `ps1-evidence.sh` repeats source preparation twice, then generated model,
  stills, appearance and twelve hero/shape/shell/backing inputs across forward,
  reordered and repeat builds. It runs the full WSL suite and builds ARM64.
- The accepted NES/GB/GBC/SNES geometry is unchanged. All twelve hero label JSON
  files remain byte-identical. Disc poster/shape and scraping files are unchanged.

Completed evidence: **620 generated files** match across forward, reordered and
repeat builds; prepared source GLB/JSON match two independent preparation runs.
All **132 tests pass in WSL**; Windows passes with five platform skips. ARM64
builds warning-clean. A five-pose native comparison against pre-change code
(`5d887fd`) has **190/190 identical PNGs**: Cel on all twelve existing console
variants and Realistic on the seven already supported variants, using the same
current assets on both sides. The accepted-model geometry files also have no
diff. Details are under `build/ps1/comparison/`.

This is an authored adaptation with a checked envelope, port family and optical
orientation, not a certified OEM scan. Fine moulding dimensions and the hinge
axis still inherit source accuracy; hidden internal mechanics are outside the
animation. The native optical artwork does not write depth, so its physical fit
and the final cover pass are essential. Exact collision checks beyond the sampled
disc-footprint rays remain useful follow-up validation.

Installed Realistic insert/eject previews pass at **57.8/58.4 fps**, with no
mesh/paint/image fallback. Optical art and the 28 existing PS1 faces are unchanged.
MODEL_HANDOFF.md records the full deployment, snapshots and protected-pipeline
preservation; the previous hash stop is resolved without overwriting that pipeline.
