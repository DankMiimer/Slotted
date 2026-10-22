# Source-faithful textured models

Implemented and device-tested 16 October 2026 (Phases A and B of
[NEXT_CHAT_PLAN.md](NEXT_CHAT_PLAN.md)). The first textured model is BPoole's
Game Boy Color; the same path serves the remaining selected sources.

## Format

The legacy `SCTOON2` mesh (positions, normals, colours) is unchanged and still
read by every renderer. A textured model adds two files beside it:

- `model.texture` — `SCTEX003`: vertex count, atlas width/height, paint
  reference luminance, FNV-1a hashes of the mesh vertices, the index buffer and
  the albedo PNG's bytes, then one GL UV pair per vertex.
- `model.albedo.png` — power-of-two RGBA atlas (GBC: 2048²). RGB is the source
  base colour; alpha marks repaintable plastic for the console-colour options.

`tools/slotlaunch/console-gl.h` validates everything before use. Any missing,
truncated, stale, non-finite or mismatched file keeps the vertex colours (which
are sampled from the same atlas, so the fallback still resembles the source).
GLES2 mipmaps are generated; the shader multiplies albedo by the existing
Realistic/Cel lighting. **No PBR:** the source normal, ORM and emissive maps
are not rendered and are not claimed.

Paint: `mix(albedo, paint × luminance/paint_luma, alpha)` keeps printed logos,
labels, buttons, screws and the source's moulding/weathering detail under every
colour. The vertex `paint.mask` remains for the untextured fallback.

## Pipeline

```sh
# WSL. Blender stage (source never executes scripts), then CPython packing,
# fallback sprite, specs, patched frontend and host probe:
sh tools/consolebuild/textured.sh bpoole_gbc.py research/model-options-20261016/gbc.glb gbc
sh tools/frontend/render_presentation.sh          # front LCD poses + SlotScreens.h
sh tools/consolebuild/appearance-preview.sh       # finish/colour bands and bodies
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
   --probe build/queued-models/native-probe --models gbc --all-finishes
```

- `textured_blender.py` imports with UVs/images intact, flattens parents, keeps
  the source's original encoded image bytes and writes per-corner native
  geometry. `bpoole_gbc.py` is the source-specific adapter.
- `textured.py` builds the atlas: the base-colour map is only ever reduced
  (4096 → 2048), every texel no kept face samples is cleared (this removes the
  removed parts' art), named regions are blanked, small material maps are
  inset into free space, and the paint alpha is derived from plastic colour
  within the painted parts' UV coverage. It also writes provenance to
  `third_party/models/<family>/source.json`, the registration
  (`consoles/<model>/registration.json`) used by `tools.themebuild.consoles`,
  and `tools/slotlaunch/textured-data.h`.
- Generated files are written with LF endings; run the generators under WSL.

Several material tiles can share one atlas: `tiles` maps each source material to a quadrant (`tile_size` sets
the atlas side so 1024 px maps stay at native resolution, as for the GBA SP) and flat-colour materials
(`constants`) may sit beside them.

## BPoole GBC adaptation

- Uniform scale from the source's own Game Pak width (57.00 mm at 7.987 mm per
  source unit): housing 78.03 × 131.33 × 28.55 mm. The artist's proportions are
  kept; nothing is stretched to the 133.5 mm hardware height.
- The fixed half Game Pak and the battery contacts/springs hidden under the
  cover are removed (15,606 kept triangles, 10,343 native vertices). The
  displaced battery cover is moved 11.867 source units forward, the median of
  28 rim samples, so it continues the back surface.
- Rear lip measured by ray-casting the back wall: the label clip (`slot`) is
  88.33 native units; the existing CGB Game Pak is centred on the source cart
  (`cgb_cart_label_native` −16.13). Clearance below the lip is 1.4 mm behind and
  0.5 mm in front of the Game Pak; above it the back is open.
- Atlas: the baked Pokémon battle screenshot on the LCD panel is blanked, the
  fixed Pokémon Game Pak label is cleared with all other unused texels, and the
  scratched glass map is composited over a dark LCD (no blending at runtime).
- The registered LCD is the source's 44.45 × 40.26 mm screen glass.

## Device measurements (Mali-G31, RG34XX-SP)

| | first open | reopen | scene p50 / p99 |
|---|---|---|---|
| GBC textured, no prefetch | 597–604 ms | 154–157 ms | 4.6 / 5.3 ms |
| GBC textured, after browse prefetch | 178–234 ms | 154–164 ms | — |
| GB / local GBA SP / PSP / DS (untextured) | 116 / 142 / 86 / 115 ms | — | 6.6 / 8.0 / 4.6 / 5.7 ms (p50) |

GLES limits: texture 8192, 16 attributes, 16 fragment units; ASTC LDR and ETC1
are available in the GLES2 context. PNG decode of the 2048² atlas is 420 ms, so
the frontend decodes it on a worker thread when a game for that console is
highlighted (`slot_native_prefetch`). Decoded pixels stay in a two-entry RAM
cache keyed by the PNG hash (not GL names, which may not survive ES's context
recreation). A 1024² atlas would decode ~4× faster but visibly softens small
print; 2048² is kept. ASTC would remove decoding but needs an encoder that is not
installed; it is not used.

## Verification

- Host: 13 sidecar acceptance/fallback cases (`tests/textured_fallback.py`),
  all 13 model probes with GL error 0 (untouched models pixel-identical to the
  pre-change baseline), 155 Windows + 155 Linux tests, reproducible pre-session
  helper hash (`9a9e2ffc…`) before rebuilding it.
- Device: browse pose; insertion (61-frame capture, no blank frames after the
  prefetch); seated rear lip/label; LCD metadata alignment and wrapping;
  eject; Realistic red and Cel blue; standalone helper insert at 56.6 fps.
