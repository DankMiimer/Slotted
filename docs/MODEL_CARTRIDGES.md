# Selected cartridge sources — 16 October 2026

The user moved these cartridges ahead of the queued console replacements.
Sources are preserved, hash-listed under `research/model-options-20261016/`.
The Blender adapter never runs source scripts. Original archives, imported
scenes, source images and registered textured masters stay in ignored research/
build directories. Distributed editing GLBs contain geometry and attribution;
runtime albedo contains cleared labels and simple lighting, without PBR maps.

| Cartridge | Creator / licence | Native triangles | Registration |
|---|---|---:|---|
| PAL SNES | SomeKevin; UVs cpt.brotzeit, CC BY 4.0 | 33,839 | 130 × 78.074 × 20.069 mm; source proportions retained, US shell retained |
| SNES-inspired option | kutejnikov, CC BY 4.0 | 216 | 130 × 88.559 × 20 mm; depth fitted to existing bay, separate PAL/US native scales |
| GBA | Vxcl, CC BY 4.0 | 1,522 | 60 × 35.129 × 7.287 mm; uniform scale, two zero-area source triangles omitted |
| PICO-8 | sunnychow, CC BY 4.0 | 438 | 60 × 76.721 × 6 mm; depth fitted from 9.698 mm, source width/height retained |
| N64 | Chris Sweetwood, **CC BY-NC-SA 4.0** | 1,050 | 116 × 77.333 × 19.333 mm; one upright shell and sticker, other two posed copies excluded |

Exact measurements, source hashes, attribution, modifications and atlas tile
sizes are in `third_party/models/cartridge-*/source.json` and each runtime
`media-registration.json` (or `media-tzakol-registration.json`). No decimation.
GBA retains the source's two plastic parts, board, screw and sticker surface.
N64 retains the source silhouette; its flap contact uses this shell's thickness.
The models inherit source accuracy rather than claiming to be OEM CAD.

SomeKevin uses a 2048px reduction of its 4096px colour map. GBA packs its
2048px maps as 992px tiles plus the board/screw maps in a 2048px atlas, with
16px wrapped borders. Those borders preserve the artist's small out-of-range
UV samples without allowing a UV to escape the atlas (which triggers the
safe vertex-colour fallback). N64
keeps its 1024px plastic map; fixed label image is excluded. Tzakol reduces
2048px to 1024px. PICO-8 copies its original **128px** map into a 256px atlas
alongside tiny constant material swatches: no source image is enlarged.
Normal/roughness/metallic maps are retained in the originals, but are not used
by the current native shader; detail present only in those maps is not restored
by albedo. Generic moulded print/contacts remain where present in geometry or
the base-colour maps. Fixed game art/credits are cleared from all kept maps.

## Shared shelf and animation contract

`cartridges_blender.py` registers each source and identifies the physical sticker
triangles. `cartridges.py` writes SCTOON2 geometry, hash-bound SCTEX003 UV/albedo,
a hash-bound plastic mask and a second mesh for the game label. Game labels
follow the source surface (including the curved PAL SNES sticker), with a
0.035 mm offset. The renderer samples only the current game's measured shelf
label crop, unlit, and shares the console/shell depth buffer. Missing or invalid
label UVs use the existing projected-label fallback. Missing colour textures
retain vertex colours and per-game plastic tint.

The neutral and black-plastic hero passes separate tintable moulding from
fixed-colour details. The shelf baker combines that moulding with the game's
plastic and adds the fixed RGB layer. A captured sticker mask preserves the
source's rounded outline and the divider between PICO-8 artwork and credits.
Per-game caches include the regenerated shape revision.

PICO-8's original 160×205 PNG is read as data, never executed or changed.
Its `(16,24,144,196)` art/credits area fits the new sticker while the source
shell supplies the PICO-8 frame. Text `.p8` carts retain their entire 128×128
label and receive a separate title panel. No Song of Morus game data ships as
a generic texture. Library ROMs retain their original bytes.

**Slot SNES cartridge model** (`slot-snes-cartridge-model`) offers `regional`
(default: SomeKevin PAL or the existing US shell) and `tzakol`. The baker
prepares both `<stem>.png` and `<stem>.tzakol.png` with separate cache entries
and backings. A theme include variable selects the matching complete shelf,
label/video boundary and generic fallback. Native and standalone animation use
the same choice; unknown values select the regional default. US and PAL
console geometry remains regional. The selection is persistent in normal ES
theme settings.

## Reproduction / verification

Run in WSL from the checkout:

```sh
/home/mads1/slot-tooling/blender-4.5.0-linux-x64/blender \
  -b --factory-startup --disable-autoexec --python-exit-code 1 -t 1 \
  --python tools/consolebuild/cartridges_blender.py -- snes pico8 gba n64 tzakol
python3 -m tools.consolebuild.cartridges
python3 tools/consolebuild/media.py
sh tools/consolebuild/hero-shells.sh snes:snes pico8:pico8 gba:gba n64:n64
SLOT_SNES_CARTRIDGE=tzakol sh tools/consolebuild/hero-shells.sh snes-tzakol:snes
python3 tools/consolebuild/media.py
python3 -m tools.themebuild
```

`models.py` protects authored media from procedural replacement. Existing GB,
GBC, NES, US SNES, Mega Drive and DS media retain their previous builders.
Host tests cover full source counts, geometry/UV hashes, curved label surface,
physical envelopes, game-art isolation, actual native shelf handoff, explicit
style/default/unknown behavior on both SNES consoles, and independent style
bake caches without ROM modification. Device results and active build are
recorded in section 0 of NEXT_CHAT_PLAN.md after the device pass.

## Completed device pass, 17 October 2026

164 Linux tests pass, plus input/state replay and 91 real GLES texture
acceptance/fallback/finish cases (GBC, Dreamcast and all five new cartridge
profiles). Both finishes/eight paints across all 14 browse families regenerated.
The actual Theme Configuration setting is visible, changes the complete shelf
and native cartridge, and persists across a frontend restart. PAL and US Tzakol
insertion, ejection and a PAL-to-US highlighted-game swap are captured. Metadata
remains on the existing TV glass or handheld LCD. No games launched in this pass.

The handheld's 180-frame scene benchmarks have maxima of GBA 12.662ms, PAL SNES
10.175ms, existing US SNES 10.502ms, N64 14.912ms, PICO-8 9.792ms and Tzakol
PAL/US 9.017/9.623ms. This measures the native scene, not the entire frontend.
Logs are under `build/queued-cartridges/device/`; use `bench-gba-final.log`
instead of the pre-UV-fix GBA entry in bench.json. Final GBA prefetch 268.499ms,
first open 257.752ms, reopen 197.370ms. New cartridge albedos prefetch during browse.

The offline rebake produced 1,551 faces, including alternate SNES styles; all
198 GBA faces were rebaked again after adding the wrapped atlas borders. Dense
capture is 24–25fps with 6×4 timestamped grids under
`build/queued-cartridges/shots/`. Final GBA evidence is `gba-insert-final` and
`gba-eject-final`; earlier GBA captures show the rejected-UV fallback and are
kept as diagnostic history.

Fresh stopped-frontend snapshot `cartridges-20261016a`: 323 data / 1,506 runtime
files. Existing generated media (3,615 files) has its own untouched backup.
Final data restoration/audit: **323 files, zero changed, zero new**. Eight
sampled original ROM hashes are unchanged, all 132 intended deployed files
hash-match. Settings changes were preserved before restoration; intended baked
faces remain installed. Device frontend is running with no game running:
`…/queued-cartridges-20261016/emulationstation-queued-cartridges-a`, SHA-256
`e00e495f8e4652801fe20727ae92efa6899900a5ef606cc4b8f663296b3ac631`;
helper SHA-256 `fda939439a8b78c200c32337f500748302a446e34d5dafb412a54101426e13d9`.
Reboot returns to the official frontend. No OS overlay saved; nothing committed.

Preserve the accepted PSX/Dreamcast shared-depth discs and open lids, closing
only for the one-second A/Play prelaunch interval. This cartridge increment
does not change their state choreography.
