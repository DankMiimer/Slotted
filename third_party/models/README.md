# Authored console recreations

The user selected authored recreations instead of scans on 14 October 2026.
These geometry assets have separate CC BY licences; they are **not MIT**.
The project's processing code, original UMD and newly drawn identity paths
remain MIT. No creator endorsement is implied.

| Directory | Work / creator | Source | Geometry licence |
|---|---|---|---|
| `letsdo3d-dmg` | GameBoy DMG-01 / Let's Do 3D (@LetsDo3D) | https://sketchfab.com/3d-models/gameboy-dmg-01-29849a15fe0a40a6a18e01c9d544a0ed | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `jsjetstream-psp` | Playstation Potable(PSP 3001) / JSJetStream14 | https://blendswap.com/blend/14767 | [CC BY 3.0 Unported](https://creativecommons.org/licenses/by/3.0/) |
| `wikiti-cgb` | Game Boy Color / Wikiti | https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `thegraphicsgeek-ags` | Gameboy Advance SP and companion GBA cartridge / thegraphicsgeek | https://sketchfab.com/3d-models/gameboy-advance-sp-18c9688eaa8f4903a940c105242df15f and https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `dave-gba` | Gameboy Advance Cartridge (GBA cart) / Dave Parker | https://www.printables.com/model/190861-gameboy-advance-cartridge-gba-cart | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `quick-loop-snes` | Super nintendo (PAL/SFC shell) / quick_loop (@so_O) | https://sketchfab.com/3d-models/super-nintendo-d42c35b117974ade8842f0964f5fd59e | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `ibbqcats-snes` | Super Nintendo Console (SNS-001) / Steven H. Tran (@ibbqcats) | https://sketchfab.com/3d-models/super-nintendo-console-41c9dd1f5a53493cbe2e00a190150e93 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `josephrohm-n64` | Nintendo 64 (NUS-001) / Joseph Rohm | https://sketchfab.com/3d-models/nintendo-64-0bec1e1ed1bf4a96af858008b72437a3 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `darkigorek-ps1` | Sony PVM-1341 / PlayStation (console only) / dark_igorek | https://sketchfab.com/3d-models/5f80311f1a4646ef9673f20ee6dc6245 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

`source.json` records source-file SHA-256, dimensional normalization and changes.
The GLBs contain only geometry, vertex colours and small provenance/motion extras.
Images, UVs, packed screenshots, decal planes, cameras, lights and source scripts
are excluded. Original downloaded archives stay in ignored `research/`.
No scanned geometry is included.

Dave's GBA shell is assembled from its two binary STLs, preserving guides,
keyed mode slots, screw opening and interlocks. Height 34.4 becomes 34.5 mm to
preserve the existing label contract; width/depth stay 60/7.7. Original photo-
referenced grip groove, recessed lettering and rear identifier details replace
replacement-print approximations. New board, contacts and blank paper are MIT.
`import_gba_cart.py` reads data only. The source BOSL BSD notice is retained.
The earlier thegraphicsgeek cartridge is historical and no longer imported.

DMG changes: remove backdrop/decals/auto-smoothing modifier; normalize the complete
console to 90x148x32 mm and Game Pak to 57x65.5x7.8 mm; remove coplanar tessellation;
rebuild sharp boundaries and weighted panel normals after removing source
auto-smoothing nodes;
separate the D-pad from side fittings; widen the concealed cartridge cavity by
1 mm and set its rear inner surface to z=-13.45 mm; raise the visible rear lip
by 4.1981 mm to y=45.5 mm. Console outlines are protected during runtime export.

PSP changes: one subdivision level; normalize the housing frame to
169.4x71.4x18.6 mm; reduce minor fittings individually; correct the screen and
matching opening to 95x53.833333 mm at (0,3.2); make the rear ring circular;
remove source Sony lettering/shoulder labels; tag the real rear cover and ring
with the existing animation hinge. Our separate vectors replace identifying
wordmarks. Original holder rails and a shallow drive base are added at export.

Downstream derivatives include `theme/art-book-slot/_slot/consoles/{gb,psp}`
model GLBs/native meshes/body images and their generated idle bands. DMG media
GLBs/native mesh also derive from Let's Do 3D's work. Retain the shipped
`MODEL_CREDITS.txt` alongside these assets when redistributing them.

The PSP source used transparent key covers above its symbols. Our opaque
native version retains those covers and projects the flat glyphs onto their
outer surfaces. System-key printing is newly drawn with our existing paths.

Normal builds import these prepared physical GLBs without Internet access or
an account. To reproduce preparation from the ignored original scenes, use
Blender 4.5 with `--disable-autoexec --python tools/consolebuild/import_authored.py
-- gb|psp SOURCE.blend`. The importer opens scenes with scripts disabled.

CGB/AGS preparation uses `import_handhelds.py -- gbc|gba|gba-media SOURCE`.
Explicit source axes and component mappings are recorded there and in source.json.
The CGB source's partial cartridge is excluded; the complete dedicated cartridge
is original MIT geometry in handhelds.py. Master exports precede per-part runtime
reduction. The AGS derivative restores protected receiving planes after reduction.

PAL/US SNES preparation uses `import_snes.py -- snes|snes-us SOURCE` with Blender
4.5, `-t 1 --disable-autoexec --python-exit-code 1`. Sources are the approved DAE
and STL downloads under ignored `research/snes/`. Normalize physical envelopes,
remove source images/UVs/decal planes and replace the STL's four text regions
with blank panel patches. Open skins are clipped at the actual cartridge-mouth
position; original dark liners and connector floors complete the concealed bay.
Retain the source-specific semantic palette and enclosure/control separation.
The prepared GLBs keep full detail; runtime fitting budgets are separate.
The console GLBs, native meshes, body sprites, bands and appearance derivatives
retain CC BY 4.0. Their original cartridge meshes remain MIT.

N64 preparation uses `import_n64.py -- SOURCE.fbx` with Blender 4.5,
`-t 1 --disable-autoexec --python-exit-code 1`. The source is the approved
original-format FBX under ignored `research/n64/rohm/`. The yawed Maya group is
baked into its own frame; the controller, cable, cartridge, images, UVs and
normal maps are dropped. The envelope is corrected per axis to 260x73x190 mm.
Only the cartridge bay is widened (a smooth local x warp, `n64.BAY`) so the
116-mm Game Pak fits a 118.5-mm slot. The two source dust flaps are retained,
widened with lateral running gaps and registered for contact-driven motion.
The entry follows their closed surface; the visible slot and concealed hinge
relief are clipped through the final skin. Slot liners and the front badge are MIT.

PlayStation preparation uses `import_ps1.py -- SOURCE.blend` with Blender 4.5,
`-t 1 --disable-autoexec --python-exit-code 1`. Keep only the seven `ps1`
collection meshes, close the source's explicitly rotated lid and register its
hinge/spindle. The closed envelope is 270 x 60 x 188 mm. Retain early SCPH-1001
rear ports; register the optical pickup/cover behind the spindle for that
variant. Remove source images/material graphs, cameras, lights and accessories.
Prepared source remains full detail; native budgets and identifying words are
separate. Geometry, body/band images and appearance derivatives retain CC BY 4.0.

The selected Panasonic CRT TV (1990s), by DamianToons, is CC BY 4.0:
https://sketchfab.com/3d-models/panasonic-crt-tv-1990s-45f7728e4f534d9393ef1d681137b6d9
`damiantoons-panasonic/source.json` records hashes and adaptations. Rebuild with
`tools/consolebuild/import_tv.py` in Blender 4.5 with autoexec disabled, then
`python -m tools.themebuild.television`. The broadcast screen material and its
images are excluded; only housing materials and new blank glass are exported.
The frontend uses its transparent render with live content mapped onto glass.
