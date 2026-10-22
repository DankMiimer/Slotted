# Dreamcast and optical-disc presentation

Implemented 16 October 2026. Zerescas's CC BY 4.0 Dreamcast is integrated into
the shelf, independent presentation, baker, launch gate and standalone helper.
Original downloads remain untouched under `research/model-options-20261016/`.

## Source preparation

`tools/consolebuild/zerescas_dreamcast.py` preserves all 13 console parts,
including the lid, drive, spindle, buttons and ports. The fixed Sonic Adventure 2
disc and its entire image/material are excluded. Runtime geometry has 41,644
vertices and 36,270 nondegenerate triangles; no decimation is applied.

Registration is uniform: 190 mm enclosure width, 70.972 mm per source unit,
1.3 native units/mm. The smaller native framing keeps the fully open lid inside
the animation buffer. Final presentation framing still fits the console beside
the TV. The artist's base stays level; its drive/lid slopes about three degrees.
The independent 120-mm GD-ROM follows that plane, with its label raised 0.8 mm
to clear the drive cover at real 1.2-mm thickness. Ray checks around the full rim
verify drive and lid clearance. Hinge, spindle and plane data are generated in
`dreamcast-data.h` from the registered source.

The two 4K base-colour maps retain their independent UV spaces as 1024px tiles
in a 2048px RGBA atlas. Source print, sockets and buttons survive repainting.
Full textured masters and original maps remain in ignored `build/textured/`;
image-free registered/physical GLBs, runtime atlas and provenance are packaged.
Lighting is albedo plus the existing simple shader; no PBR, normal or ORM maps.

```sh
# WSL, Blender auto-execution disabled by the wrapper:
sh tools/consolebuild/textured.sh zerescas_dreamcast.py \
  research/model-options-20261016/dreamcast.glb dreamcast
sh tools/consolebuild/appearance-preview.sh
sh tools/frontend/tests/run_probe.sh python3 tools/frontend/render_quality.py \
  --probe build/queued-models/native-probe --models dreamcast --all-finishes
```

The generic Blender console builder preserves registered textured models;
rebuild them through their source adapter. The baker supports Dreamcast
CHD/GDI/CDI/CUE/M3U names without reading/hashing whole GD-ROMs. Per-game labels,
disc scans, regional selection, live preview and generic fallbacks are retained.

## Shared PSX/Dreamcast depth and lid behavior

The user reported tray/disc layering on both systems. The old projected SDL
disc had no 3D depth, so it painted over the tray and the lid painted over it.
`tools/slotlaunch/optical-disc.h` now draws a native annulus, underside and both
rims into the housing's depth attachment. The tray, spindle, disc and moving
lid therefore occlude each other by depth. Transparent texture pixels discard
without writing depth; SDL BGRA/RGBA artwork formats are respected. The legacy
projection remains a setup-failure fallback. Disc resources close with the scene.

Latest user instruction supersedes the old automatic lid closure in the
independent frontend: **Down inserts and leaves the lid open. Up ejects from
the open console. A/Play swaps in Highlighted if needed, animates the lid shut
and waits one second before handing off exactly one launch. Return reopens the
inserted scene.** Closure takes 0.35 seconds, followed by a closed hold through
the remainder of the one-second prelaunch interval. Controls cannot enqueue a
second game during that interval. The ordinary launch validation/owner remain.

## Verification and evidence

- 162 Linux tests, input mapping/release replay and independent state tests pass.
  State tests include the one-second close, repeated A, swap then close and
  exactly-once launch. An independent depth test places the same disc above
  and beneath an opaque tray; only the upper disc is visible. Actual PSX and
  Dreamcast source lids hide the diagnostic disc when closed.
- Both consoles have device insertion/ejection grids; Dreamcast keeps its own
  red test disc art and open lid. PSX metadata stays inside the TV glass.
- A real existing PSX game was launched after the close/one-second interval;
  return restored the open lid and same inserted disc. Dreamcast fixtures were
  never launched. Final snapshot audit: 323 data files, zero changed, zero new;
  owned fixtures/media removed, tested game data preserved before restoration.
- Final open Dreamcast probe on Mali-G31: prefetch 200 ms, first open 296 ms,
  reopen 185 ms; scene p50/p99 11.30/11.79 ms, maximum 11.97 ms, GL error 0.
  This includes native disc depth and its shader setup, unlike earlier timings.
- Device capture now supports half-resolution hardware writeback, reaching
  about 25 fps (previous full-resolution captures about 16 fps), with 6×4 grids,
  frame numbers and timestamps. Full-resolution capture remains available.

```sh
python3 capture_frames.py OUTPUT 3 --period .016667 --display \
  --display-wait .034 --capture-scale .5 \
  --grid-cols 6 --grid-rows 4 --thumb-width 240 --button down
```

Evidence is under `build/queued-models/shots/`: `dreamcast-open-insert/`,
`dreamcast-open-eject/`, `psx-open-insert/`, `psx-close-play/` and the return
capture. `timing.json` records achieved FPS; each `grid-NNN.png` holds up to
24 frames. Individual frames are retained. Hardware downscaling is only for
inspection capture and does not change the device render resolution.

Device snapshot: `dreamcast-20261016a`. Restore/audit the snapshot after tests
and remove the two explicitly owned non-playable Dreamcast fixtures. Latest
binary/hash and final device audit are recorded in section 0 of NEXT_CHAT_PLAN.
