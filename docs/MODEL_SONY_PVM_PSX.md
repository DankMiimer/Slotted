# Sony PVM-1341 and textured PlayStation

Implemented and device-tested 17 October 2026 (TASK_QUEUE item 14). Source:
[Sony PVM-1341 || Sony Playstation — dark_igorek](https://sketchfab.com/3d-models/sony-pvm-1341-sony-playstation-5f80311f1a4646ef9673f20ee6dc6245),
CC BY 4.0. Both the models and their derived renders retain that attribution/licence.
The original ZIP was recovered locally and verified against the previously recorded SHA-256
`0dab2049dc14e93fffb97b4576017fe26f26df31323612457405a00326885845`.
The packed original blend is `fe083c1125de93b3a62beb1497756acfbda26f36e2fc66e2559d24aa18cf05af`.
They remain intact under `research/model-options-20261016/sony-pvm-psx/`.

## PlayStation

`tools/consolebuild/darkigorek_psx.py` restores all seven source console meshes:
**64,717 triangles / 51,805 native vertices**, without decimation. It retains the
accepted 270 × 60 × 188 mm envelope, 1.6 scene units/mm, hinge and disc seat from
[MODEL_PS1.md](MODEL_PS1.md), including the early SCPH-1001 optical-unit registration.
The source lid is closed before registration and animated independently.

The two original 4096px albedos become 1024px tiles in a 2048px runtime atlas, with
protected print/drive/socket detail and repaintable enclosure/lid. Full source maps
and the textured editable master remain in ignored `build/textured/psx/`; the shipped
editing GLBs contain geometry/provenance. Native shading remains albedo plus simple
lighting, without normal/roughness/metallic/emission shading. The source alpha map
has no transparent interior texels in the console's sampled UV islands (10,926,162
covered texels checked, excluding the narrow UV-edge apron). There is no fixed game
disc or screen in the seven console objects; other source collections are excluded.
The earlier image-free model stays in `third_party/models/darkigorek-ps1/` for reproduction.

The accepted optical behavior is unchanged: native disc/body/lid share depth,
insert/eject leave the lid open, A/Play closes during the one-second prelaunch interval,
launches once, and returning reopens the inserted scene. Independent vertical rays at
576 points across the 120mm disc annulus found **zero body or closed-lid intrusions**.

## Monitor and metadata

**Slot TV model → Sony PVM-1341 (dark_igorek)** is a third persistent option, alongside
the Panasonic/default and Retro TV. Unknown values still fall back to the Panasonic.
`darkigorek_pvm.py` keeps the complete cabinet, feet, controls and rear connections with
source materials/maps, without decimation. It removes six loose power-cord/plug/contact
islands that were joined to `main_body`. The curved glass (320 source polygons) is
separated from the speaker/indicator assembly and replaced by blank live glass.

`render_tv_standard.py` renders the cabinet at the accepted 35° elevation / −22° turn,
205 native units high, with the glass quad, floor point and footprint registered.
Its logical cabinet is **321.5 × 347px** and live glass **155 × 108px**. The deep cabinet
leaves a smaller metadata area than the other TVs. `SlotMetadataLayout.h` uses 70% type
and tighter spacing for TV glass under 125px high so two-line titles, HUD, art/scrolling
description and footer fit without overlap. Other TVs and handhelds retain their existing
metrics. The layout arithmetic is exercised directly by a host C++ test.

## Rebuild and verification

Use Blender 4.5 with `--factory-startup --disable-autoexec --python-exit-code 1 -t 1`;
both source adapters open the blend with `use_scripts=False`. From WSL:

```sh
source=research/model-options-20261016/sony-pvm-psx/source.blend
blender=/home/mads1/slot-tooling/blender-4.5.0-linux-x64/blender
sh tools/consolebuild/textured.sh darkigorek_psx.py "$source" psx
# Run the PVM adapter with the safe Blender invocation above, then:
"$blender" -b --factory-startup --disable-autoexec --python-exit-code 1 -t 1 \
  --python tools/consolebuild/darkigorek_pvm.py -- "$source"
"$blender" -b --factory-startup --disable-autoexec --python-exit-code 1 -t 1 \
  --python tools/consolebuild/render_tv_standard.py -- pvm third_party/models/darkigorek-pvm/model.glb
python3 -m tools.themebuild.television
sh tools/consolebuild/appearance-preview.sh
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
  --probe build/sony-pvm/native-probe --models psx --all-finishes
```

Host: **177 tests**, actual-view input replay, 50-cycle state replay, independent optical
depth test, 13 PSX texture acceptance/fallback/finish cases and all 16 PSX finish/paint
browse poses pass. Three host compositions check PSX/SNES/Dreamcast with the PVM on the
shared floor. Device: real menu selection, saved PVM choice across restart, original and
Cel/blue presentation, insertion/ejection, both metadata pages, and actual Bugs Bunny
Play/return. Playcount changed **0 → 1**, confirming one launch; test statistics/save/config
changes were preserved and restored afterwards. No ROM modifications or new fixtures.

Device native scene, 180 measured frames: **15.714ms median / 16.341ms worst**, GL error 0;
prefetch 252ms, first open 255ms, reopen 200ms. This measures the native scene rather than
the entire frontend; the full-detail model is near the 60Hz frame budget.
Evidence is under `build/sony-pvm/`: `tests-final.log`, `psx-fallback.log`, `clearance.json`,
`scene/`, `device/` and `shots/`. Dense captures run at 24–25fps, with 24 timestamped frames
per 6×4 grid; full-resolution metadata captures run at about 18fps.

## Installed state

115 owned files in `sony-pvm-a.tar`; frontend
`/userdata/system/slot-dev/sony-pvm-20261017/emulationstation-sony-pvm-c`, SHA-256
`4c91a37bf4b4ce2952e3e4fdac93f265fc369b4d07daabeecaa1112ea27925c1`.
Helper SHA-256 `dcee63ea66b657a4982b1928cc51cbfe32717067ddf0d77500b33535398ad36b`.
The development frontend is bind-mounted over the official executable; reboot restores
the official binary. No OS overlay saved and no commit made.

Snapshot `sony-pvm-20261017a` contains 324 data files / 1,597 prior runtime files.
Final audit checks all restored data and all **1,604 runtime files** against that snapshot
plus the intended increment. The tested CHD remains SHA-256
`41d9c0d56a87803886473a2178b4d0da52455630ae3f375a46e49f122eb6091a`.
Original TV/paint/style/startup settings are restored; the new TV remains an available option.
See `build/sony-pvm/device/final-audit.json` for the final audit result.
