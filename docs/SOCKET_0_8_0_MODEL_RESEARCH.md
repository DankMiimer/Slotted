# Socket 0.8.0 cartridge model research

19 October 2026. Static analysis of the APK supplied by the user, plus public
creator/store metadata. This is research, not a model replacement or deployment.

## Findings

Socket bundles platform-specific cartridge geometry and material textures in its
APK. It instantiates a platform's scene for a game and replaces its label with
downloaded artwork. Several original model-source clues survive the Godot export.
The clearest commercial source is **Shrednector on CGTrader**; a separate DS model
strongly matches **satchii_ on Sketchfab**. There is no evidence that every mesh
comes from one supplier, or that Socket downloads a unique 3D mesh for each game.

### Sources traced

| Model | Original source / lead | Evidence and confidence |
|---|---|---|
| GBA | [Shrednector, Gameboy Advance SP Pikachu](https://www.cgtrader.com/3d-models/electronics/computer/gameboy-advance-sp-pikachu) | **High confidence, direct ID match.** APK import path is `models/gba/uploads_files_3322711_GBA_Cartridge.fbx.import`. The seller's Pikachu listing identifies itself as model **3322711**. Its cartridge texture family matches Socket's `GameboyAdvanceSP_Cartridge_Pokemon_*` names. This traces the source package; it is not a byte-for-byte comparison with a purchased original. |
| DS | [satchii_, Nitendo DS Cartridge Super Mario 64](https://sketchfab.com/3d-models/nitendo-ds-cartridge-super-mario-64-2a768cba31054846817bcf2465611e21) | **Strong match.** The APK retains the unusually spelled exact folder `models/nitendo_ds_cartridge_super_mario_64`, `nds_cartridge_v2.glb`, and the hierarchy `Sketchfab_model/Cartouche_Ds_002`. Sketchfab's public API returns the exact listing title and author. Source API reports CC BY 4.0 and downloadable. Geometry is not proved identical to the current public version. |
| GB | [Shrednector, Nintendo Gameboy Cartridges](https://www.cgtrader.com/3d-models/electronics/computer/nintendo-gameboy-cartridges) | **Probable source family.** Socket uses `GameboyTextures/GameboyCartridge_*` maps and a separated label. The seller offers the corresponding cartridge asset with separate game texture variants and an interior board. No unique store ID or original-file hash survives for this mesh, so this is a lead, not a proven exact match. |
| GBC | [Shrednector, Gameboy Color Cartridge](https://www.cgtrader.com/3d-models/electronics/other/gameboy-color-cartridge) | **Probable source family.** Socket includes `gbc_world.fbx`, `GameboyColorCartridgeTextures_world/GameboyColorCartridge_GameboyColorCartridge_*`, and Body/Circuit_Board/Screw nodes. Store format and material structure are consistent. Exact original identity still needs a source-file comparison. |
| Switch | [Shrednector, Nintendo Switch Game Cartridges](https://www.cgtrader.com/3d-models/electronics/computer/nintendo-switch-game-cartridges) | **Probable source family.** Socket retains four game albedos (Advance Wars, Kirby, Minecraft, Pikmin), shared PBR maps, and Case/CircuitBoard nodes. The seller's listing describes one cartridge with four interchangeable game textures. No unique store ID proves this mesh's exact original. |

Shrednector also sells a [standalone GBA cartridge pack](https://www.cgtrader.com/3d-models/electronics/other/nintendo-gameboy-advance-game-cartridges).
That is a useful source listing, but the APK's surviving numeric ID points to the
SP Pikachu package specifically. The reviewed CGTrader listings say Royalty Free
License; they are commercial originals, not established as CC assets.

The NES, N64, SNES PAL/US, Mega Drive/Genesis, 3DS, PSP UMD, Vita, Android-style
cartridge and generic disc meshes are also bundled. Their exact creators were
not established. SNES US and Vita retain `Sketchfab_model` node names, but those
names alone cannot identify an author. No model attribution/license manifest was
found in the reviewed application assets; this does not establish the developer's
private licensing arrangements.

## How the models and artwork meet

1. `scripts/models/platforms/*.gd` select local scenes such as
   `res://scenes/selectables/cart_gba.tscn`. SNES selects a regional PAL/US scene;
   GBC has an additional dual-mode scene selection. Bundled files alone do not
   mean every mesh is selected for every game.
2. `Cartridge.set_game()` applies casing and label materials. The cover is a
   separate mesh/surface, or a designated material surface, rather than a complete
   new model downloaded for every title.
3. The active manager creates `ScraperGamesDB`. Its base URL is
   `https://gamedb.depmots.com`, with a `/v1/match` request accepting ROM hashes,
   filename and platform. The current manager supplies ROM filename, platform slug
   and the available MD5. The response supplies a game, labels and metadata.
4. The scraper chooses a label by preferred region, then US/English/world fallback,
   downloads its image URL, and decodes WEBP/PNG/JPG. The manager caches JSON and
   `<rom>_support.png` under `user://scraped_data/<platform>/`.
5. The image becomes the label shader's `artwork_texture`. Per-game controls can
   replace the image, move/zoom it, change label effects, and override the casing.
   Metadata fields include `cart_material`, `cart_color`, and `label_foil`.

A `ScraperScreenScraper` implementation is present, but the normal manager uses
`ScraperGamesDB`. Its presence does **not** demonstrate that ScreenScraper is the
active provider or an automatic fallback in 0.8.0. The APK does not reveal the
private game database's ultimate upstream label suppliers. No request using an
embedded application API credential was made during this research.

## Why they look detailed

The evidence supports a combination of authored meshes, material maps and custom
shaders. Geometry alone does not explain the result:

| Reconstructed asset | Stored base triangles |
|---|---:|
| GB | 1,162 |
| GBA | 1,092 |
| GBC | 1,776 |
| N64 | 1,050 |
| Switch | 1,494 |
| DS | 5,030 |
| SNES PAL / US | 12,130 / 8,296 |
| PSP UMD | 144,640 |

These counts sum mesh primitives reconstructed from imported resources. They are
not profiler measurements, draw-call counts, or the original creators' quad counts.
They do not include a complete running scene or every possible generated LOD.

- GB/GBA/GBC/Switch commonly ship 1024-square color/normal maps and 512-square
  metallic/roughness maps. DS color is 2048-square. Normal maps retain small surface
  detail while the shell geometry remains modest.
- `CartFinishBank` builds opaque, translucent, clear, glitter and metallic finishes,
  with tint overrides and reusable maps.
- `game_sticker.gdshader` and `paper_sticker.gdshader` expose aging, wear, paper
  texture, scratch normals, holographic foil, diffraction, sheen, gloss and
  clearcoat controls. Individual label materials enable different combinations;
  this does not mean every effect runs on every label.
- The main scene and several label materials reference
  `studio_small_08_1k.hdr`, with environment reflections and a directional light.
  The project selects Godot's mobile renderer and enables 3D MSAA.

For Slot_ESDE, the useful technical finding is the preservation of material detail
and lighting alongside the mesh. This research makes no changes to our selected
models, registrations, label sources, shader implementation, or authored layouts.
Any later adoption should start from the creator's original and its license, with
an explicit comparison against the user's current model.

## Evidence and verification

- Input: `C:/Users/mads1/Downloads/socket_release_0.8.0.apk`, 153,793,423 bytes.
- SHA-256: `592421db2e84e12831bc0f67a2c630c86bd4fd04b22ec0ff70fadd69a4f6a62e`.
- Recovered configuration identifies Socket **0.8.0** and Godot **4.7.1**.
- Python `zipfile` inventory found 11,327 ZIP entries, including 11,213 asset entries.
- [Godot RE Tools](https://github.com/GDRETools/gdsdecomp) v2.7.4 was used for local,
  static recovery; the supplied app was not launched. Targeted recovery excluded
  third-party addons/examples/sprites/audio/fonts. It returned exit 0, reported
  124 scripts decompiled and zero scripts not decompiled, and produced 15 GLBs.
- Recovery emitted a missing addon icon warning, pack-version/decryption probe
  warnings, and an incomplete `gdmaim` plugin regeneration note. It is not a tested,
  runnable project recovery. The relevant model assets and scripts were readable.
- The tool reconstructs FBX/Blend imports as GLB. Its generated `asset.copyright`
  field is **not** original creator attribution and was not used as evidence.
- Local evidence is under ignored `build/research/socket-0.8.0-20261019/`:
  `apk-inventory.json`, `model-analysis.json`, public source metadata JSON,
  recovery logs, and the recovered resources/scripts. Recovered application files
  and analysis-only material remain local; none were added to runtime assets.

Useful local code anchors (inside that evidence directory):

- `recovered/scripts/models/platforms/gba.gd:7` - local scene and map selection.
- `recovered/scripts/autoload/manager.gd:734` - active scraper selection;
  `:742` - cache directory; `:771` - match inputs; `:797` - cached artwork.
- `recovered/scripts/models/scrapers/scraper_games_db.gd:60` - match route;
  `:85` - response game/labels; `:140` - regional image selection.
- `recovered/scripts/cartridge.gd:33` - game/material application;
  `:155` - artwork shader binding; `:175` - foil selection.
- `recovered/scenes/selectables/cart_nds.tscn:164` - retained Sketchfab hierarchy.
- `recovered/scenes/main.tscn:167` - panorama environment.

Device state was not queried or changed. Last recorded installed state remains n9
as documented in TABLETOP_HANDOFF.md, not newly verified by this research.
