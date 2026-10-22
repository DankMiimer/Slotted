# Slotted audit and hardware spikes — 20 October 2026

This is a measured prototype checkpoint, not completion of the TV host or home
frontend/editor. The current device/installation checkpoint is TABLETOP_HANDOFF.md.

## Recovered starting point

The three relevant local Claude histories were recovered to
`build/slotted/recovered-chat/`. They confirm the decisions in SLOTTED_THEME_PLAN.md
and the unfinished Phase 0/1/2 work. A 111-file source checkpoint with SHA-256 is
retained in `build/slotted/resume-baseline-20261020/`. No authored layout JSON or
browser draft was modified by recovery or the probes.

## Dependency audit

Slotted's generated root, `_tv/` views, per-system entries and splash have no
Art Book Next include. Original procedural artwork, network/battery icons and
CC0 Raster Forge live in its own tree. The shared carousel uses retained Slot
assets and Open Sans (its OFL is in `_slot/fonts/OFL.txt`). Model licences remain
in MODEL_CREDITS.txt; this work changes none of their geometry or textures.

The old `shelf-common.xml` imports status into every view. Clock and battery
components can re-enable themselves during update, so a visibility override is
insufficient. Slotted generates `_tv/carousel.xml` from that MIT shelf, omits its
global status import and adds its own carousel status. Relative references still
resolve to the copied `_slot/` resources. The legacy source is unchanged.

Per-system entry points initialise `themePath` to their own subfolder. The root
explicitly sets it from its current include path; `/.` forces path interpolation
because this pinned engine's math evaluator retains the original `currentPath`
inside includes. Real-engine modelled and unmodelled host captures verify fonts,
frames and console art resolve. The corrected fonts, console art and single status
header were then visually verified in hardware trial `slotted-ui-20261020-210605-7e376b`.

Remaining legacy tool names are not an Art Book Next theme dependency. Upload
now targets the active supported theme; packaging/release tools still need the
Phase 6 owned-file review. Wallpapers retain their legacy customization lookup.

## Eleven full-detail consoles

Inventory: `build/slotted-phase0/inventory/inventory.{json,md}`.
Device session: `slotted-spike-20261020-204056-863e84` under
`build/slotted-phase0/device/`. This uses the current full meshes and mip chains,
the existing shared depth/camera, and generated fallback composition only. It
does not author or overwrite a home layout.

| Native scene | Triangles | Draws | Tracked GPU resources | RSS at overview | Settled overview p95 |
|---|---:|---:|---:|---:|---:|
| Eleven consoles + Panasonic + table | 306,509 | 33 | 216.3 MiB | 307.0 MiB | 4.05 ms |
| Eleven consoles + PVM + table | 379,437 | 35 | 553.6 MiB | 642.1 MiB | 3.67 ms |

The tracked GPU total is the renderer's accounting, not a whole-device memory
measurement, and must not be added blindly to RSS on this unified-memory GPU.
After a home/room round trip the PVM run peaked at 713.3 MiB RSS and tracked
578.0 MiB of GPU resources. No texture reduction, geometry LOD or model replacement
was applied. No mip-residency compromise is currently needed to fit this probe.

The static cache is fast; motion is not yet a performance acceptance pass.
PVM channel-camera movement measured p95 34.55 ms, its screen-camera stage 39.31
ms, and the initial overview's maximum 176.74 ms. Full-run maxima, including
transition warm holds, reached 216.30 ms. Long selected-console idle animation,
all TVs/tables, rapid home retargets and thermal/battery operation remain open.
The home/room prototype completed both directions without an empty-frame failure.

## Real ES view on real glass; raster decision

Hardware sessions:

- `slotted-spike-20261020-204056-863e84`: initial 720×480 ES render, middle 640×480
  copied to the TV texture.
- `slotted-spike-20261020-204506-2d1b99`: both raster alternatives, 19 captures each.

The real pinned frontend rendered system selection, gamelist scrolling and
description clipping, main menu/submenus and options into its FBO, then onto the
registered TV glass. FBO status was complete (`0x8cd5`), and every captured GL
error was 0. Device runs used real ES and its real libraries; host shims were used
only in the earlier desktop runs. The private device mount namespace replaced
only the child process's game library/configs, not the user's library.

**Choose option B: a 640×480 ES target for the TV pass.** Option A crops generic
help prompts at the right edge. B keeps the complete prompts within the glass;
its screen offset is zeroed for the FBO, and viewport/scissor flips use the target
height. This decision supersedes the previous session's provisional preference
for A. Dynamic enter/leave relayout is still Phase 4 work; the spike starts ES at
the selected logical size. The first full-screen Slotted views still use their
720×480 safe-area layout until that integration.

Direct-window and FBO captures are not universally pixel-identical: status/music
notifications can change between the two sequential render calls, in addition
to small rasterizer edge differences. No strict pixel-equality claim follows
from the working glass captures. Original captures and numeric differences are
retained. There was no real video-decoder/preview concurrency test in this spike.

## Preservation

Both hardware sessions took fresh data/runtime snapshots, audited 326 data files
and 1,720 runtime files clean, and restarted the same installed n21 hash
`db402740908cc8755015b0432721658973b801b8fc84d81a39b7e8b08786759e` with
`art-book-slot`, no game. Probe outputs and recovery records are retained.
