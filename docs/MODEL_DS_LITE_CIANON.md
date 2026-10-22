# Textured DS Lite — Cianon (Phase E, part 2)

Implemented and device-tested 17 October 2026. This **replaces the procedural DS Lite**
described in [MODEL_DS_LITE.md](MODEL_DS_LITE.md) (kept for its lid-motion and Slot-1 history)
and supersedes the earlier DSi choice. Source: Cianon's
[Nintendo DS Lite](https://sketchfab.com/3d-models/nintendo-ds-lite-ca529eb7208746e89b7a28fd2246659d),
CC BY 4.0, `research/model-options-20261016/dslite/nintendo_ds_lite.glb`
(SHA-256 `2ad0ddd6…`). Pipeline as in [MODEL_TEXTURED.md](MODEL_TEXTURED.md):

```sh
sh tools/consolebuild/textured.sh cianon_ds.py research/model-options-20261016/dslite/nintendo_ds_lite.glb nds
sh tools/frontend/render_presentation.sh && sh tools/consolebuild/appearance-preview.sh
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
   --probe build/queued-models/native-probe --models nds --all-finishes
```

## What the source is

An open clamshell of 1,186 triangles in three objects: the lower body (926; shoulder keys,
buttons, D-pad, both hinge end knuckles, the centre barrel and the **bottom screen** are all in
it), the lid (232, including the **top screen** and its inner fascia) and a **fully
transparent glass overlay** (28, alpha-0 in a second copy of the same 2048 px atlas). Both
screens are painted in the atlas (health-and-safety warning, "NINTENDO DS" splash), and a game
card picture is painted on a small Slot-1 notch at the rear underside. There is no mechanism,
rig or animation, and the hinge ends interpenetrate (the lid's end tabs sit inside the body's end
barrels, 46 constant triangle pairs even when fully open). Its folded height is 24.2 mm against
Nintendo's 21.5 mm anchor (+12 %); proportions are kept, not corrected.

## Adaptation (`tools/consolebuild/cianon_ds.py`)

- Uniform scale from Nintendo's 133 mm width (1.184 mm per source unit, 3.0376 native per mm,
  the existing DS register); the 73.9 mm depth then matches the published depth. Underside at
  native y −87.5 and rear edge at z −112.3, so the camera pivot and idle framing match the old
  model (`spec`: ry 112.29, slot −113.29).
- The glass overlay is dropped (invisible). The other **1,158 source triangles and UVs are kept**
  (3,439 native vertices) with the 2048 px atlas, not enlarged.
- Screens: the two large flat faces of the deck (52.6 × 39.7 units) and of the lid's inner
  fascia are split out as `Bottom LCD` (62.3 × 47.0 mm) and `Top LCD` (61.1 mm wide) against
  Nintendo's 61.4 × 46.1 mm, blanked in the atlas and registered as the two live LCDs.
- **Hinge:** the lid already has its own knuckle; a circle is fitted to its section at both
  ends (y 20.91, z 18.64 source units), giving native hinge `(0, −25.47, −103.47)`. The lid
  group (shell + top LCD) is rotated about that axis from the source's 125.0° to the accepted
  **145° presentation pose** (`lid-data.h` is written from the registration, so
  `ds_lid_hinge`/`ds_lid_open_radians` follow the model).
- Fixed card: the game-card picture painted on the Slot-1 notch is cleared. The source has no
  receiving slot, so an original MIT **Slot-1 mouth** (35 × 4.6 mm, 1 mm proud, dark) sits on
  the rear face over the unchanged card path (card x −28, face height −70.4 native).
- Paint: dark-plastic classifier, as for the PSP; labels and the white screens' replacement
  blank stay unpainted. The existing DS card (`media.*`, original MIT) and its shelf art are
  unchanged.

## Verification

- Host: 166 tests pass (`tests/test_model_ds.py` rewritten: moving group, lid axis vs
  `lid-data.h`, scale/screens/folded height, central lid clearance, mouth on the card path);
  13 sidecar fallback cases; host frame grids `build/queued-models/frames-nds`,
  `build/phase-e/nds-host-grid.png`, `build/phase-e/nds-lid-grid.png`.
- **Limit of the geometric sweep:** the BVH body/lid sweep reports interpenetration at every
  pose (≈46 pairs open, ≈160 when folded) because the source's hinge ends and flush side faces
  overlap, and the card enters a solid rear wall (hidden by the shared depth buffer behind the
  proud mouth). The central deck area clears by >1 mm; the end-knuckle overlap is inherent to the
  source and was judged visually (no visible intersections in the opening sweep or on the device).
- Device (Mali-G31), `SLOT_BENCH=1`: open 186 ms, reopen 159 ms, scene **9.58 / 10.0 / 10.2 / 10.3 ms**
  (p50/p95/p99/max; the untextured procedural DS was 5.7 ms p50), GL error 0.
- Device, real menu, ~25 fps 6×4 grids (`build/phase-e/shots/nds-{insert,eject}`): browse, lid
  opens as the card is fed through the rear mouth, card seats, lid closes, the console turns to
  the open reading pose with title/players/year/art on the top LCD and the scrolling overview
  on the bottom LCD; eject reverses it. One 25 fps frame shows capture tearing, not model
  tearing. No game launched.
- Deployed 98 owned files (`build/phase-e/device/phase-e-b.tar`) and frontend
  `emulationstation-phase-e-b` SHA-256 `29bc17cfc79d25445e5656b30e7b833a4c07312e12a8e1099cbf155f6078effa`,
  helper `294cee5314a4f62fb9331bc7b329df1eff4cb1030c641c2857dcefe2b5ab506a`. Snapshot
  `phase-e-ds-20261017a` (324 data / 1,587 runtime): restored and audited **zero changed/new**,
  0 differing owned files, `StartupSystem=recent`.
- Previous procedural nds assets and generated headers are in `build/phase-e/before-nds/`.

## Not verified / known limits

- Cel and the eight paints are baked and host-tested, not checked individually on the device.
- The hinge and Slot-1 mouth are registrations, not OEM data. The source's top/bottom screens
  differ by 2 %; the lid is 12 % thicker folded than the published envelope.
- Reading at the three-quarter angle is not implemented (TASK_QUEUE item 10).
