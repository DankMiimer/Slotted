# Textured PSP and Game Boy (Phase E, part 1)

Implemented and device-tested 17 October 2026 through the source-faithful
textured pipeline ([MODEL_TEXTURED.md](MODEL_TEXTURED.md)). Phase E's DS Lite is in
[MODEL_DS_LITE_CIANON.md](MODEL_DS_LITE_CIANON.md); the GBA SP option/setting is still open (TASK_QUEUE item 7).

Rebuild either model end to end (WSL):

```sh
sh tools/consolebuild/textured.sh ostrovsky_psp.py research/model-options-20261016/psp/sony_psp.glb psp
sh tools/consolebuild/textured.sh verheyen_gb.py   research/model-options-20261016/gb/gameboy_classic.glb gb
sh tools/frontend/render_presentation.sh && sh tools/consolebuild/appearance-preview.sh
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
   --probe build/queued-models/native-probe --models gb psp --all-finishes
```

## PSP — Ilya Ostrovsky (CC BY 4.0)

`tools/consolebuild/ostrovsky_psp.py`. Source: `research/model-options-20261016/psp/sony_psp.glb`
(SHA-256 `aca80b66…`), 58,250 triangles.

- Only the staging ground (50 triangles) is removed; the source's 45° display
  tilt is undone and the model is scaled uniformly from its own 169.4 mm width
  (26.06 mm deep, 74.8 mm tall). No decimation: **58,676 runtime triangles**
  (52,760 vertices) because the one connected rear moulding is clipped at two
  straight seams (x = ±38 mm, UVs/normals interpolated) into a separately moving
  UMD cover and two rear wings.
- Source UVs and base-colour map (4096 → 2048 px). The baked home-screen image on
  the LCD is blanked; the 15 source button parts are kept.
- Original MIT fittings behind the cover: drive floor, cover lining and two holder
  rails plus a stop. The UMD keeps the existing original geometry (`media.*`) and
  insertion path; the cover hinges about (0, −36.5, −10.6) mm.
- **Hinge is a fitted approximation:** the source has no mechanism
  (`registration.json` → `hinge_uncertainty`).
- Registered LCD is the source's 95.3 × 53.6 mm glass (aspect 1.779, 0.8 % wider
  than 16:9); live metadata is inside it at the accepted reading zoom.

## Game Boy — Bram Verheyen (CC BY-NC 4.0, noncommercial)

`tools/consolebuild/verheyen_gb.py`. Source `research/model-options-20261016/gb/gameboy_classic.glb`
(SHA-256 `86ad86c9…`), 9,856 triangles, all kept (13,105 vertices).

- Presentation tilt undone from the source LCD plane; uniform scale from its 90 mm
  width (90 × 150.9 × 34.9 mm). The source wear and its front sticker are kept.
- The active LCD (eight planar faces, 47.5 × 42.9 mm) is separated from its bevel and
  blanked for live metadata; source U range repeats continuously, so the atlas wraps.
- Bay measured by ray-casting: floor 6.263 mm, rear lip at 44.54 mm; the existing
  Game Pak (original MIT shell, `media.*`) is registered to those (label plane
  −26.62 native). Clearance: 0.88 mm behind the label, 0.2 mm in front.
- **Licence:** the model, its atlas and every GB render are noncommercial; this is
  carried through CREDITS.md and `_slot/MODEL_CREDITS.txt`. The preceding Let's Do 3D
  housing is no longer used; its Game Pak shell is still the GB media mesh.

## Verification (17 October 2026)

- Host: 164 tests pass (PSP/GB assertions in `tests/test_consoles.py` and
  `tests/test_model_exemplars.py` were rewritten for the new sources: part names,
  registration-based bay/lip/LCD checks, per-model triangle budget 15 k GB / 60 k PSP).
  13 sidecar acceptance/fallback cases each for GB and PSP (missing, truncated,
  stale, non-finite, changed or resized albedo all fall back to vertex colours;
  Realistic red / Cel blue / original render). Host frame grids: `build/queued-models/frames-gb`,
  `build/phase-e/frames-psp`, `build/phase-e/gb-host-grid.png`.
- Device (Mali-G31), `native-probe` with `SLOT_BENCH=1 SLOT_PREFETCH=1 SLOT_REOPEN=1`,
  GL error 0:

  | | open | reopen | scene p50 / p95 / p99 / max |
  |---|---|---|---|
  | GB | 245 ms | 179 ms | 6.88 / 7.19 / 7.51 / 8.22 ms |
  | PSP | 250 ms | 159 ms | 12.72 / 13.15 / 13.23 / 13.24 ms |
  | GBC (reference) | 251 ms | 172 ms | 7.12 / 7.49 / 7.76 / 7.84 ms |

  PSP stays under the 16.7 ms frame budget at its worst sample (for scale, the N64
  cartridge scene measured 14.9 ms).
- Device, real menu, Realistic default finish, ~25 fps 6×4 grids in
  `build/phase-e/shots/{gb,psp}-{insert,eject}`: browse, insert (rotate to rear,
  Game Pak / UMD seat, door closes), reading view with title, players/year,
  scrolling description and artwork inside the registered LCD, and eject, both
  consoles. No game was launched.
- Deployed 189 owned files (hash-verified, `build/phase-e/device/phase-e-a.tar`) plus
  the frontend `emulationstation-phase-e-a`, SHA-256
  `6e1a5c45a02589948446f7498c94706fdb92cc9f104eb7bf0ade0608aa6696fb`; a later
  one-file credits increment. Snapshot `phase-e-20261017a` (324 data / 1,581 runtime
  files, taken before any Phase E deployment): restored and audited — **zero changed,
  zero new data files**; a fresh hash comparison shows 0 differing owned files.
  `StartupSystem=recent` / `StartupOnGameList` unset again. Reboot restores the
  official frontend.

## Not yet verified

- Cel finish and the eight console paints were baked (2 finishes × 8 colours × 14
  models) and pass on the host, but were not individually checked on the device.
- Three-quarter view / shared TV surface (TASK_QUEUE item 10) is not implemented;
  the 17 October answer for handheld reading is recorded there.


Public asset update (23 October 2026): The Game Boy character sticker and the Retro TV decorative decals are removed in the public derivatives. Earlier references to retaining the sticker describe historical/private originals. Geometry and source licenses are retained. See docs/PUBLIC_ASSET_REMEDIATION.md (or the repository root documentation).
