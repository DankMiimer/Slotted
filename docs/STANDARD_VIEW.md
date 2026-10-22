# Standard three-quarter view and the shared floor (TASK_QUEUE item 10)

**Current home-console revision:** see [HOME_SURFACE.md](HOME_SURFACE.md). The user
subsequently confirmed TVs southwest −22°, home consoles southeast +22°, front
base edges aligned with relative physical sizes, handhelds unchanged. The
centre-based home layout below is historical; its handheld reading pose remains.

Implemented and device-tested 17 October 2026. Every TV, home console and handheld reading pose now
uses one view: the native camera's **35° elevation** (`PSX_PHI`) with the object turned
**−22°** about its vertical axis (`SLOT_STANDARD_YAW_DEGREES`, `tools/slotlaunch/psx.h`). In the
inserted home-console view the console and the TV stand on **one floor line**, with contact shadows and
the cable on that floor. The user decided (17 October) that handhelds also *read* at this angle.

## What changed

- **Home consoles.** SNES/NES/N64/MD/PICO-8 already ended their insertion at −22°. PSX and Dreamcast
  (previously −8°) now use the same turn in the optical scene (`ps1-scene.h`; the disc's final yaw
  follows the console's), the camera and the projection (`SlotNative.c`). The PSX scene origin is raised
  16 px (`ps1.py`, `origin=304`) so the turned console with its open lid fits the native raster.
- **TVs.** `tools/consolebuild/render_tv_standard.py` renders each prepared TV (Panasonic, Retro) with a
  pinhole camera that reproduces `psx_project` (1200 units, 35° elevation, cabinet turned −22°, 2 image px
  per native unit). It registers the live-glass quad on the curved glass (corner depths sampled from the
  glass, then inset 9 % / 5 %), the floor contact point under the cabinet's centre and the projected
  footprint. `tools.themebuild.television` crops, records `display`, `base` and `footprint` (logical px),
  and writes them into `SlotTelevision.h`. Cabinet heights are 262 / 238 native units so each fits the
  360 px scene (Panasonic 336 × 342 px, Retro 297 × 332 px).
- **Shared floor.** The native module records each mesh's floor height and footprint at load
  (`ConsoleMesh.has_footprint/floor_y/footprint`) and `slot_native_ground()` projects the footprint centre
  and extent in the presentation pose. `SlotPresentation::prepareGeometry` chooses the floor line from the
  TV (its floor point must leave the cabinet inside the scene: y 389 for the Panasonic, 380 for the Retro),
  places the console's footprint centre on that line and scales the console to fit above and below it,
  then puts the TV's floor point on the same line at the right. `render` draws a faint floor glow
  (`stage/floor.png`), soft contact shadows (`stage/shadow.png`, both from `tools/themebuild/floor.py`)
  under both footprints, and the cable on the floor between them.
- **Handheld reading poses.** The camera's target is `console_matrix_turn`: lean to face the screen to
  the camera, then turn about the *camera's* screen-up axis expressed in the device frame, so the screen
  is skewed horizontally at any lean and never rolled (turning about the model's own vertical rolled the
  flat-modelled DS by the full 22°; turning about the world vertical rolled the leaning handhelds by ~12°). The DS reading origin is 326 (was 340) so the turned pose fits the raster.
- **Text on the angled glass.** The glass surface size is the shorter of each pair of opposite edges of the
  projected quad. `titleLines` now word-wraps to at most two lines that are guaranteed to fit (4 px inside
  the box, so `TextComponent` never wraps again; whole UTF-8 characters are ellipsised); the previous
  wrap could overlap the HUD on the narrower glass. A TV glass under 200 px wide (the Retro TV) uses a
  compact type set (×0.84).

**Not changed:** shelf browse/idle poses (−8° to −14°) and the insertion choreography keep their
angles; each insertion now *ends* in the standard view. The fallback sprites in `stage/front/` remain
front views (used only when the native renderer is unavailable).

## Trade-offs (measured)

| | live glass (px) | before |
|---|---|---|
| Panasonic | 222 × 159 | 287 × 218 |
| Retro TV | 184 × 143 (compact type) | 263 × 219 |

At the elevated, turned angle the glass is foreshortened and the cabinet must still fit 360 px, so the
TV metadata area is about 55 % of the front view's. Titles, players/year, artwork, the scrolling
description and the page footer still fit; descriptions show fewer lines at a time. Consoles are scaled
by the floor-line constraint (0.53–0.74 of native size; SNES 0.60, PSX 0.60, Dreamcast 0.74).

## Verification

- Host: 175 tests (new `tests/test_standard_view.py`); native probe `front` renders of every model
  (`build/phase-e/view/`, the probe now prints `bounds` and `ground` and saves the image even when it
  clips); `tools/frontend/tests/compose_home_scene.py` composes the inserted scene on the host from the
  probe, the TV render and the same layout arithmetic (`build/phase-e/scene/`).
- Device, real menu: SNES with the Panasonic (short and two-line titles), PSX with the Retro TV and with
  the Panasonic, GB, DS Lite, PSP and the local NeilVFX SP reading poses; 25 fps grids of the DS and PSX
  insertions (`build/phase-e/shots/view-*`). No game launched.
- Frontend `emulationstation-phase-e-g`, SHA-256
  `9e24eb5b790ed8daa7004e88e18a769bd538e3b7de50450e3fda3bb2573e1087`; helper
  `5a68a3e4242d97af42ff692acea6e8734f5fadfc2bef1f9bd8c6df25dbf48af3`; 9-file theme increment
  `build/phase-e/device/phase-e-d.tar` (TV renders/profiles, floor textures, specs, helper). Snapshot
  `views-20261017a` (324 data / 1,595 runtime): restored and audited zero changed/new; the TV setting
  and startup settings are back to their defaults.
- Previous TV renders/profiles: `build/phase-e/before-tv-stage/`, `build/phase-e/before-*-render.png`.

## Not verified / limits

- Dreamcast, N64, NES, Mega Drive and PICO-8 inserted scenes were checked on the host composition, not
  each on the device; the Retro TV was checked with the PSX only.
- The floor glow and shadows are deliberately faint on the near-black scene; there is no rendered table.
- The text surface is mapped onto the glass quad with the existing 12 × 12 bilinear grid, not a true
  projective mapping; at a 22° turn this is not visible in the device captures, but it was not measured.
