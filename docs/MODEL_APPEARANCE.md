# Model appearance: finish and console colour

Recorded 15 October 2026; updated 16 October. Two theme options change how the accurate console
recreations are drawn. They change no geometry, motion, timing or media art.

| Option (theme subset) | Values | Default |
|---|---|---|
| Console model style (`slot-model-style`) | Realistic (`realistic`), Cel shaded (`cel`) | `realistic` |
| Console color (`slot-console-color`) | Original, Black, White, Red, Blue, Purple, Green, Yellow | `original` |

**Realistic** is the same accurate geometry with smooth diffuse lighting, a small
specular highlight and **no outlines**. **Cel shaded** keeps the three light bands
and inverted-hull outline. **Console color** is one shared choice for every
supported console; **Original** keeps each source's own palette. Paint applies to
enclosure parts only. Screens, controls, trim, printed identifiers, media and ROM
art keep their colours.

## Scope (explicit user decision)

**Updated direction, implemented and installed 16 October:** Realistic and Cel shaded
now work for **all thirteen console variants**, preserving the accepted
NES/GB/GBC/SNES geometry. `STYLE_MODELS` is separate from `PAINT`. The previously
excluded NES, DS, Mega Drive variants and Pico-8 receive the same existing smooth
shader. PlayStation uses a new authored native model and separate moving lid;
see [MODEL_PS1.md](MODEL_PS1.md). The seven-family rollout restriction is historical.

Paint is supported on **DMG, CGB, AGS, PSP, PAL/SFC SNES, US SNES, N64 and PS1**.
The five other console variants retain their original colours in every finish.
This distinction is covered by pixel comparisons of original/red stills. No
global gloss/gamma change or new clear-coat shader was introduced. The scratch
DS experiment is recorded in [MODEL_INDEPENDENT_RESEARCH.md](MODEL_INDEPENDENT_RESEARCH.md).

The subsequent GBA slice adds a physically registered lid and thinner, rebuilt
Game Pak. Both finishes share that motion; closed idle derivatives and the GBA
Realistic hero/shell/backing are regenerated. Panel normals remain planar, with
no global shader change. Hero label JSON is unchanged. Baked shelf faces keep
the Realistic finish even when Cel is selected for the animated console. Details
and offline evidence are in [MODEL_GBA_SP.md](MODEL_GBA_SP.md).

The DS follow-up retains that shared shader and adds a fitted, moving upper
assembly with closed idle renders in both finishes. Its twelve speaker wells
and control/port layout remain. See [MODEL_DS_LITE.md](MODEL_DS_LITE.md) for the
manufacturer anchors, fold clearance, native evidence and remaining estimates.

## How it works

- `tools/themebuild/appearance.py` defines `COLORS`, `STYLES` and `PAINT`. `PAINT`
  names each family's enclosure objects in its `model.glb`. SNES also checks the
  enclosure palette, since STL control corners share positions with the housing.
  It writes
  `consoles/<name>/paint.mask`: an `SCPAINT1` header, the vertex count, an FNV-1a
  64 hash of the native vertex bytes, then one weight byte per vertex (0 = keep,
  otherwise the brightness relative to the housing median × 192). The weight
  keeps moulded shading and two-tone housings readable after repainting.
- It also generates `appearance/manifest.json`, `style-*.xml`, `color-*.xml`,
  `appearance/shelf.xml` and `tools/slotlaunch/appearance-data.h`, with separate
  generated style and paint eligibility lists.
- `theme.xml` exposes both subsets; each include only sets `slotModelStyle` or
  `slotConsoleColor`. `shelf.xml` overlays the matching prerendered idle band on
  all systems (including the `gbh`/`gbch`/`gbah`/`n64h` aliases, regional SNES
  dispatch and Japanese Mega Drive selection matching the native helper).
- `launch/common.sh` exports `SLOT_MODEL_STYLE` and `SLOT_CONSOLE_COLOR`, honouring
  live per-system overrides before the theme profile.
- The native helper (`appearance.h`, `console-gl.h`) repaints the loaded vertices
  only when the mask's count and hash match the mesh; a stale or missing mask logs
  and keeps the original colours. Realistic selects the smooth fragment shader and
  skips the outline pass. `slot-launch.c` loads
  `appearance/<style>/<color>/band-console-<name>.png` and `.../consoles/<name>/body.png`,
  falling back to the default assets.
- `tools/consolebuild/appearance-preview.sh` (WSL, cached SDL/desktop GL from
  `build/native/`) compiles `appearance-preview.c`, renders each finish and colour
  with the same shader and writes the shipped bands and body sprites:
  2 finishes × 8 colours × 13 models. The five unpainted models repeat their
  original-colour stills so a shared colour choice keeps finish selection valid.

## Realistic cartridge shelf faces (16 October 2026)

The user approved matching the shelf to the Realistic default, including the
device installation. The later all-model finish request supersedes the original
six-shape limit. `hero-shells.sh` now captures **all twelve cartridge shapes**
with `SLOT_MODEL_STYLE=realistic`; PSP and PS1 optical posters are untouched.
Shapes, shells and backings are regenerated. All twelve hero label JSON files
remain byte-identical, including those of the six newly supported shapes.

The GBA Game Pak's lower-edge gloss streak came from interpolated shell normals
across long planar triangles. `ags_media()` rebuilds only that shell's normals
after cutting the label recess and pins front/back planar faces to their face
normal. Curved mouldings stay smooth. Triangle positions and material colours
are identical, and `console-gl.h` is unchanged. The exported-panel regression
rejects the old mesh; 4,392 matched native PNGs for every other family are
byte-identical (both finishes on supported families, cel on the others).

**Shelf faces are baked once.** All twelve shapes therefore stay Realistic on
the shelf even if someone selects **Cel shaded** for the animated models. The
option still controls the supported in-scene consoles and media. Clear boards,
plastic colours, finishes and chosen ROM labels retain the existing baker rules.

`realistic-faces-evidence.sh` repeats 113 generated files across forward,
reordered and repeat builds. All 127 tests pass in WSL; Windows passes with four
platform skips. The native shelf hand-off test recaptures every hero with the
specified shader and requires exact pixels/label measurements, then bounds the
first scene frame's mean RGB difference over the shelf canvas to 8/255
(observed 0.04–6.53). Baking, tint sampling, clear layers and resampling prevent
a lossless hand-off. The cached-library ARM64 build is warning-clean and the
helper hash remains `97d7fbcd…`.

The initial device preflight stopped on `slotcart/labels.py`. After the user's
“install and continue”, the installed pipeline differences were inspected and
preserved, never overwritten. The complete model rollout and **3,613 cached-plan
cartridge faces** are now installed. Fresh snapshots, atomic-copy audits, 56
installed previews and a real launch/return passed; details are in MODEL_HANDOFF.md
and `docs/evidence/models-install-20261016.json`.

## Adding paint support for a family

1. Identify the family's accurate enclosure parts. Realistic style support can
   expand independently under the updated user direction above.
2. Add its enclosure object names to `PAINT` and its system aliases to the
   `choices` list in `tools/themebuild/appearance.py`.
3. Run `wsl --exec sh tools/consolebuild/appearance-preview.sh` and review the cel,
   realistic and painted bodies. Painted vertices must not reach screens,
   controls, marks or the media label.
4. Update `test_model_appearance.py`'s expected scope and run the full suite plus
   the POSIX gate in WSL.

## Status

- The current full unit suite has 138 tests; Windows has five platform skips.
  Run both platforms for each model slice. The ARM64 helper builds warning-clean.
- The PS1/all-family rollout repeats 620 generated files across forward,
  reordered and repeat builds. Source preparation repeats twice. Native captures
  against pre-change code match 190/190 PNGs for existing Cel paths and the seven
  existing Realistic paths; accepted-model geometry and hero label JSON are
  unchanged. New Realistic shelf/scene hand-offs pass for all twelve shapes.
- Known blemish: a thin band of DMG paint reaches the left edge of the grey LCD
  bezel in painted colours. Tighten the DMG `PAINT` mapping if it is visible on
  the device.
- **Installed on the handheld on 15 October 2026**, after the user's explicit
  deployment request. The earlier guarded installer had stopped on the newer
  device `theme.xml`; the deployment reviewed that file and added only the style
  defaults and two option subsets. Other customizations were retained.
- Default is **Realistic** / Original since 16 October 2026: the user found cel
  shading too flat. Realistic is listed first in the subset, set as the theme
  variable default and used by `common.sh` when nothing is saved; an explicit
  Cel shaded choice is still honoured (tested). All twelve cartridge
  shapes and 3,613 rebaked library faces are now installed. Realistic installed
  previews measured 55.9–58.9 fps; the real launch/return measured 55.8/54.0 fps.
  MODEL_HANDOFF.md records the fresh rollback snapshots and current
  helper hash. MODEL_SNES.md retains the earlier temporary test evidence.
