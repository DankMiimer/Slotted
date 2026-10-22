# Selected cartridge validation — 19 October 2026

The six exact selected sources are active locally. Native host and isolated
RG34XXSP rendering tests are complete; these are not an assertion that every
physical slot is collision-free or that every authored camera frames the scene.
The N64 cartridge remains protected and GitHub publication remains on hold.

## Rendering and labels

- Refreshed the full-detail GBA after its final label crop adjustment.
- Six systems × two aspects (720×480 and 720×540), twelve distinct per-game
  labels, fifteen captures per run: **180 host and 180 device captures**.
  Overview, front/rear/quarter inspection, six insertion and five ejection poses
  all rendered successfully. All runs reported **12 labels and GL error 0**.
- The real device used **4× MSAA** at logical resolution; Mesa host rendering
  used the existing 2× supersampling fallback. No mesh reduction, source
  replacement, camera rewrite or antialiasing downgrade was applied.
- Six further private host diagnostic views point at each physical slot. Their
  insertion/ejection captures make the feed visible when the authored console
  close-up misses its newly moved console. These derived fixtures live only in
  `build/cartridge-validation-20261019/diagnostic-prepared/`; they were never
  saved to `scene-layouts/`, uploaded or used to replace browser drafts.

Evidence: `build/cartridge-validation-20261019/host-results.json`, `host/`,
`diagnostic/`, `device-report.json`, and the downloaded `device-results.tar.gz`.
The device capture contact sheet is `device/selected-cards.jpg`.

## Device scene timings

The same probe compared selected and preceding cartridges against the exact nine
installed layouts copied into a private fixture. Each sample contains 180 moving
insertion frames after 20 warmup frames, with `glFinish()` inside the measured
interval. This includes GPU completion rather than only command submission or
static scene-cache reuse. It excludes the ordinary frontend's page/UI/presentation
work and is a short benchmark, not a promise of displayed frame rate. Device
clock/temperature variation remains possible.

| System | Selected 3:2 median / p95 ms | Previous 3:2 median ms | Selected 4:3 median / p95 ms | Previous 4:3 median ms |
|---|---:|---:|---:|---:|
| DS | 19.37 / 21.06 | 14.37 | 16.99 / 17.62 | 15.17 |
| GBA | 25.13 / 35.90 | 21.73 | 25.15 / 25.57 | 22.05 |
| NES | 14.58 / 16.68 | 17.70 | 16.34 / 17.68 | 18.80 |
| GB | 16.42 / 17.20 | 18.03 | 17.14 / 19.26 | 18.40 |
| GBC | 17.33 / 17.78 | 18.98 | 17.78 / 18.21 | 17.57 |
| Mega Drive | 18.16 / 22.02 | 11.94 | 26.28 / 26.96 | 17.44 |

All **24 runs exited 0**. The accepted plan targets at least steady 30 fps, with
95th-percentile scene time within **33.3 ms**. GBA's 3:2 p95 of 35.90 ms slightly
misses that target in this sample; the other selected runs are below it. These
short scene-only measurements do not establish full frontend performance
acceptance. Full source detail is retained.

A separate opt-in back-face-culling prototype was compared across 180 host
captures, including the slot-facing fixtures. It changed GBC pixels/details and
was not adopted. Its four private GBA/MD device runs also passed and were audited,
but GBA timing did not improve consistently. The production renderer source was
restored byte-for-byte to the saved pre-experiment source. No experimental
frontend or culling policy was installed. Prototype binaries/results remain in
the ignored build directory for further source-specific investigation.

## Physical fit and authored framing

The diagnostic captures show the intended feed direction and seated/ejected
poses for all six cards. Raw triangle tests still find intersections on both
preceding and selected cartridges; topology-dependent pair counts cannot be
treated as a physical clearance score.

The read-only seat search and source-component mapping found:

- GB intersects parts of the DMG rear housing/rails; GBC intersects CGB housing.
- The DS adapter's `DS Slot-1 mouth` is a **solid black box**, not an open cavity.
  A card entering it necessarily intersects the box. Changing card position alone
  cannot establish collision-free insertion through that mesh.
- A GBA offset of −4.5 to −5 mm in console Y yields zero pairs by moving the card
  outside the case, so that apparent fix was **rejected**. The selected NeilVFX SP
  housing and cartridge were not modified to conceal the issue.
- No registration offsets, console geometry or authored object poses were changed
  by these diagnostics. True physical clearance remains open work.

The exact installed layouts also retain framing limitations: GBC clips about
5.4 px of the TV's left edge; NES and MD (the latter borrowing the SNES layout)
clip about 54 px at the right. DS's 3:2 status clips about 1.4 px at the top and
MD's about 4.7 px. GB/GBA cabinet bounds lie about 1 px beyond the left edge.
Several authored console close-ups point below/outside moved handheld consoles.
These were recorded, **not automatically reframed**. See `overview-framing.json`
and `diagnostic-cameras.json` for exact bounds/temporary review cameras.

## Device safety and reproducibility

The validation transaction `cart-validation-20261019-034535` used the shared
editor-upload lock, checked no game was running, captured the current preview
environment, stopped the frontend and made a fresh standard snapshot of **326
data and 1,697 runtime files**. All selected/preceding models and captures lived
in a private job; no theme files were deployed by validation. The final audit
found **zero changed/new data or runtime files**. The separate culling transaction
also returned a clean audit.

Both reopened the same **PSX/Panasonic** preview, with `SDL_NOMOUSE=1`. The frontend
SHA-256 stayed
`99c35406427d194b302e42bf777bfc837144958bf5c8177f6d868258c05980bd`.
The earlier portable backup `theme-user-20261019-033049` remains retained.

## Installed state

Installation transaction **`cartridges-20261019-035854`** subsequently deployed a
frozen manifest of **49 files**: eight native runtime/registration files for each
of the six cartridges and `MODEL_CREDITS.txt`. All final hashes verified. DS/GBA
already matched through independent editor uploads; NES/GB/GBC/MD and the combined
credits changed. The obsolete GBA `media.paint.mask` was removed only after its
fresh snapshot copy matched its live SHA-256. Source/master GLBs and previous
named packages were preserved; no console geometry was deployed.

Final audit: **zero changed/new data files**, nine intended runtime modifications,
24 new cartridge sidecars and one preserved-sidecar removal. No unrelated runtime
changes; all nine device layouts and the frontend hash above remain unchanged.
The same PSX/Panasonic preview and complete captured SLOT_/SDL_ environment were
verified after restart. No game was launched and no experimental binary installed.

Recovery: `/userdata/system/slot-dev/sessions/cartridges-20261019-035854/`.
The device job is under `/userdata/system/slot-dev/cartridge-installation/`;
the host payload, exact 49 hashes and final report are under
`build/cartridge-installation-20261019/cartridges-20261019-035854/`.
Installation commands are `python -m tools.consolebuild.install_selected_cartridges`
and its detached `tools/tabletop/cartridge_device_install.py` worker. The worker
uses the shared editor lock and standard snapshot/restore/audit, refuses any
manifest outside its exact cartridge/credit scope, and never binds a frontend.

Relevant commands:

```text
python -m tools.consolebuild.validate_selected_cartridges
python -m tools.consolebuild.review_cartridge_feeds
PYTHONPATH=tests python -m unittest tests.test_authored_cartridges tests.test_scene_editor tests.test_slot_presentation tests.test_handheld_models
```

The renderer commands run in WSL with the built host probe and Mesa environment
configured by their scripts. Targeted tests: **33 run, one skipped, pass**.
`tools/tabletop/cartridge_probe.cpp` is selected through the optional
`SLOT_SCENE_PROBE_SOURCE` build argument; the ordinary probe remains the default.
Device worker, requests, payload hashes, snapshots, logs and reports are retained.

## Next work

Resolve visible/physical slot occlusion against the selected console sources
without shrinking/simplifying the cards or replacing the user's models. Then
investigate source-specific GPU savings, especially GBA and MD, while preserving
the actual surface appearance. Any authored camera adjustment needs to remain a
user-controlled editor operation. Launch ownership/input behavior was not changed
by the cartridge asset work; no new game launch was needed for this validation.
