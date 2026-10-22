# Slotted

Standalone theme source for the pinned Knulli frontend. It has no Art Book Next
include, logo pack or font dependency. Generate the XML and original TV graphics
with `python -m tools.slotted.build`; do not edit generated XML by hand.

Slotted browses in one persistent room. Home shows the current console models
and a selectable TV. Every frontend list, collection and menu appears on that
TV; games, Ports and MPV run full-screen after launch. Each table model has a
fixed room position. Same-table layouts rearrange there; cross-table travel
follows the selected console to its saved composition. Authored close-ups stay exact.

| Control | Action |
|---|---|
| D-pad | Select physical consoles, cartridges or the TV in four directions; cartridge edges reveal the next window |
| A on a console | Open its saved cartridge layout |
| A on a cartridge | Insert or swap; a separate A on the loaded selection launches |
| B | Eject a loaded cartridge first; the next B returns home or to its originating collection |
| A on the home TV | Enter channels; Up/Down selects, A opens a list, B returns |
| R3 | Cycle authored camera views |
| L2 / R2 | Switch systems while browsing cartridges |
| L1 / R1 | Change metadata page |
| L3 | Inspect the selected cartridge |
| Start | Main menu and submenus on the TV |

Held A/B dispatch one action per press. Consoles retain loaded games across
navigation and gameplay return until explicit eject or replacement. Collections
can contain any system; modelled systems have no duplicate system channel.
Random offers separate Shuffle and Open actions.

Panasonic uses blue OSD, PVM uses broadcast green/amber, and Old/Retro TV use
teletext. TV-glass effects add subtle scanlines and a vignette. Reduced object
motion removes idle sway, rocking and landing bounce while retaining cameras,
travel paths and a small steady selection highlight.

Open **Open Scene Editor.cmd**, then **Room studio**, to edit fixed table
positions/paths, the home arrangement and its separate whole-TV camera. SNES
and Mega Drive regional pickers preserve placements. Imports open undoable
drafts; Save retains history and refuses stale overwrites. Room/home/console
batch upload is one snapshot-protected transaction with verified rollback.
Existing console JSON and browser drafts remain independent.

`python -m tools.slotted.install --package-only` creates the owned-file package.
`python -m tools.slotted.trial` runs a temporary side-by-side device trial with
snapshot/restore/audit. Permanent installation is a separate action. The existing
`art-book-slot` theme and its selected models remain available.

Use the compatible frontend from the reviewed candidate package before selecting
Slotted. A theme-only install does not provide the room runtime. Device gates,
binary hashes, remaining performance limits and current installed state are in
`docs/TABLETOP_HANDOFF.md`; a packaged candidate is not installation or acceptance.

The installer copies the current runtime `_slot/` tree without rebuilding models
or changing authored layouts. On updates it keeps Slotted's own uploaded layouts.
Use `--resync-slot` only when explicitly replacing that copy with the legacy one.
Source archives, full-detail masters and scene-layout JSON remain in the project.

Original Slotted code, procedural frames, test cards and icons are MIT. Raster
Forge is CC0 (licence in `_tv/fonts/`). The shared carousel retains Open Sans with
its OFL under `_slot/fonts/`. Model/image licences and required attribution remain
in `_slot/MODEL_CREDITS.txt` and the project's `CREDITS.md`; the theme's MIT licence
does not replace them. Local-only assets must remain local in release packaging.
