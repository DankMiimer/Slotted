# Art Book Slot

See [credits and asset licences](CREDITS.md) for creators, source links and
restrictions, and the [user request queue](TASK_QUEUE.md) for current work.

The [complete next-chat plan](docs/NEXT_CHAT_PLAN.md) records the queued model
replacements, TV choices, accepted behavior and implementation/verification order.

The [2026-10-16 presentation implementation](docs/SLOTTED_PRESENTATION_IMPLEMENTATION.md)
adds independent Down/Up slotting, continued Left/Right browsing, swap-before-Play,
a top-quarter cartridge wheel, Panasonic CRT/handheld LCD metadata, auto-scrolling
descriptions and current full console models. It is opt-in and requires the
pinned custom frontend; the official frontend keeps its existing behavior.
See the [accepted plan](docs/SLOTTED_PRESENTATION_PLAN.md) and
[TV model research](docs/TV_MODEL_RESEARCH.md) for decisions and limitations.

A theme add-on for Knulli and Batocera (Batocera EmulationStation) that turns game libraries
into shelves of physical cartridges, discs and UMDs, after
[Slot](https://github.com/BrandonKowalski/slot). Every other screen stays
[Art Book Next](https://github.com/anthonycaccese/art-book-next-es), which the add-on loads from
where the OS already installed it.

**Status:** GB/GBC/GBA shelves, the cart baker, native insert/eject and Phase 4 polish are
complete and tested on RG34XXSP. Video previews play inside the selected cart after three
seconds, with a toggle. The default background is black and cart silhouettes stay opaque.
Battery and clock sit at the top in every theme view and during native launch/return.
Phase 5 is complete: regional SNES shells, NES Game Paks, N64 and Genesis/Mega Drive cartridges, plus PS1 discs, PSP UMDs, DS game cards and Pico-8 carts, with downloaded
labels and matching top-loader/front-loader motion. Launch starts before ES's audio shutdown;
the shelf stays visible during the return handoff, and the whole cart clears the slot before launch.
Launch hooks stay installed, and ES's game
launch transition must be Instant. See [PLAN.md](PLAN.md), [HANDOFF.md](HANDOFF.md)
and the [theme's usage instructions](theme/art-book-slot/README.md).

The current quality cycle adds full-label cropped previews, a PS1 disc preview with its
hub, open bore and neutral outer rim preserved, and 650 ms selection slides. The
[implementation evidence](docs/IMPLEMENTATION_PROGRESS.md) records device checks and
the normal power-saving setting needed for reliable three-second previews on Scarab.
Measured model accuracy, internal scroll pacing and immediate post-eject input remain
open. The [refined implementation proposal](docs/IMPROVEMENT_PLAN.md),
[current analysis](docs/IMPROVEMENT_ANALYSIS.md) and [frontend/theme research notebook](docs/FRONTEND_RESEARCH.md)
track this work. The visual direction is accurate hardware with restrained cel shading.
Packaging follows those improvements.

Cartridge systems have original cel-shaded 3D consoles with black outlines and three shadow
bands. GB/GBC show the front, turn to the rear slot, and receive the selected cartridge.
Both SNES housings, NES, N64, Mega Drive and an open GBA SP have matching physical loading
motion. Tap scrolling uses a gentler 650 ms slide. Editable models and rebuild instructions
are in [tools/consolebuild](tools/consolebuild/README.md).

DS has an original game-card shell and a full cel-shaded DS Lite. Its open front turns
to reveal Slot-1; the selected card flips label-down, slides in and clicks into place.
Regional cartridge scans preserve the complete printed label, with logo/text fallbacks
for unavailable art and ROM hacks. Native and zipped DS reads are limited to the header.

Pico-8 preserves the original PNG cartridge's pixel artwork and credits, with opaque plastic
and nearest-neighbour scaling. Text `.p8` labels are read without executing the game;
Splore gets an original browser label. An original red and charcoal cel-shaded fantasy
console receives the cart. Shelf and delayed-video toggles work like the other systems.

Build the generated parts of the theme with `python -m tools.themebuild` (Python 3, Pillow,
numpy, resvg_py, ffmpeg on PATH).
Build the native ARM64 launch helper separately with `tools/slotlaunch/build.ps1` before
copying the theme; its binary is generated and is not checked into git.

PS1 uses [Socket](https://depmots.com/socket) as its main inspiration, with our own perspective
disc, rear-hinged lid and spindle model. Regional labels, disc-number matching, video previews
and native insert/eject are installed and tested on the handheld. The original design preview
is still available through `python -m tools.discpreview.preview`; see
[the research and validation notes](tools/discpreview/README.md).

PSP now has our own full cel-shaded PSP-3000, including its curved shell, controls,
ports and bottom-hinged UMD drive. It shows the front, turns to the rear, loads the
complete case and closes the cover. The refined DS buttons and hinge and both full
console models are installed on the RG34XXSP. Its separate regional
disc-art index supplies printed labels; missing regional artwork uses a logo or text. ISO, CSO and
PBP containers are read only for their small header, without full-file CRCs.

## Layout

| Path | What |
|---|---|
| `theme/art-book-slot/` | the theme set that gets copied to `/userdata/themes/` |
| `tools/themebuild/` | generates the theme's art, icons, shelf views and per-system files |
| `tools/dev/` | dev loop against a handheld over ssh: push, restart ES, inject input, screenshot |
| `tools/slotlaunch/` | native SDL2 insert/eject helper and its cross-build scripts |
| `tools/discpreview/` | local Socket-inspired PS1 disc appearance and motion study |
| `tools/consolebuild/` | original cel-shaded console geometry, editable models and idle renders |
| `spikes/` | Phase 0 experiments and their results |
| `third_party/slot-mit/` | Slot artwork and sounds from its last MIT release |
| `third_party/slot2-mit/` | pinned MIT reference assets for later systems |

## Credits and licences

- Our code and artwork: MIT (see `LICENSE`).
- Cart outlines, moulding and insert/eject sounds: Slot by Brandon T. Kowalski, MIT, from commit
  `1a655b8` (the last MIT release; later Slot releases are GPL-3.0 and nothing from them is used).
  See `third_party/slot-mit/`.
- SNES/NES/N64/MD/DS shells and console models: our own drawings and geometry. SLOT2's MIT reference assets are pinned
  in `third_party/slot2-mit/` for later systems.
- Open Sans: SIL Open Font License.
- Raster Forge by GGBotNet: CC0 (`third_party/raster-forge/`).
- Art Book Next by Anthony Caccese (CC BY-NC-SA 2.0) is required at runtime and is not
  redistributed here.
- No game artwork is included. Labels are fetched or read from local Pico-8 carts on the user's own machine.
