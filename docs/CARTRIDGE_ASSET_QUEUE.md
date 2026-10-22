# Cartridge asset implementation queue

Updated 19 October 2026. Only user-selected assets belong in this queue. Research
candidates are not automatic replacements for the user's chosen current models.

## Implementation checkpoint — 19 October

All six selected sources are prepared, active locally, and **installed/hash-verified
on the device** (19 Oct ~04:00). Host/device rendering tests and measured device
timings are recorded in [the validation report](CARTRIDGE_VALIDATION_20261019.md).
Physical clearance, authored framing and full performance acceptance still have the explicit
limitations recorded there. The selection-time notes below are historical.

| System | Native shell triangles | Current preparation |
|---|---:|---|
| DS | 5,004 | One `Cartouche_Ds.003` copy; full source detail, live label, original sticker blanked. |
| GBA | 5,802 | Full thegraphicsgeek source; no earlier reduction or historical thickness stretch. |
| NES | 1,266 | Complete shell/contacts/clips; all 14 source sticker triangles retain the top wrap. |
| GB | 510 | Complete Bob source, live label and original texture details. |
| GBC | 1,887 | Wikiti exposed section plus explicitly original concealed lower shell/contacts; partial label recess completed. |
| Mega Drive | 26,224 | Freestanding `Object_3`, `Object_14`, `Object_42`, `Object_45`; all 148 wrapped sticker triangles. Cases and seated example excluded. |

Creator archives, highest-resolution GLBs and fresh metadata are preserved in
`research/selected-cartridges-20261019/`. Source GLB hashes, registrations,
modification notices and named packages are recorded under
`third_party/models/cartridge-SYSTEM-UID/` and
`theme/art-book-slot/_slot/cartridges/models/SYSTEM/`. The previous runtime
cartridges remain hash-verified `previous-*` alternatives; none were discarded.
Select a retained alternative with
`python -m tools.consolebuild.selected_cartridges SYSTEM --select PACKAGE`.
The tool refuses N64 and never writes scene-layout JSON.

Host evidence: 36 native GLES inspection renders (six views per model), all
exit 0, twelve cards and source-surface per-game labels. Targeted tests:
33 run, one skipped, pass. Native runtime atlases are 1024 square except MD
2048; full-resolution originals and PBR maps are retained. The native renderer
still uses opaque albedo/source normals, without source normal/roughness/metallic
or transmission maps. Source material appearance is consequently approximate.

Further validation: 180 host and 180 real device captures cover both aspects and
all six sources, with 90 additional private slot-facing host captures. All 24
selected/previous device comparisons passed (GL error 0, twelve labels, 4× MSAA).
GBA's 3:2 p95 slightly exceeds the plan's 33.3 ms scene target; full frontend
timing remains open. Raw triangle feed
checks intersect both old/new media; the DS slot mouth is a solid box. No geometry
was simplified or moved outside the case to hide that limitation. Authored camera
crops/missed close-ups are recorded without editing user saves.

Device installation `cartridges-20261019-035854` verified all 49 manifest files,
retained the existing frontend and PSX/Panasonic preview, and preserved all user
data/layouts. The only removal was an obsolete GBA paint sidecar, first proved in
the fresh recovery snapshot. Host/device originals and previous alternatives are
retained; the portable user-setup backup remains intact. See the handoff for
payload/recovery paths and the exact next fit action. N64 unchanged; no publishing.

## Accepted source choices

The user's follow-up selected these six sources. They are **queued choices, not
completed integrations**. DS retains its existing first position; the rows do not
authorize replacing any unlisted media or console housing.

| System | Accepted source | Scope / status |
|---|---|---|
| DS | [satchii_ - Nitendo DS Cartridge Super Mario 64](https://sketchfab.com/3d-models/nitendo-ds-cartridge-super-mario-64-2a768cba31054846817bcf2465611e21) | Existing first queued item; original acquisition/inspection next. |
| GBA | [thegraphicsgeek - Pokemon Cartridge (Gameboy)](https://sketchfab.com/3d-models/pokemon-cartridge-gameboy-7d79300f91a441d0ba520fdbd268aa5f) | User's exact GBA choice, superseding the Vxcl recommendation for this queued change. Retained full source GLB verified. |
| NES | [dark_igorek - NES Cartridge / Battletoads](https://sketchfab.com/3d-models/nes-cartridge-battletoads-8aeab01fce084c3abaf3de792dda47a1) | User answered yes to this proposed source. |
| GB | [Bob / MeBob - Gameboy Cartridge lowpoly](https://sketchfab.com/3d-models/gameboy-cartridge-lowpoly-8b9728eab16c4056ac2636ae7f0f038f) | User answered yes to this proposed source. |
| GBC | [Wikiti - Game Boy Color](https://sketchfab.com/3d-models/game-boy-color-03c6fe28d45244d2acd55486e3cfee19) | User's exact source, replacing the Ingoldt research suggestion. Prior original inspection found an incomplete seated cartridge; completeness work is required. |
| Mega Drive | [Nerd_Sp - Couple of Mega Drive / Genesis Cartriges](https://sketchfab.com/3d-models/couple-of-mega-drive-genesis-cartriges-c17dd351aa2743048430bf9a2b8af1dc) | **Use one of the three freestanding cartridges. Do not use the cartridge seated inside a game case.** |

All six source listings are CC BY 4.0 according to their checked creator metadata.
Retain creator/license/change notices in resulting assets. Other shortlist entries
remain unselected. In particular, no SNES, PSP or PSX replacement is queued here.

## Protected selection: current N64 cartridge

Latest authorization (19 October): proceed with the six-source implementation,
keep the current N64 until a fitting replacement is found, and **hold GitHub
publication until then**. Do not publish/push the theme during this work.

The user explicitly confirmed on 19 October 2026: **"the current N64 cartridge is
already perfect btw. Dont change it"**. Preserve its exact runtime geometry,
materials, labels, registration, source archives and settings. It is not queued
for replacement, simplification, retexturing or re-registration. Its recorded
CC BY-NC-SA 4.0 license is a publication/packaging consideration only; it is not
authorization to change the model. Any other N64 research leads are unselected.

## 1. Nintendo DS cartridge - satchii_

- **User selected; queued for implementation.** User request: "I really like the
  DS model you linked, queue it up for implementation in my theme."
- Source: [Nitendo DS Cartridge Super Mario 64](https://sketchfab.com/3d-models/nitendo-ds-cartridge-super-mario-64-2a768cba31054846817bcf2465611e21)
  by **satchii_**, model ID `2a768cba31054846817bcf2465611e21`.
- License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), confirmed in
  Sketchfab's public model API on 19 October 2026. API says downloadable, 20,016
  triangles, five textures and one material; creator describes 4K textures.
- Status: **selected and queued only**. Original source archive not downloaded
  in this increment; no conversion, runtime integration, host visual validation,
  device test, or installation has been performed.

### DS implementation sequence

1. Obtain the creator's original through Sketchfab's normal download flow. Record
   source metadata/license and SHA-256 of every original/archive. Preserve full
   original geometry, textures and editable sources. The extracted Socket APK
   derivative is evidence, not the source for redistribution.
2. Inspect the complete original. Measure card envelope, label surface/UVs and
   back/contacts; identify orientation and any separate parts. Public whole-model
   statistics are not a substitute for original geometry inspection.
3. Add a named source alternative with explicit registration to the current DS
   console and slot. Preserve the current card, all originals and registrations.
   Keep the existing label-down feed and launch/eject ownership. Replace the
   fixed Super Mario label with the user's existing per-game label pipeline;
   do not package that game artwork as generic theme art.
4. Preserve source normals, UVs and surface maps; record the native renderer's
   current material limits and any visual difference. No unrequested decimation,
   automatic camera framing or edits to authored scene-layout JSON/browser drafts.
5. Verify shared depth, label alignment, all card faces, insertion/seating/ejection,
   cartridge inspection and twelve-card performance at 3:2 and 4:3. Preview against
   the current model and record actual results. Add creator/license/change notices
   to the source ledger and shipped model credits when integration actually occurs.
6. If/when deployed, use the existing snapshot/restore/audit process, a narrow
   owned-file manifest and recorded frontend/asset hashes. Preserve saves/settings.
   Update TABLETOP_HANDOFF.md with distinct host-tested/device-tested/installed states.

**Next action:** acquire and inspect satchii_'s original DS source. No further
selection approval is needed for this queued source. Authenticated download access,
if unavailable, remains an acquisition limitation, not a reason to use Socket's copy.

## 2. GBA cartridge - thegraphicsgeek

The user explicitly selected model `7d79300f91a441d0ba520fdbd268aa5f`. Despite the
listing's generic "Gameboy" title, its description identifies a Pokemon Fire Red
cartridge made as a companion to the creator's GBA SP. This is a **cartridge**
choice; it does not change the user's chosen GBA SP console or its setting.

The retained `research/gba/pokemon_cartridge_gameboy.glb` is available locally:
SHA-256 `dad8725dd884d7254741b3a662358617d6bfc00a7b870365b2e3ebac51e2ed8f`,
2,358,420 bytes, 5,802 stored triangles, one mesh and three embedded GLB images.
It matches `third_party/models/thegraphicsgeek-ags/media-source.json`.
Use that complete source for fresh preparation and inspect its UV/material/label
surfaces. Do not treat the earlier texture-stripped/reduced derivative or its
historical 9.4-mm envelope as the new accepted result. Preserve the current Vxcl
card and its sources as an alternative; no current model is removed by this queue.

## 3. NES cartridge - dark_igorek

Selected model `8aeab01fce084c3abaf3de792dda47a1`, previously recommended at 1,270
listing triangles with PBR maps. Obtain/hash/preserve the original; register a
complete card and independent live label to the current front-loader mechanism.
Keep the current card as an alternative. New original not acquired in this increment.

## 4. GB cartridge - Bob / MeBob

Selected model `8b9728eab16c4056ac2636ae7f0f038f`, previously recommended at 510
listing triangles with a 2K material set. Preserve all original maps and geometry;
inspect back/contacts, material response and label surface before native conversion.
This choice does not change the user's GB console. Original not acquired in this increment.

## 5. GBC cartridge - Wikiti

Selected model `03c6fe28d45244d2acd55486e3cfee19`; **do not substitute Ingoldt**.
Public metadata reconfirmed CC BY 4.0 and downloadable on 19 October. The complete
listing is 15,350 triangles with 21 textures, including the console; this is not
the cartridge's count. Prior inspection and the prepared-source ledger in
`docs/MODEL_GBC.md` / `third_party/models/wikiti-cgb/source.json` explicitly identify
the included cartridge as only its **exposed seated half**, removed during the
earlier console preparation. That source ledger records original DAE SHA-256
`8bf473be6d1627c78f104eddba4396969464a81ae7946b8156ca08a250206184`.
Locate/hash-verify that exact retained Wikiti original, or obtain the selected
creator's original normally. Do not infer identity from a generic archive name:
`research/model-options-20261016/gbc-original.zip` is associated with **BPoole's
different GBC source**, not this selection, and is not approved as a substitute.

Reinspect the complete original for concealed parts before creating a loose cart.
If those parts are absent, preserve the authored visible portion and explicitly
document/model the missing concealed shell, back and contacts; do not stretch an
incomplete prop into a full card or claim new geometry is the artist's original.
Preserve the current complete card as fallback during that work. This selection
does not replace the user's selected GBC console housing.

The earlier sourcing report's Ingoldt recommendation missed an existing inspection:
its cartridge has a GB-compatible notch and was rejected for the dedicated CGB
shape. The report is corrected; Ingoldt is neither selected nor queued.

## 6. Mega Drive cartridge - Nerd_Sp, freestanding example

Selected model `c17dd351aa2743048430bf9a2b8af1dc`. The user clarified that **three
cartridges stand separately in the scene** and authorized choosing one of them.
Inspect those three complete examples and choose a suitable one for the loose
cartridge; record its exact node/mesh names and reason. **Exclude the cases and
the cartridge seated inside a case from the runtime derivative.** Preserve the
entire original scene/archive unchanged as source evidence.

The listing's 177,618 triangles, 46 materials and 84 texture entries describe the
whole scene, not one chosen standing cartridge. Measure that cartridge's actual
cost, shell/label/board components and UVs after acquiring the original. Preserve
its detail; no automatic decimation. Register it to the existing MD insertion and
per-game label pipeline without altering the authored cameras. JP/EA variants
stay unchanged unless the chosen original actually supports their forms.

## Shared boundaries

All six items are source choices awaiting their respective implementation/QA.
Preserve full source quality, current alternatives, authored camera/layout JSON,
browser drafts and source archives. Apply the DS sequence's source preservation,
label separation, native shared-depth/animation checks, twelve-card performance
review, attribution and device snapshot/audit requirements to the other five too.
No runtime asset, frontend binary, user setting or device state changed in this
selection increment. First implementation action remains DS original acquisition;
the verified GBA GLB can be inspected without downloading a replacement copy.
