# Textured GBA SP — thegraphicsgeek, and the "Slot GBA SP model" setting (Phase E, part 3)

Implemented and device-tested 17 October 2026. thegraphicsgeek's
[Gameboy Advance SP](https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f)
(CC BY 4.0, `research/model-options-20261016/gbasp/gameboy_advance_sp.glb`, SHA-256 `a2f81428…`)
replaces the earlier reduced vertex-colour derivative as the **packaged** SP, and a new theme
setting chooses between it and the user's local NeilVFX SP. See also
[MODEL_QUALITY_INTEGRATION.md](MODEL_QUALITY_INTEGRATION.md) (the local model) and
[MODEL_TEXTURED.md](MODEL_TEXTURED.md) (the pipeline).

```sh
sh tools/consolebuild/textured.sh graphicsgeek_gba.py research/model-options-20261016/gbasp/gameboy_advance_sp.glb gba
sh tools/frontend/render_presentation.sh && sh tools/consolebuild/appearance-preview.sh
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
   --probe build/queued-models/native-probe --models gba --all-finishes --packaged gba
```

`--packaged gba` bakes the packaged SP even though `local-models/` holds the NeilVFX profile
(it sets `SLOT_GBA_SP=graphicsgeek` for the probe); without it the local browse poses are baked.

## The setting

Theme Configuration → **Slot GBA SP model** (`slot-gba-sp-model`, `theme.xml`):

| Value | Shows |
|---|---|
| `neilvfx` (default, first entry) | The local NeilVFX profile when `local-models/consoles/gba` is installed and valid; otherwise the packaged SP. Behaviour before this change. |
| `graphicsgeek` | The packaged thegraphicsgeek SP, even when the local profile is installed. |

An unknown or missing value is the default. `SlotPresentation.cpp` reads the setting, exports
`SLOT_GBA_SP`, includes it in the native scene identity (so changing it reloads the scene) and
skips the local browse image for `graphicsgeek`; `slot_local()` in `SlotNative.c` returns before
touching any file for `graphicsgeek`; `launch/common.sh` exports the same variable for the standalone
helper (which always uses the packaged SP). **Shrednector's Zelda SP is not a menu entry**: it is on
the waiting list (no download, no licence) and a fake option would break the setting's contract.

## Adaptation (`tools/consolebuild/graphicsgeek_gba.py`)

- Source: 66,826 triangles in 46 parts and three material tiles (1001 base, 1002 buttons/ports/lid,
  1003 shoulder keys/lettering/label), each with a 1024 px base-colour map and UVs offset by whole
  tiles. The two alpha-blended lens overlays (42 triangles) are dropped; **66,784 triangles and
  44,179 native vertices are kept**, with the source UVs, wear and printed detail. The three maps are
  packed unreduced into one 2048 px atlas (`textured.py`: new `tile_size`, constants alongside tiles).
  The source colour is a neutral grey (silver); the old blue was a vertex-colour reconstruction.
  Normal/roughness/AO maps are not rendered.
- Registered into the packaged SP's native frame so the Game Pak path and reading pose are unchanged:
  footprint corrected from the artist's 84 × 82 mm to Nintendo's published 82 × 84.6 mm (×0.9762,
  ×1.0317; thickness uniform at 224/82 native/mm), underside at native y −85.1, and the bay end wall
  at native z 18.0, 0.8 behind the Game Pak's leading edge.
- **Bay:** the source has a real cavity (floor 1.07 mm, roof 7.20 mm, open at the front, 6.1 mm tall);
  the registered Vxcl Game Pak is 7.29 mm thick, so the roof, the mouth's top edge and the lip rounding
  above it (635 vertices) are raised 1.72 mm.
- **Hinge:** circles fitted to the hinge pin inside both fixed corners (r 2.5 mm, residual < 0.05 mm)
  give native `(0, −33.62, −109.79)` (written to `lid-data.h` as `ags_lid_hinge`). The source lid is open
  at 105.0°; after the footprint correction the registered LCD gives **105.45°** (`ags_lid_open_radians`
  1.8405, as before). The source has no mechanism: the axis is a registration.
- Moving group: `SP display lid`, `SP LCD glass`, both knuckles, `SP ScreenGuard`, `SP LogoSticker`
  (9,770 triangles). LCD: the source's 2-triangle screen (61.3 × 42.6 mm), registered as `SP LCD glass`.

## Verification

- Host: 170 tests (`test_handheld_models.py` rewritten for the new bay/lid contracts, new
  `test_gba_sp_setting.py`); 13 sidecar fallback cases; the 8 local-profile cases
  (`local_profile.py`) still pass, i.e. damaged local files still fall back to the packaged SP.
  Probe check: default and `neilvfx` load the local profile, `graphicsgeek` does not and validates the textured albedo.
- Geometry sweeps (Blender BVH, `check_handheld_lids.check`): **0 body/lid pairs over 101 poses**
  (positive control 1,714 with the closed lid lowered 5 mm) and **0 Game Pak/body pairs through the
  complete feed** (the first build overlapped the lip by 330 pairs until the roof window was widened).
- Device (Mali-G31), scene p50 / p95 / p99 / max, GL error 0:

  | | open | reopen | scene |
  |---|---|---|---|
  | thegraphicsgeek (packaged) | 343 ms | 234 ms | 8.78 / 9.01 / 9.49 / 9.51 ms |
  | NeilVFX (local, reference) | 218 ms | 791 ms | 11.73 / 12.03 / 12.26 / 12.27 ms |

- Device, real menu: the entry appears in Theme Configuration, selecting thegraphicsgeek was saved
  (`subset.slot-gba-sp-model=graphicsgeek`) and the silver SP replaced the blue one at once; ~25 fps
  grids (`build/phase-e/shots/gba-{insert,eject}`) show the Game Pak fed through the front slot, the
  lid closing, the turn to the reading pose, title/players/year/art/description inside the LCD, and
  the reverse eject. No game launched.
- Deployed 516 owned files (`build/phase-e/device/phase-e-c.tar`; the count is the regenerated GBA
  stage/appearance images) and frontend `emulationstation-phase-e-c`, SHA-256
  `2d5f751e13aa226bcbf5bb89c897f8940eda7dcd0e2846df9ee0433e727bccdb`, helper
  `5a6764f2b8c02cb0518d653e19fa9d130c92429d1e392dd9d6a9441d048e4551`. Snapshot
  `phase-e-gba-20261017a` (324 data / 1,592 runtime): restored and audited **zero changed/new**, 0
  differing owned files; the setting returned to its default; the NeilVFX files are untouched.
- Previous packaged GBA assets and generated headers: `build/phase-e/before-gba/`.

## Not verified / limits

- Cel and the eight paints are baked (host-tested), not individually checked on the device; the
  grey source takes paint like the other textured models.
- Selecting NeilVFX again was checked on the host (probe) and by the unchanged default render, not by
  clicking it back in the device menu.
- The roof raise and footprint correction are registrations to the existing Game Pak, not OEM data.
