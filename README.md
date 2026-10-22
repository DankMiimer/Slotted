# Slotted

A 3D tabletop theme and frontend extension for Knulli / Batocera EmulationStation.
Browse physical consoles and cartridges in a room, insert a game, and launch it
with a second press. Lists, collections, settings and metadata appear on the TV.

**Open-source code (MIT), with separately licensed model assets.** You may use,
modify, redistribute and sell the original code while retaining its MIT notice.
Models, fonts, sounds and their derivatives keep their own licenses. Some included
models prohibit commercial use; see [license scope](LICENSE_SCOPE.md) and
[credits](CREDITS.md) before redistributing assets or screenshots.

This is a **development source release**, primarily tested on the Anbernic
RG34XXSP with Knulli. The persistent room requires this project's custom frontend
at the [pinned upstream source](https://github.com/knulli-cfw/batocera-emulationstation/tree/4041b56a714265de81de8165b34fbd10f313a891).
Copying theme XML to stock EmulationStation does not add the room renderer.
Other devices and upstream versions need their own validation. No firmware,
frontend binary, ROM, BIOS, save, or downloaded game artwork is supplied.

## Features

- Eleven tabletop systems: GB, GBC, GBA SP, SNES, NES, N64, Mega Drive / Genesis,
  PlayStation, PSP, DS and PICO-8, including regional/model alternatives.
- One persistent room, fixed positions for each table model, and travel between
  authored layouts. Loaded games remain inserted until ejected or replaced.
- Frontend menus on the TV, with Panasonic OSD, PVM broadcast and teletext
  styles, plus CRT effects and reduced-motion settings.
- A browser scene editor for consoles, cartridges, cameras, home, room positions
  and room surfaces. Saved JSON, undo, browser drafts and history are preserved.
- Cartridge/disc artwork tools and snapshot-protected device upload tooling.

## Controls

| Input | Action |
|---|---|
| D-pad | Select consoles, cartridges or the TV spatially; cartridge edges reveal more games |
| A on a console | Open its cartridge layout |
| A on a cartridge | Insert/swap; a separate A on the loaded game launches |
| B | Eject first, then leave the console layout on the next press |
| A on the home TV | Enter channels; Up/Down chooses, A opens, B goes back |
| R3 | Cycle authored cameras |
| L2 / R2 | Switch systems in cartridge browsing |
| L1 / R1 | Change metadata page |
| L3 | Inspect a cartridge |
| Start | Main menu on the TV |

Games and external apps run full-screen after normal launch validation. A held
button does not trigger both insert and launch. Collection navigation remembers
its origin and selected game.

## Start developing

Use Python 3.11 or newer, Git, and the dependencies in
[`requirements-dev.txt`](requirements-dev.txt). From the public source export:

```sh
python -m pip install -r requirements-dev.txt
python -m tools.publication.restore_assets
python tools/tabletop/editor/server.py
```

Open [the local editor](http://127.0.0.1:8765). Its first start downloads pinned
Three.js modules and retains their MIT license. Asset restore copies verified
public assets into build paths and refuses to overwrite differing files.
It never connects to a handheld. Keep your own scene JSON and browser drafts.

The Slotted XML/TV graphics can be regenerated with:

```sh
python -m tools.slotted.build
python -m tools.slotted.install --package-only
```

The second command packages theme files locally. It does not provide the custom
frontend or a complete first-time device installation. See
[development setup](docs/DEVELOPMENT.md) for the ARM64 toolchain,
native dependencies, source pin, device configuration and current limitations.
Keep a working theme and firmware backup while testing.

## Project layout

| Path | Purpose |
|---|---|
| `theme/slotted/` | Standalone Slotted theme; no Art Book Next dependency |
| `theme/art-book-slot/` | Retained legacy theme and shared `_slot` assets/tools |
| `tools/frontend/` | Source-pin-specific patches and room renderer |
| `tools/tabletop/editor/` | Local scene editor and transactional uploads |
| `scene-layouts/` | Durable authored profiles and history |
| `tools/consolebuild/`, `tools/themebuild/` | Model processing and art generation |
| `third_party/` | Prepared sources, provenance and upstream notices |
| `assets/` | Verified public build assets, present in the public export |
| `release/` | Publication allowlist and model license index |

Legacy Art Book Slot uses Art Book Next at runtime; that external theme is
CC BY-NC-SA 2.0 and is not bundled. Its
[older overview](docs/LEGACY_README.md) is historical; Slotted's controls above
are current. Some older design documents describe superseded prototypes.

## Reuse and contributions

Read [LICENSE_SCOPE.md](LICENSE_SCOPE.md), [CREDITS.md](CREDITS.md) and the
[asset index](release/model-licenses.json). Retain attribution, source links,
license texts and modification notices with reused assets. CC BY-NC-SA adaptations
remain under CC BY-NC-SA; they are not relicensed MIT. Hardware names/logos and
third-party game artwork do not become project-owned through a model license.

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and
[PUBLISHING.md](PUBLISHING.md) for generating a clean, verified GitHub upload.
