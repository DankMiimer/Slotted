# Supplied GBA SP and rendering quality

Implemented and checked on the RG34XX-SP, 16 October 2026. The eight verified
originals are indexed in [MODEL_SOURCE_RECOVERY.md](MODEL_SOURCE_RECOVERY.md).

## Result and limits

The independent presentation now uses the user's NeilVFX GBA SP. Its separate
lid and 61.2 × 40.8 mm active LCD are registered to the native scene. Original
cartridge loading, hinge opening/closing and ejection choreography is retained,
followed by the reading pose at the user's half zoom. Independent browsing and
the fixed metadata HUD remain intact.

The untouched **65-object, 1,118,396-triangle** import remains in ignored
`build/model-quality/gbasp-neilvfx/`. The animation derivative has **81,010
triangles, 48,613 vertices and 53 parts**, versus the preceding 13,667-triangle
GBA. Per-part budgets retain large mouldings, bevels, hinge barrels and controls.
The source Game Pak and hidden internal parts are excluded; the existing
ROM-labelled Game Pak enters its bay. Uniform scaling uses an 82 mm base width,
preserving the artist's proportions rather than stretching the envelope.

The OBJ has one white material. Its colours are explicitly reconstructed;
these are **not recovered C4D shaders or full PBR materials**. The supplied logo
and alpha mask provide the bezel lettering. The native C4D and all four texture
files remain intact. The listing's **Editorial License (no AI)** is recorded
in the local credits and model information. Geometry, pose and browse assets
live under ignored `_slot/local-models/consoles/gba/`, outside the normal
redistributable model bundle and presentation packager.

Other consoles retain their current meshes/materials. Their rendering has
improved; the recovered originals are not described as eight completed new
geometry/material integrations.

## Rendering correction

All live models render into **1440 × 960**, retaining logical 720 × 480 scene
coordinates, framing and timing. The private renderer uses a matching depth
attachment and explicitly applies/restores the physical GLES viewport. SDL
cartridge/art geometry uses the same scale. Cached bounds convert back to logical
coordinates; tests compare them with the actual high-resolution pixels. There
is still one bounds readback per model, with none on animation/idle frames.

Browse poses are rendered at 2× and reduced to their final size. The baker
rejects raster enlargement and covers both finishes/all eight colours. Valid
pose caches include mesh and bridge source hashes. A normal stage rebuild
reuses them instead of returning to the small appearance PNGs. Editorial GBA
poses remain local; the packaged GBA fallback is kept separate. Since 17 October 2026 the packaged
SP is thegraphicsgeek's textured model and the theme setting **Slot GBA SP model** chooses between it and this
local profile ([MODEL_GBA_SP_GRAPHICSGEEK.md](MODEL_GBA_SP_GRAPHICSGEEK.md)).

Long game names now occupy two title lines when needed, including an upstream
`Font::wrapText` edge case where the overflowing final word was left unwrapped.
Players/year stay fixed while descriptions scroll.

## Reproduction and checks

- `tools/consolebuild/local_sp.py`: run in Blender 4.5 with `--disable-autoexec`,
  passing `gbasp-full-geometry.blend` and an ignored output folder. Saves the
  registered master before deriving the animation mesh.
- `model.pose`: `SCLCD001`, sixteen little-endian floats (hinge, opening angle,
  four LCD corners), then a 64-bit FNV-1a geometry hash. Positions/normals bind
  the registration to its mesh independently of paint selection.
- `tools/frontend/render_quality.py --probe PATH --all-finishes`: uses the
  compiled native probe's Linux SDL/GLES environment; prepares caches, records
  raster dimensions/scales and updates the stage assets.
- `tools/frontend/tests/local_profile.py PROBE SLOT`: valid, truncated,
  bad-magic, nonfinite, changed-geometry and mismatched-registration cases,
  plus Realistic/red and Cel/blue. Damaged profiles retain the packaged model.
- Windows: **152 tests pass, 6 POSIX skips**. Linux presentation/launch/watch:
  **12 pass**. Actual patched input replay and 50-cycle state checks pass.
- All **13** native probes pass: populated 2× textures, correct logical bounds,
  unclipped persistent silhouettes and GLES error zero.
- Device: new SP browse/slot/eject/reinsert, original lid/cart motion, LCD and
  typography, independent browsing, Panasonic/NES and DS screens. Pixel checks
  confirm fixed TV HUD/moving description and an unchanged released wheel.
  Composed-display capture retains 54 animation samples; capture cadence is
  **not** a GPU frame-rate measurement.

Evidence: ignored `build/model-quality/`, particularly
`shots/quality-final-title.png`, `shots/quality-final-tv.png`,
`shots/quality-final-ds.png`, `device-motion-review.png`, `pixel-checks.json`,
test/build logs and pose reports. The 18 unrelated dirty scraper/video files
still match their starting hashes. No scrape was resumed and no games launched
in this follow-up.

## Device state

Active temporary frontend:
`/userdata/system/slot-dev/slotted-prototype-20261016a/emulationstation-quality-readable`.
SHA-256: `7681e6fbb354a33c833f91db72e2e76deee12b1f297451640190f2c60f742abd`.
Official frontend and standalone helper are preserved. Reboot returns to stock;
the private scraper-credential release limitation still applies. No OS overlay
was saved. Test snapshot: **model-quality-20261016e**. Restore/audit its data and
runtime before reapplying the owned package and local-only SP assets.

Long-duration thermal/battery testing and p95/p99 input/frame targets remain
unmeasured. Successful renders do not establish those guarantees.
