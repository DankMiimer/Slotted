# Original model recovery and quality audit

2026-10-16. The user reported that the new presentation looked as if small
models had been enlarged and selected `Slotters/Research/gbasp3d` as the new
GBA SP source. This pass locates and verifies originals, imports the selected
SP at full detail and identifies the quality losses. The subsequent authorized
[integration](MODEL_QUALITY_INTEGRATION.md) is installed in the temporary
frontend, with measured hinge/LCD registration and sharper rendering.

## What was found

The original downloads are intact. Eight original source files were compared
with their existing SHA-256 provenance records: **all eight match**. Runtime
GLB hashes also match the preceding `Slot_ESDE-next-models` checkout for all
13 console variants. The presentation did not accidentally substitute an
older set of mesh files.

There are nevertheless three real losses in the current pipeline:

1. **Small raster inputs get enlarged.** The GBA browse input is only 248×197px,
   with a 246×194px visible model; its new stage enlarges that silhouette to
   228px high. The live model is first drawn into a small part of a 720×480
   texture, then that texture is enlarged for the LCD reading pose. After the
   user's 50% zoom reduction, GB is still enlarged about 2.03×, GBC 1.88× and
   GBA 1.60×. PSP is about 1.05×; DS is about 0.95×, so enlargement cannot
   explain all of their appearance differences.
2. **Some meshes were reduced before this presentation work.** GBA's prepared
   master has 42,190 triangles versus 13,667 in its runtime GLB; PS1 has 59,007
   versus 13,768, and DS 25,810 versus 14,343. Even some files called `master`
   already follow earlier source preparation/reduction; they are not all
   untouched artist originals.
3. **Source materials were deliberately stripped in earlier preparation.**
   All current runtime console GLBs contain zero embedded images. Source UVs,
   albedo/normal/roughness maps and material graphs were replaced by semantic
   colours and the lightweight native shader. The Realistic option smooths
   that shader's lighting; it does not restore the original materials.

The corrective direction is to use the original files below as the source of
truth, preserve material/UV information in editable masters, derive animation
meshes separately and render static/close views for their final pixel size.
Enlarging cached PNGs or simply renaming the current runtime GLBs cannot
recover their lost detail. Original sources also need the existing slot,
cartridge, hinge and LCD registrations reapplied; a direct file swap is not a
complete integration.

## Verified original files

Paths are relative to `C:/Programmering/SBC/RG34xxSP/` unless otherwise noted.
The machine-readable index, full hashes and raster measurements are in
`Slot_ESDE/build/model-quality/audit.json`.

| Console | Creator / original source | Verified local original |
|---|---|---|
| GB / DMG | [Let's Do 3D](https://sketchfab.com/3d-models/gameboy-dmg-01-29849a15fe0a40a6a18e01c9d544a0ed) | `Slot_ESDE/research/model-quality/originals/dmg/source/Skectfab gameboy.blend`; original archive is also in the user's Downloads |
| GBC | [Wikiti](https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19) | `Slot_ESDE-next-models/research/gbc/source/source/model.zip`, member `model/model.dae`; original texture maps remain beside the archive |
| GBA SP, preceding source | [thegraphicsgeek](https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f) | `Slot_ESDE-next-models/research/gba/gameboy_advance_sp.glb`; the 10.4MB original, not the 1.05MB prepared derivative |
| PSP | [JSJetStream14](https://blendswap.com/blend/14767) | `Slot_ESDE/research/model-quality/originals/psp/Playstation Portable(PSP 3001).blend`; 23.9MB Blender source with subdivision/material setup, from the original Downloads ZIP |
| SNES PAL | [quick_loop](https://sketchfab.com/3d-models/super-nintendo-d42c35b117974ade8842f0964f5fd59e) | `Slot_ESDE-next-models/research/snes/quick-loop/source/model/model/model.dae`; texture maps and original archive remain in that research folder |
| SNES US | [Steven H. Tran / ibbqcats](https://sketchfab.com/3d-models/super-nintendo-console-41c9dd1f5a53493cbe2e00a190150e93) | `Slot_ESDE-next-models/research/snes/ibbqcats/source/Super Nintendo Console Mesh/Super Nintendo Console Mesh.stl` |
| N64 | [Joseph Rohm](https://sketchfab.com/3d-models/nintendo-64-0bec1e1ed1bf4a96af858008b72437a3) | `Slot_ESDE-next-models/research/n64/rohm/extracted/source/N64_with_controller.fbx`; original ZIP and maps remain in the same research tree |
| PS1 | [dark_igorek](https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245) | `Slot_ESDE-next-models/research/hardware-review/independent/ps1-exterior/extracted/source/Sony_Pack_final(blend 3_6).blend` |

DS Lite, NES, Mega Drive and Pico-8 currently come from the project's procedural
geometry. There is no hidden, previously imported high-detail artist original
for those models. DS has an unreduced prepared geometry master; NES and MD have
their editable generator. This distinction matters when deciding which systems
need better rendering and which need a different source model.

## Selected replacement GBA SP source

**The user's `Slotters/Research/gbasp3d` was selected and integrated as the local
GBA model.** Their latest request also adds thegraphicsgeek's SP as an additional
CC option. Keep both sources: the full 10.4MB thegraphicsgeek original listed
above is available for renewed quality preparation, and the working NeilVFX
local model remains. See `docs/NEXT_CHAT_PLAN.md` for the current queued work.

The directory contains:

- `GameboyAdvanceSP_neilvfx.c4d` — 43,155,999 bytes, original native scene.
- `GameboyAdvanceSP+OBJ.rar` — 23,821,394 bytes; extracted OBJ is 118,447,641 bytes.
- `Textures.rar` — original four-image pack: 1280×125 screen-surround lettering,
  its alpha, 2835×2835 AGS-001 sticker and 2400×2400 Nintendo graphic.

It matches [nvfx's Gameboy Advance SP listing](https://www.cgtrader.com/free-3d-models/electronics/other/gameboy-advance-sp)
by title, filename, July 2019 archive dates and the listed C4D/OBJ sizes. The
listing currently says Editorial License (no AI), rather than CC BY. Originals
and research derivatives remain local and excluded from the redistributable
MIT/CC runtime assets; their attribution and terms have not been relabelled.

The OBJ was imported with Blender 4.5, auto-execution disabled, retaining all
**65 objects, 564,288 polygons and 1,118,396 triangulated faces**. No decimation,
geometry scale normalization or material replacement was applied to these saved
source derivatives:

- `Slot_ESDE/build/model-quality/gbasp-neilvfx/gbasp-full-geometry.blend`
- `Slot_ESDE/build/model-quality/gbasp-neilvfx/gbasp-full-geometry.glb`
- `Slot_ESDE/build/model-quality/gbasp-neilvfx/objects.json` — per-part geometry,
  bounds, UVs and material inventory.

The 1600×1600 `gbasp-full-geometry.png` is a neutral studio geometry review,
rendered directly from the full imported mesh. It deliberately uses one review
material. The supplied OBJ's 79-byte MTL contains only a white `default`
material, so it cannot reproduce the C4D materials by itself. The native C4D
scene and separate textures are retained for their material translation.

The new model now has the lid/base/LCD/material map and an 81,010-triangle
animation derivative. Its 1.12-million-triangle source is preserved. The
derivative has 48,613 vertices, within the native 65,535-vertex limit; the full
GLB is not treated as a drop-in `.mesh`.

## Repeatable evidence

```powershell
python -m tools.consolebuild.audit_quality --gba-source 'C:\Programmering\SBC\RG34xxSP\Slotters\Research\gbasp3d'
```

This command reads source, master, runtime and image files without modifying
them, verifies all eight original-file hashes and writes the local audit JSON.
The original user files and active device presentation remain untouched by
this recovery pass.
