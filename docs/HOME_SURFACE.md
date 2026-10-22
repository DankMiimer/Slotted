# Home consoles and TVs on one surface

17 October 2026 revision of TASK_QUEUE item 10. Supersedes the home-console
orientation and centre-based floor layout in STANDARD_VIEW.md.

The user's confirmed choices:

- TVs keep their southwest turn (−22°); home consoles face southeast (+22°),
  matching the TV's amount of turn in the opposite direction.
- Align the front base edges and use believable relative sizes.
- Apply this to home consoles only. Keep handheld browsing, reading angles,
  zoom and live LCD registration as they were.

The nine home profiles are SNES PAL/US, NES, N64, Mega Drive international/Japan,
PICO-8, PSX and Dreamcast. Their browse images, fallback sprites, paint/finish
derivatives, insertion/ejection scenes and inserted views now face southeast.
Both optical lids retain the existing behavior: open after insertion/ejection,
close only for the one-second A/Play sequence, reopen on return.

## Placement

Home consoles rotate about physical vertical (`console_matrix`), keeping their
bases level. Handhelds retain `console_matrix_turn`, which turns their reading
screens about camera-up. `SLOT_HOME_YAW` and `SLOT_STANDARD_YAW` are deliberately
separate in `tools/slotlaunch/psx.h`.

The previous layout aligned footprint centres. A deep TV's nearest base edge
then appeared lower than a shallow console's. `slot_native_contact` now projects
the visible front edge of the console base, including housing overhang in front
of recessed feet. `slot_native_ground` still supplies the footprint centre and
extent for its soft shadow. TV registrations separately record their nearest
base/foot contact, with their existing centre and footprint for the TV shadow.

`SlotHomeLayout.h` aligns those front edges, centres the console in the free
space to the left of the TV, and constrains the whole open-lid silhouette to the
360 px scene. The television glass dimensions and metadata typography are kept.
The scene retains its faint floor glow, contact shadows and cable.

Console scale follows its existing native-units-per-mm registration rather
than independently filling a 310 px box. SNES PAL/US: 1.6/1.55; N64: 1.5;
PSX: 1.6; Dreamcast: 1.3. Procedural NES/MD/PICO-8 use their existing physical
media scales (1.63333333/2.05504587/2.2). These are proportions for the current
artist models; PICO-8 is fictional. Panasonic and PVM use the prepared GLB's
metre scale. Retro's source is artist-scaled to about 2 m tall, so its cabinet
is explicitly approximated at 450 mm high with its proportions preserved.

All three TV PNGs are byte-identical to the preceding build. Only registration
metadata was added, using `render_tv_standard.py --registration-only`.
`tools.frontend.home_assets` refreshes home fallback derivatives from the native
2x browse cache. Targeted `stage.build(..., only=...)` preserves other families'
images and manifest entries, even when their caches have a different renderer
fingerprint. This prevents an unrelated handheld image refresh.

## Verification and reproduction

Host evidence is under `build/home-surface/`:

- 177 unit tests, input replay and the 50-cycle insertion/play/eject state test.
- `home_surface.py`: actual native-rendered bounds/contact anchors passed to
  the production C++ layout, all nine consoles × three TVs. Front edges match,
  original physical scale ratios fit without clamping, and every silhouette
  stays inside the scene.
- All 12 handheld browse/reading poses are pixel-identical, including both GBA
  SP choices. All 590 protected handheld/TV files retain their starting hashes.
- All 16 home-console finishes/paints refreshed through the native 2x renderer.
  Both finishes of every cached family were rechecked after the floor-anchor
  calculation changed; their browse pixels were identical.

```sh
python3 tools/frontend/apply.py /home/mads1/slot-es-presentation/frontend
sh tools/frontend/tests/build_probe.sh /home/mads1/slot-es-presentation/frontend build/home-surface/native-probe
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/tests/home_surface.py build/home-surface/native-probe
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py --probe build/home-surface/native-probe --all-finishes --models snes snes-us nes n64 md md-jp pico8 psx dreamcast
python3 -m tools.frontend.home_assets
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/tests/compose_home_scene.py build/home-surface/native-probe theme/art-book-slot/_slot build/home-surface/panasonic snes nes n64 md pico8 psx dreamcast
```

Host compositions use stand-in metadata text; the device captures show actual
frontend fonts and game metadata. Device results and final audit are recorded
in HANDOFF.md and section 0 of NEXT_CHAT_PLAN.md.

Device: all nine native profiles pass with GL error 0; live frontend scenes were
checked for SNES, NES, N64, MD (Cel blue), PICO-8, PSX and Dreamcast across all
three TVs. Captures are 24.5–25.5fps, 24 frames per 6×4 grid; full-resolution
metadata captures are about 18fps. PSX scene median/max: 15.830/16.882ms,
prefetch/open/reopen 258/238/196ms. Actual PSX Play/return increments playcount
exactly once (0→1, 21s), closes for one second and reopens on return. Dreamcast's
selection-only fixture was never launched and was preserved/removed afterwards.
The snapshot restored 324 data files; all 1,608 runtime files match the snapshot
plus the 621-file increment. The tested CHD hash is unchanged. Six modified/two
new data files were preserved before restore. See `build/home-surface/device/`
for the manifests and final independent audit.

All original meshes, textures, hinges, cartridge/disc seats and source licences
are retained. The soft surface cue is a composition of registered bases and
shadows; this revision does not introduce a rendered tabletop mesh.
