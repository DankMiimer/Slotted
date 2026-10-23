# Credits and asset licences

Model assets retain their own licences. The project's MIT licence covers its
original code/geometry; it does **not** relicense the third-party models below.
Attribution applies to modified models and their derived render images too.
No creator or hardware manufacturer endorsement is implied.

## Public source edition (23 October 2026)

Read [LICENSE_SCOPE.md](LICENSE_SCOPE.md) for the code/asset boundary and
[`release/model-licenses.json`](release/model-licenses.json) for source records
and affected file families. Full CC legal texts are in `LICENSES/`. MIT notices
for pinned Slot/SLOT2 and OFL/CC0 font notices stay beside those files.

The retained selected **GB housing (Bram Verheyen)** and **Retro TV (Denys
Hroshko)** are CC BY-NC 4.0. The **N64 cartridge (Chris Sweetwood)** and **TV
stand (Qu3st10n)** are CC BY-NC-SA 4.0. Their textures, adapted geometry and
derived images retain those conditions. Project contributions to these SA
adaptations are distributed under the same CC BY-NC-SA 4.0 terms. Independent
tools/code retain MIT. Commercial reuse of the complete supplied art bundle is
not granted by the root license.

The six 19 October cartridge selections below are now integrated: Bob (GB),
Wikiti (GBC), thegraphicsgeek (GBA), satchii_ (NDS), dark_igorek (NES) and
Nerd_Sp (MD), all CC BY 4.0. Earlier cartridge sources/masters remain available
as credited alternatives/history. Older references to a preceding runtime model
are historical, not a new selection.

The public exporter excludes the NeilVFX editorial SP and all local derivatives,
unlicensed previews, games/BIOS, user library art and private device data. Their
local originals and the user's model choices remain preserved. Furniture source
GLBs, prepared runtime room assets, full-detail theme masters and authored scene
profiles are included through explicit, hash-checked publication inputs.

Upstream [EmulationStation at the pinned source](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/LICENSE.md)
credits Alec Lofquist, MIT. Its notice is preserved in
`LICENSES/EmulationStation-MIT.txt` for upstream excerpts used in the patcher.
Native dependencies keep their own notices; no compiled frontend is exported.

17 October 2026 scene revision: derived home-console renders face southeast (+22°);
the TVs retain their southwest (−22°) renders. Front base edges and relative sizes
are registered for the shared surface. The Retro TV uses an approximate 450 mm
cabinet height because its source scale is not physical. Individual asset licences
and the noncommercial/ShareAlike terms below still apply to these render images.

| Asset / creator | Source | Licence | Usage |
|---|---|---|---|
| Wooden Table — lena-wachs | [Sketchfab](https://sketchfab.com/3d-models/wooden-table-e4a9129ea0114d3e8d1989971eca53ef) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Experimental shared 3D tabletop. Official GLB and original FBX archive preserved in `research/table-lena-wachs/`; top slab/trim retain 112 source triangles, original UVs and 4K albedo, with a uniform physical registration. Legs omitted from the runtime view. Shipped as `_slot/tabletop/table/` in the 18 October SNES tabletop development build; credited in `_slot/MODEL_CREDITS.txt` |
| GameBoy DMG-01 — Let's Do 3D | [Sketchfab](https://sketchfab.com/3d-models/gameboy-dmg-01-29849a15fe0a40a6a18e01c9d544a0ed) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | GB Game Pak (`consoles/gb/media*`), its shelf/hero renders. The former DMG housing is superseded by Bram Verheyen's Gameboy Classic below |
| PSP 3001 — JSJetStream14 | [BlendSwap](https://blendswap.com/blend/14767) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | Preceding PSP housing; prepared source retained for reproduction, no longer the runtime housing (superseded by Ilya Ostrovsky's Sony PSP) |
| Game Boy Color — Wikiti | [Sketchfab](https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Preceding GBC model; prepared source retained for reproduction, no longer the runtime housing |
| Game Boy Color Model — BPoole | [Sketchfab](https://sketchfab.com/3d-models/game-boy-color-model-a3dad19c800f4c61a931865f14870768) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Runtime CGB housing and base-colour atlas (`consoles/gbc/`), all CGB renders. Fixed Game Pak/hidden contacts removed, cover seated, screenshot blanked, unused texels cleared; see `third_party/models/bpoole-cgb/source.json` |
| Gameboy Advance SP / Pokemon Cartridge — thegraphicsgeek | [SP](https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f), [cartridge](https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | SP installed as a textured model (17 October 2026), selectable as **thegraphicsgeek** in the theme setting "Slot GBA SP model": all 66,784 visible source triangles (two transparent lens overlays dropped), source UVs and its three 1024 px base-colour maps packed at native resolution in one 2048 px atlas, footprint corrected to Nintendo's published 82 × 84.6 mm, source opening angle kept, the cartridge-bay roof raised 1.7 mm so the registered Game Pak clears it. **The hinge axis is a registration** (no source mechanism). Simple lighting, no PBR. See `third_party/models/graphicsgeek-ags-textured/source.json`. The earlier reduced vertex-colour derivative and the cartridge are retained for reproduction only. Separate from the local NeilVFX model |
| GBA cartridge CAD — Dave Parker | [Printables](https://www.printables.com/model/190861-gameboy-advance-cartridge-gba-cart) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Preceding fitted GBA Game Pak; source retained for reproduction, superseded by the user-selected Vxcl shell |
| Super Nintendo PAL — quick_loop (@so_O) | [Sketchfab](https://sketchfab.com/3d-models/super-nintendo-d42c35b117974ade8842f0964f5fd59e) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | PAL/SFC housing and renders |
| Super Nintendo US — Steven H. Tran (@ibbqcats) | [Sketchfab](https://sketchfab.com/3d-models/super-nintendo-console-41c9dd1f5a53493cbe2e00a190150e93) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | US housing and renders |
| Nintendo 64 — Joseph Rohm | [Sketchfab](https://sketchfab.com/3d-models/nintendo-64-0bec1e1ed1bf4a96af858008b72437a3) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Housing, articulated flaps and renders |
| Sony PVM-1341 / PlayStation — dark_igorek | [Sketchfab](https://sketchfab.com/3d-models/sony-pvm-1341-sony-playstation-5f80311f1a4646ef9673f20ee6dc6245), [original short link](https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Textured PSX console/lid, 64,717 source triangles without decimation; existing hinge/disc registration retained. Sony PVM-1341 TV theme choice with source maps and blank live glass; loose power lead/plug excluded. Full original/master preserved; prior image-free console retained for reproduction |
| Panasonic CRT TV (1990s) — DamianToons | [Sketchfab](https://sketchfab.com/3d-models/panasonic-crt-tv-1990s-45f7728e4f534d9393ef1d681137b6d9) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Blank live TV, prepared model and renders |
| TV, Old TV, Retro TV — Denys Hroshko | [Sketchfab](https://sketchfab.com/3d-models/tv-old-tv-retro-tv-f13b9a45c0d649dc90ebac5f7717cebf) | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | Selectable "Slot TV model" (`stage/tv/retro.png`); blank live glass, cabinet maps kept. **Noncommercial** restriction applies to its render and derivatives |
| Old TV — pibanezl (@hypermegadev) | [Sketchfab](https://sketchfab.com/3d-models/old-tv-833d046f00394fb1a69514b3c96e86bd) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Added 18 October 2026 as a selectable "Slot TV model" and tabletop TV: all 2,770 source triangles, UVs and 2k base-colour maps; uniformly scaled to a 14-inch set (tube face = 13.2-inch / 335 mm viewable diagonal; cabinet 442 x 302 x 261 mm); the tube face is blank live glass. Downloaded GLB in `research/tv-pibanezl-old-tv/`, prepared model `third_party/models/pibanezl-old-tv/`, renders `stage/tv/oldtv.png` |
| Sega Dreamcast — Zerescas | [Sketchfab](https://sketchfab.com/3d-models/sega-dreamcast-f82d99e4739e42f4abfc37cb97918cfc) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Installed: all 13 console parts, 36,270 triangles, source albedo/UVs in a 2048px atlas, registered moving lid and sloped disc seat; independent per-game disc artwork. Fixed Sonic disc and its image excluded; simple lighting, no PBR |
| Sony PSP — Ilya Ostrovsky | [Sketchfab](https://sketchfab.com/3d-models/sony-psp-dca89d10ec304d0cab76837750df7761) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Installed (17 October 2026): all 58,250 source triangles (ground plane removed, 58,676 after splitting the rear cover at its straight seams), source UVs/albedo (4096px reduced to 2048px), baked home screen blanked for the live LCD. Separately hinged UMD cover plus concealed drive floor, lining and holder rails are original MIT fittings; **the hinge is a fitted approximation** (the source has no mechanism). Simple lighting, no PBR. See `third_party/models/ostrovsky-psp/source.json` |
| Gameboy Classic — Bram Verheyen | [Sketchfab](https://sketchfab.com/3d-models/gameboy-classic-854c46e14ce24779ad64ae74cb9b9089) | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) | Installed (17 October 2026): all 9,856 source triangles, source UVs and cosmetic wear/sticker kept (4096px albedo reduced to 2048px), tilt undone, separate planar LCD for live metadata, Game Pak registered to the measured bay floor and rear lip. **Noncommercial** restriction applies to the model (`consoles/gb/`), its atlas and every derived GB render. See `third_party/models/verheyen-dmg/source.json` |
| Nintendo DS Lite — Cianon | [Sketchfab](https://sketchfab.com/3d-models/nintendo-ds-lite-ca529eb7208746e89b7a28fd2246659d) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Installed (17 October 2026), superseding the earlier DSi choice and the procedural DS Lite housing: all 1,158 visible source triangles (the fully transparent 28-triangle glass overlay is dropped), source UVs and 2048px base-colour atlas, both screens split out and blanked for live metadata, the fixed game-card picture painted on the Slot-1 notch cleared. The lid is registered about its own knuckle and opened from the source's 125° to the 145° presentation pose; **the hinge is a fitted registration** (the source has no mechanism and its hinge ends interpenetrate by design). The dark Slot-1 mouth is an original MIT fitting. Simple lighting, no PBR. See `third_party/models/cianon-ds-lite/source.json` |
| Super Nintendo Cartridge — SomeKevin (UVs: cpt.brotzeit) | [Sketchfab](https://sketchfab.com/3d-models/super-nintendo-cartridge-b2076d8a65d648ff99bf51ca9d5fca2a) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | PAL SNES cartridge, all 33,839 triangles and source UVs; source sticker cleared, curved per-game label; matching shelf renders. US shell retained |
| Game Cartridge (Tzakol in Exile) — kutejnikov | [Sketchfab](https://sketchfab.com/3d-models/game-cartridge-tzakol-in-exile-49251a57f2c9418faec314a5a5ab7ee9) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Selectable SNES cartridge style, 216 triangles, source UVs/colours; depth fitted to bay, game label/title cleared; per-game labels and matching shelf renders |
| Gameboy Advance Cartridge — Vxcl | [Sketchfab](https://sketchfab.com/3d-models/gameboy-advance-cartridge-38c1e6702e5d4f21af1d0930689b1d10) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | GBA Game Pak and shelf renders; two shells, board, screw and independent per-game sticker. 1,522 nondegenerate triangles, uniform registration; Mario Kart image excluded |
| Song Of Morus: pico-8 cartridge — sunnychow | [Sketchfab](https://sketchfab.com/3d-models/song-of-morus-pico-8-cartridge-fc89d8b44a934400bdf282600f61d369) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 438-triangle shell, board/contacts and shelf renders; depth fitted to existing slot, original 128px albedo retained without enlargement. Fixed art/credits cleared; each game's art/credits remain its own |
| Nintendo 64 Cart — Chris Sweetwood | [Sketchfab](https://sketchfab.com/3d-models/nintendo-64-cart-7b93f9cb196743009c2211a5e47643d8) | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | One upright 1,050-triangle cartridge and its shelf renders; two posed duplicates excluded, original plastic map retained, fixed Diddy Kong Racing image excluded. Attribution, noncommercial and ShareAlike terms apply to this shell and render images containing it |

Detailed changes and asset scope for the installed baseline are in
[`MODEL_CREDITS.txt`](theme/art-book-slot/_slot/MODEL_CREDITS.txt), shipped with
the theme. Source hashes and modifications are also retained in per-model
`source.json` / `model-info.json` files. New source inspections preserve the
original meshes, UVs and texture files before any adaptation.

## Local-only and unavailable sources — not CC assets

- **Gameboy Advance SP — NeilVFX / nvfx**, [CGTrader](https://www.cgtrader.com/free-3d-models/electronics/other/gameboy-advance-sp):
  **Editorial License (no AI)**. User-supplied local source and derivatives,
  excluded from the redistributable CC/MIT model bundle. Adaptation: uniform
  physical registration, separate lid/LCD, per-part runtime reduction, explicit
  colours and source-logo translation. Full original geometry is preserved.
- **Nintendo Gameboy Advance SP Zelda — shrednector**, [Sketchfab](https://sketchfab.com/3d-models/nintendo-gameboy-advance-sp-zelda-faa74a9aad5f49bdbb8a5b90ddb0d58a)
  and **Nintendo 64 Cartridge (PBR version) — NeoZeroo**, [Sketchfab](https://sketchfab.com/3d-models/nintendo-64-cartridge-pbr-version-047280dd0a0141baa007c51424a21f34):
  user-requested but preview-only (no download, no licence in the metadata).
  Nothing from them is installed or distributed; waiting for licensed files.
- **CRT TV — kitnxi**, [Sketchfab](https://sketchfab.com/3d-models/crt-tv-f5d3de5d04ca469aa192b9c4268dc81a):
  preview-only, Standard/NoAI listing, no downloadable model available. No model
  or derivative is installed or distributed. It is not presented as CC licensed.

## Other notices

- The local Scene studio authoring tool uses [Three.js r170](https://github.com/mrdoob/three.js/tree/r170), MIT. The official package's licence is cached with the browser modules in `build/tabletop/editor-vendor/LICENSE`; see `tools/tabletop/editor/README.md`.
- The original procedural consoles/media, new slot liners, mechanisms and
  processing code retain their MIT notices. See the runtime credits for scope.
- Dave Parker's source includes a BOSL dependency notice: [BSD 2-Clause](third_party/models/dave-gba/BOSL-LICENSE.txt).
  Downloaded source code is not executed as part of the model import.
- Raster Forge's supplied reference assets retain [CC0](third_party/raster-forge/LICENSE-CC0.txt).
- Other dependencies, fonts and upstream themes retain the licences supplied
  beside them. Game artwork from the user's library is not project-owned art.


TV stand by Qu3st10n
https://sketchfab.com/3d-models/tv-stand-2bad9d5f36b840c5a15e612cf9b7d78c
CC Attribution-NonCommercial-ShareAlike
http://creativecommons.org/licenses/by-nc-sa/4.0/
Author must be credited. No commercial use. Modified versions must have the same license.

Official 4k GLB and original archive preserved in research/tv-stand-qu3st10n/.
Runtime derivative: original geometry and UVs, source albedo, simple lighting; X right / Y up / Z forward, 1500 mm initial width, top surface at y=0. Editable table scales multiply these dimensions. No decimation. Full source PBR maps stay in the GLB/archive.
The 196-triangle source collision proxy is retained with its original zero-alpha visibility (hidden). The 888-triangle visible cabinet stays intact.
The model and its derivatives remain CC BY-NC-SA 4.0; this does not relicense the application.


Wooden table (low poly) by AndreyUEDev
https://sketchfab.com/3d-models/wooden-table-low-poly-ab96499ddb3b4bd7bc739e4f99dad409
CC Attribution
http://creativecommons.org/licenses/by/4.0/
Author must be credited. Commercial use is allowed.

Official 4k GLB and original archive preserved in research/table-andrey/.
Runtime derivative: original geometry and UVs, source albedo, simple lighting; X right / Y up / Z forward, 1500 mm initial width, top surface at y=0. Editable table scales multiply these dimensions. No decimation. Full source PBR maps stay in the GLB/archive.

Selected cartridge sources — 19 October 2026

NDS cartridge — satchii_
https://sketchfab.com/3d-models/nitendo-ds-cartridge-super-mario-64-2a768cba31054846817bcf2465611e21
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
Whole source scene and full PBR maps preserved; runtime uses opaque albedo and simple lighting.

GBA cartridge — thegraphicsgeek
https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
Whole source scene and full PBR maps preserved; runtime uses opaque albedo and simple lighting.

NES cartridge — dark_igorek
https://sketchfab.com/3d-models/nes-cartridge-battletoads-8aeab01fce084c3abaf3de792dda47a1
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
Whole source scene and full PBR maps preserved; runtime uses opaque albedo and simple lighting.

GB cartridge — Bob
https://sketchfab.com/3d-models/gameboy-cartridge-lowpoly-8b9728eab16c4056ac2636ae7f0f038f
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
Whole source scene and full PBR maps preserved; runtime uses opaque albedo and simple lighting.

GBC cartridge — Wikiti
https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
GBC hidden lower shell and connector are original additions; partial source label well extended through its filled lower strip; dimensions are presentation estimates

MD cartridge — Nerd_Sp
https://sketchfab.com/3d-models/couple-of-mega-drive-genesis-cartriges-c17dd351aa2743048430bf9a2b8af1dc
CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
Registered full source geometry/UVs/normals; no decimation. Fixed game artwork blanked; independent per-game label.
Whole source scene and full PBR maps preserved; runtime uses opaque albedo and simple lighting.



Public asset derivatives (23 October 2026): The public exporter removes the Game Boy character sticker and the Retro TV decorative decals while retaining the creators, source geometry and CC BY-NC 4.0 conditions. Historical/private originals are preserved. See [public asset derivatives](docs/PUBLIC_ASSET_REMEDIATION.md) and `release/asset-derivatives.json` for exact scope and hashes.

TV brand marks (24 October 2026): the Panasonic and Sony marks on the Panasonic CRT, Sony PVM-1341 and Retro TV are replaced, in the working models and the public copy alike, by the RETROvision print from the Old TV texture by pibanezl (CC BY 4.0). `tools/tabletop/tv_branding.py` applies it to the prepared TVs; the public source GLBs and `stage/tv` renders are matching derivatives. The models keep their own licences and no endorsement is implied. See [public asset derivatives](docs/PUBLIC_ASSET_REMEDIATION.md).
