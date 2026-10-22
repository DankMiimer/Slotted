# Art Book Slot

Physical media shelves for Game Boy, Game Boy Color, Game Boy Advance, Super Nintendo, NES, N64, Genesis/Mega Drive, PlayStation, PSP, Nintendo DS and Pico-8, after
[Slot](https://github.com/BrandonKowalski/slot), on top of
[Art Book Next](https://github.com/anthonycaccese/art-book-next-es).

Every screen except the cart shelves uses Art Book Next, loaded from where Knulli/Batocera
install it (`/usr/share/emulationstation/themes/es-theme-art-book-next`). Art Book Next must be
installed; it is not included here.
Battery and percentage sit at the top left, with the clock at the top right, across system
and game views. Native insert/eject preserves that placement too.

Launch animations use original cel-shaded 3D consoles with modelled controls, connectors
and regional details. GB/GBC show the front before rotating to their rear cartridge bays;
DS and PSP reveal their card/UMD openings. Cartridge mouldings include handheld header
lettering and the DS card's latch notch and rear contacts. Regional SNES and Genesis/MD
shells follow each ROM's region.

## Install

1. Copy this folder to `/userdata/themes/art-book-slot`.
2. To carry your Art Book Next theme options over, copy
   `/userdata/system/configs/emulationstation/themesettings/es-theme-art-book-next.cfg` to
   `art-book-slot.cfg` in the same folder (ES keeps theme options per theme).
3. Main menu > User Interface Settings > Theme Set > `art-book-slot`.

GB (`gb`, `gbh`), GBC (`gbc`, `gbch`) and GBA (`gba`, `gbah`) open as shelves. **Theme
Configuration > Slot shelf: Game Boy / Game Boy Color / Game Boy Advance** switches each
family back to Art Book Next's normal list. **Slot shelf: Super Nintendo** does the same for
`snes` and `snesh`. **Slot shelf: Nintendo NES** controls `nes` and `nesh`.
**Slot shelf: Nintendo 64** controls `n64` and `n64h`.
**Slot shelf: Genesis / Mega Drive** controls `megadrive` and `genesis`.
**Slot shelf: PlayStation** controls `psx`; **Slot shelf: PSP** controls `psp`;
**Slot shelf: Nintendo DS** controls `nds`; **Slot shelf: Pico-8** controls `pico8`. The launch hooks
follow these switches too.

SNES is the first Phase 5 system, with our own Europe/Japan and North American cartridge
drawings, with shaded moulding, plastic texture and recessed screws. `(USA)` / `(Canada)`
filename tags select the North American shell; other regions and untagged games use the
Europe/Japan shell. The slot has one continuous housing, without detached side trim.

NES uses our own Game Pak drawing with the left ribbed strip, tall right-hand label and
connector notches. The two Zelda games use gold plastic. A horizontal front-loader bezel
matches its tilt, slide-in and press-down launch motion; eject reverses the sequence.
Videos replace the whole tall label with a uniformly scaled crop after three seconds.

N64 uses our own arched Game Pak with broad side shoulders, lower finger grips and a tall
central label. Its dark console deck has a top-loading mouth. North American filename tags
select verified coloured fronts, including yellow Donkey Kong 64, glitter gold Pokémon
Stadium 2, and the supported black, green and red releases; other games default to grey.
Use `cart_shell.ini` for a particular edition or custom colour. The launch motion drops the
whole cart through the slot; cropped video fills the entire printed label.

Genesis/Mega Drive uses a black shell with broad smooth Western shoulders; Japan-only filename
tags select the projecting ribbed grips. Blades of Vengeance uses the verified taller EA shell
with its yellow grip. The drawings share a 360×270 transparent canvas, keeping each body's
proportions. Each variant's video follows its complete label, including the taller EA print.
The continuous dark socket matches
the native top-loader drop and reverse eject. Hidden systems stay hidden until you enable them
in ES's system visibility settings.

PlayStation uses an original perspective CD with a thin edge, opaque printed face and open
centre bore, inspired by [Socket](https://depmots.com/socket). The console rises from the footer;
its rear lid opens, the disc lowers onto the spindle and spins briefly, then the lid closes.
Eject reverses the motion. After three seconds, optional video replaces the circular
printed face. The original metallic hub and open centre bore remain visible. A neutral
dark reflective outer rim contains no game artwork or video; its appearance is inspired
by photographed discs, without claiming the rim is physically transparent.

PS1 labels use a separate LaunchBox disc index. Region comes from the boot serial when
available, then explicit filename tags; ambiguous regions use a logo/text print. Multi-disc
scans need a known printed disc number; the four US Final Fantasy IX scans are verified.
The baker reads only the boot area of BIN/ISO/CUE tracks. If `chdman` is installed, it extracts
only that area from CHDs and caches the serial by CHD v5 raw SHA1 in
`~/.cache/slotcart/psx-identities.json`. A cached identity can also be supplied there as
`{"<raw SHA1>": "SLUS-01251"}`. CHDs are never read in full for cartridge CRCs.
Formats: CHD, CUE, BIN, ISO, IMG and PBP; unidentified containers still get fallback prints.
Each disc has a shelf PNG, opaque backing, flat `.disc.png` and fast native `.disc.tga` texture.

PSP uses a white UMD case with an opaque printed window and closed centre. Our full
cel-shaded PSP-3000 shows its curved front, controls and LCD, turns to the rear and
opens its drive door around the lower hinge. The complete UMD slides into the holder,
then the cover closes over it.
Eject reverses this motion. Video fills the circular printed window after three seconds;
the UMD case stays visible and its centre is closed.
Regional LaunchBox Disc images are cropped to their print so a photographed case does not
appear inside the drawn case. Unavailable regional scans keep a logo/text fallback. ISO, CSO
and PBP are supported; the baker reads only a small header and never checksums whole PSP images.

Nintendo DS uses an original opaque 312×341 game card with rounded corners and a recessed
label. Infrared game codes select black plastic; other cards use dark grey. Our full
cel-shaded DS Lite shows the open front, turns to its rear Slot-1 bay, then receives the
selected card label-down with a short push-and-click. The rear reveal tilts the console
to show its embossed lid and card-slot hardware. Eject reverses that sequence.
Its D-pad is a continuous cross moulding; the action, Start/Select and shoulder keys
sit close to the deck. A long lid knuckle joins the short base pivots, with narrow
collar seams, end caps, microphone and separate right-side indicator windows.
The opposite card face has 17 connector fingers. Video plays inside the printed label
after three seconds, controlled by the shared cartridge-video toggle.

DS scans use exact regional LaunchBox cartridge records. The crop follows the top branding
strip so border variations do not clip the Nintendo DS lettering. ROM hacks with no exact
art record keep their own logo or title. `.nds` and zipped `.nds` reads stop at the small
header; the baker never reads a complete DS ROM to compute a CRC.

Pico-8 uses the local 160×205 `.p8.png` cartridge artwork, including its printed credits.
It is displayed at 264×338 with nearest-neighbour scaling. Encoded alpha bits are replaced
only in the derived shelf image, keeping the displayed plastic opaque and the ROM untouched.
Text `.p8` cartridges use their 128×128 `__label__` section; Splore has an original browser
label, and missing artwork uses the usual logo/text fallback. Your own label overrides
still take priority. The original red and charcoal 3D fantasy console rises, turns and
receives the upright cart. Video plays inside the square label after three seconds if
available, controlled by **Slot cartridge video**. Scrolling uses the shared 650 ms slide.

Carts show the game's logo (or its name) on a plain shell until a baked cart exists at
`<rom folder>/media/slotcarts/<rom name>.png`.

## Bake cartridges

On the device:

```sh
cd /userdata/themes/art-book-slot/_slot
python3 -m slotcart
```

The baker reads GB/GBC/GBA ROM headers for shell colours and finishes, and SNES filename region
tags for its physical shell. Labels come from
your own `<rom folder>/media/labels/<rom name>.png` (or `.jpg`, as Skraper saves some scans), then
the Slot art set by ROM CRC for handhelds or regional LaunchBox cartridge artwork for SNES/NES/N64/MD/DS,
then a logo (`media/wheels/<rom name>` or the scraped marquee), then a generated text
label. Cart Studio's `cart_shell.ini` overrides work
in the same labels folder. Downloads and CRCs are cached; unchanged carts are skipped.
Use `--systems gba`, `--offline`, `--force`, `--jobs N` or `--dry-run` as needed.
Game art is downloaded or read from local Pico-8 carts on your device and is never part of
the theme package. Pico-8 `.png`, `.p8` and `.m3u` entries are supported without ROM CRCs;
the baker reads bounded label data and never executes Lua.

SNES/NES/N64/MD/DS match exact titles and alternate names in [LaunchBox's public metadata](https://forums.launchbox-app.com/topic/30123-launchbox-games-db-external-scraper/).
It prefers **Cart - Front**, then **Fanart - Cart - Front**, cropping the printed label from a
front-on cartridge image. North American, Japanese and European artwork follow the ROM tags;
missing regional art keeps the logo/text fallback. Each platform has a separate index and crop
cache; a metadata archive is shared between refreshes. Ambiguous titles are skipped. Cropped labels
and their source records are cached in `~/.cache/slotcart/launchbox/`, so offline reruns work.
The first console run downloads the metadata archive; subsequent runs reuse the platform index.
Changing a console shape automatically invalidates its baked carts, while leaving handheld carts
up to date.

Existing mixed SNES/Genesis libraries also need their baked shell markers when updating
from the older video layout. The baker maintains these automatically. To add them without
downloading or rebuilding existing labels:

```sh
cd /userdata/themes/art-book-slot/_slot
python3 -m slotcart.surfaces --roms /userdata/roms
```

An offline PS1 bake detects the revised rim material and refreshes derived discs while
keeping cached label sources. Source game artwork is never included in the theme.

N64 supports `.z64`, `.n64`, `.v64` and ZIP dumps. Byte order is normalised for header reading;
ROM files are never rewritten. Different formats with the same stem share one cart image,
using the richest available label plan, including on cached reruns. Remote PNGs with invalid
ancillary metadata are decoded without that metadata; damaged image data retains the fallback.

Genesis/Mega Drive supports `.md`, `.bin`, `.gen`, `.smd` and ZIP dumps. Raw Sega headers supply
the domestic title; copier dumps use their filename for shell selection. ROM files remain
unchanged. Use `--systems megadrive` to bake this family alone, or `--labels-dir` with an `MD/`
folder for your own printed labels.

## Label art and previews with Skraper

The shelf looks best with a real label on every cart and a gameplay preview for the
selected game. [Skraper](https://www.skraper.net/) with a free
[ScreenScraper](https://www.screenscraper.fr/) account fetches both. The theme uses three
ScreenScraper media: **support texture** (the flat printed label or disc print), **wheel**
(logo, used only when no label exists) and **normalized video** (the preview).

1. In Skraper, sign in and add your systems, pointing at the handheld's ROM folders
   (for example `\\KNULLI\share\roms`). Then **close Skraper**.
2. Add the theme's media to your existing setup. With Python on your PC, run:

   ```
   python \\KNULLI\share\themes\art-book-slot\_slot\skraper\apply_preset.py C:\path\to\Skraper\skraper.config.json
   ```

   It keeps your other media, login and settings, backs up the config, and adds for Game Boy,
   GBC, GBA, SNES, NES, N64, Mega Drive/Genesis, PlayStation, PSP and DS:
   support texture → `%ROMROOTFOLDER%\media\labels`, wheel → `%ROMROOTFOLDER%\media\wheels`,
   and (unless you already download a video) normalized video → `%ROMROOTFOLDER%\media\videos`,
   linked in the gamelist. Without Python, add the same three entries per system on Skraper's
   **Media** tab: untick resizing, and set **Gamelist link** to *No link* for the two images.
3. Scrape. Then on the handheld, with ES stopped if Skraper did not write your gamelists:

   ```sh
   cd /userdata/themes/art-book-slot/_slot
   python3 -m slotcart.previews link     # only needed if videos are not linked yet
   python3 -m slotcart                   # bake the new labels into carts
   ```

`slotcart.previews link` adds a `<video>` only for games that have no working video, keeps
every other gamelist field (names, play counts, favourites) and writes a journal;
`python3 -m slotcart.previews restore <journal>` undoes it. The shelf needs that link: this
frontend does not search for preview files by name.

ScreenScraper labels follow your ROM's region first, so PAL ROMs get PAL labels for the
PAL shells. Console labels are fitted whole into the label well, keeping licence strips and
seals. DS previews show the top screen. Previews play silently, so the audio track and full
480p resolution only take space: the source repository's `tools/skraper/place_media.py`
converts clips to silent shelf-sized copies (about a fifth of the size) if storage matters.

## Shelf options

- **Slot cartridge video:** on by default. The selected ROM's scraped video plays silently
  across its complete label after three seconds. Each physical surface clips the video;
  one uniform scale fills it by cropping, preserving the source's display proportions.
  Scrolling stops the preview and resets the delay, including games sharing one clip.
  With no video, the original label stays visible. Turn it off in Theme Configuration.
- **Slot wallpaper:** off by default, giving a plain black background. To use your own PNG,
  put it at `/userdata/theme-customizations/art-book-slot/wallpaper.png` and enable the
  option. `<system theme>.png` in that folder takes priority for that system. A 62% black
  scrim keeps it dim. Opaque silhouette backings keep wallpaper from showing through carts,
  including the dimmed neighbours and clear shells.
- **Slot save-state photo:** off by default. The newest screenshot for the selected ROM
  appears beside its cart; ROMs without one show no photo. The baker prepares these photos
  in `<rom folder>/media/slotstates/`. Refresh them without downloading or baking cart art:

  ```sh
  cd /userdata/themes/art-book-slot/_slot
  python3 -m slotcart.states
  ```

  Installed launch hooks refresh that game's photo when it exits. Original state files are
  only read. Reload the theme after refreshing photos while ES is running.

The shelf name stays dim and steady in the slot, avoiding a fade replay after every game.
Each cartridge has one moving face; neighbours use colour shading at 55% brightness, staying
opaque during slides. Selected cartridges return at full brightness when a game exits.
Slides last 650 ms, roughly 39 display opportunities at 60 Hz. Actual frame pacing depends
on the frontend and media workload.

On Scarab's tested frontend, use **Default** power saving with delayed previews. Enhanced
power saving can put ES into a blocking input wait before the three-second timer fires,
leaving a preview stopped until another input. Default retains idle power saving while
letting the timer run. This setting was applied on the development handheld; copying the
theme alone does not change it.

That frontend also ignores non-square video pixel metadata. Such clips need square-pixel
preview copies to retain their intended display proportions. The repository's
`tools/dev/prepare_video.py` and journalled installer prepare and link copies while keeping
original videos intact. Ordinary square-pixel videos require no conversion.

## Launch animation

The ARM64 helper must be present at `_slot/launch/slot-launch`. Developers can build it with
`tools/slotlaunch/build.ps1` in the source repository.

```sh
python3 /userdata/themes/art-book-slot/_slot/launch/install.py install
```

Set **User Interface Settings > Game launch transition > Instant**. The hooks animate only
Art Book Slot's GB/GBC/GBA/SNES/NES/N64/MD/PS1/PSP/DS/Pico-8 carousel views. Keep the hooks installed when switching themes;
their theme and shelf checks stop them running on other views. Instant is an ES-wide setting.
If launching only fades or zooms, check that all three hooks are active:

```sh
python3 /userdata/themes/art-book-slot/_slot/launch/install.py status
```

Then check that the game launch transition is Instant. Copying or selecting the theme alone
does not install native launch hooks. To remove
the hooks:

```sh
python3 /userdata/themes/art-book-slot/_slot/launch/install.py uninstall
```

The selection hook maintains a sleeping launch watcher. It starts insert when ES confirms a
launch, before audio shutdown; the game-start hook is a fallback. On exit, the helper retains
the final shelf on a separate Sunxi display layer through ES's display rebuild and releases
it when the frontend redraws. This RG34XXSP handoff has a five-second timeout; other displays
retain the ordinary eject. The cartridge clears the visible slot completely,
then the whole launch scene fades together.

On the tested Knulli build, disabling **Check BIOS files before running a game** reduces the
delay before insert. This is an optional ES setting; the installer does not change it.
Manual BIOS checks remain available. Keep the normal ES window-hiding behaviour.

Uninstall removes only the three Art Book Slot hook files and stops its watcher. The helper
is currently tested on RG34XXSP / Knulli at 720×480.

## Credits and licences

- Theme XML, generated art and icons: MIT (`LICENSE`).
- Cart outlines, moulding and insert/eject sounds: Slot by Brandon T. Kowalski, MIT, from its
  last MIT release (`_slot/LICENSE-slot-mit.txt`).
- SNES/NES/N64/MD shells and housings, PS1 disc/console and PSP UMD/rear-door geometry and materials: our own art.
- SLOT2 MIT reference assets are retained in the source repository for later systems.
- Open Sans: SIL Open Font License (`_slot/fonts/OFL.txt`).
- Raster Forge by GGBotNet: CC0 (`_slot/fonts/RasterForge-LICENSE-CC0.txt`), with empty hinting
  tables added so it renders on its pixel grid in ES.
- Art Book Next by Anthony Caccese (CC BY-NC-SA 2.0) is used at runtime, not redistributed.
- SDL2 and SDL2_image are used from the device's installed runtime, not redistributed.
- Label art is fetched from Slot's art set (ScreenScraper sources) and the LaunchBox Games
  Database; game art is not included.
