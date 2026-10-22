# DS Lite lid and Realistic finish — 16 October 2026

> **Superseded 17 October 2026:** the procedural DS Lite described below was replaced by
> Cianon's textured model, see [MODEL_DS_LITE_CIANON.md](MODEL_DS_LITE_CIANON.md). This page is kept
> for the lid-motion, Slot-1 and clearance history; the numbers here no longer describe the installed mesh.

Built on `models/gbc-gba-exemplars`; installed on 16 October. The original
DS Lite geometry keeps its controls, ports, twelve speaker perforations and
rear Slot-1 path. Realistic and Cel both use the same native mesh and moving
upper assembly. The earlier flat appearance came partly from a renderer
eligibility restriction; all thirteen consoles now reach the existing
Realistic shader, as documented in MODEL_APPEARANCE.md. No new global shader
or guessed clear-coat constants are introduced here.

## References and registration

[Nintendo's product specification](https://www.nintendo.com/en-gb/Support/Legacy-system/Product-Information-242119.html)
states a closed envelope of 133 × 73.9 × 21.5 mm.
The [Japanese operations manual](https://www.nintendo.co.jp/ds/support/pdf/dsLitemanual.pdf)
also gives the two active LCDs as 61.4 × 46.1 mm. Those are manufacturer anchors.
The original lower housing's 404 native units register to 133 mm; the existing
card retains its separate 2.75-units/mm presentation register. Console and card
units are recorded separately rather than claiming a newly surveyed OEM assembly.

The existing fixed end barrels establish the hinge at native **(0, −34, −103)**.
The middle barrel, neck, complete upper shell, glass, speakers, bumpers, emblem
and microphone move together. The **145°** open presentation pose is retained;
no source has established it as the hardware's exact detent angle.
[iFixit's first-hand microphone repair guide](https://documents.cdn.ifixit.com/pdf/ifixit/guide_4794_en.pdf),
particularly steps 19–26, shows the microphone wiring and upper display assembly.
The hole/identifier now sit on the moving neck, rather than floating on the
control deck. PDF and inspected page renders are archived under ignored
`research/hardware-review/independent/ifixit-ds-microphone*`. No reference images
or image traces are shipped; geometry remains original MIT work.

The old static lid could not fold without entering the controls. Its skin is
thinned toward Nintendo's closed-height anchor, keeping the actual barrel axis
fixed. The inner plane clears the keys; a 9.55-native-unit radial bore in the
rear deck clears the 9.2-radius moving barrel. These small fit dimensions are
reconstruction estimates, not an OEM mould/hinge drawing. Active LCDs now match
61.4 × 46.1 mm at the housing register. The old Slot-1 floor extended 11 native
units outside the mouth; it is trimmed inside the receiving edge.

The exported folded height is **21.494 mm** at that register, within .04 mm of
the anchor. The complete procedural envelope including ports, switches and
other projections is approximately **134.4 × 76.9 mm** in plan, so this is not
claimed as complete 133 × 73.9-mm manufacturing accuracy. Individual port,
button and concealed-fit measurements remain estimates. Masters and physical-
unit GLBs are retained separately from the bounded native mesh.

## Motion and evidence

Idle shows the closed DS. Insertion opens the lid before the card reaches the
rear slot, then closes it after seating. Withdrawal opens the lid during its
first .60 seconds and closes it late in the reverse scene. The lid does not
operate Slot-1. Card orientation, rear approach and the original push-to-release
click pulse remain; the slot works independently of the lid, consistent with
[Nintendo's loading instructions](https://en-americas-support.nintendo.com/app/answers/detail/a_id/3906/~/how-to-insert-and-play-a-nintendo-ds-game-card).

Runtime console: **13,095 triangles / 12,025 vertices**, below 15,000 triangles
and uint16 bounds. The independent native-triangle sweep includes every fixed
and moving triangle: zero lid/body intersections at 101 opening positions,
with **1,812** intersections when the closed lid is deliberately lowered 5 mm.
Another 101 samples combine the actual aligned card path and closing lid: zero
card/lid or card/body intersections, including the seating click. The separate
101-position full feed check is clear, with a displaced-card control of 301
intersections. GBA also remains clear in the extended combined-path check.
These sampled geometry checks establish the exported animation fit, not OEM
mechanical tolerances or performance on the handheld.

Blender's reduction initially left 36 interpolated solid normals shorter than
unit length. Rebuilding the DS moulding normals after reduction and normalizing
their native serialization fixes the buffer regression. glTF normals are also
unit length; the shared Realistic shader is unchanged. All **138 tests pass in
WSL** and in Windows (five POSIX-only skips), including native shelf hand-off.
ARM64 builds warning-clean. **90 generated files** match forward/reordered/repeat;
**220/220 native PNGs** for the eleven other cartridge consoles match `c0a697b`
using identical inputs (`build/ds-lid/comparison/result.json`). Accepted console
geometry and all cartridge heroes/label boxes remain unchanged.

Native 720×480 Realistic/Cel insert/eject captures are in
`build/handheld-lids/nds-*`. All twelve cartridge hero PNGs, label JSON, shapes,
shells and backings remain unchanged in this DS slice. The existing baked faces
stay Realistic even if Cel is selected for the animated model.
The same capture directory contains Realistic insert/eject GIFs for GBA and DS;
these reproduce the native poses/composition with GIF timing rounded to 10 ms.

Reproduce the three builds, feed/lid checks, full WSL suite and warning-clean
ARM64 build with `sh tools/consolebuild/ds-lid-evidence.sh`, Blender 4.5 and
`-t 1`. Logs/hashes are under `build/ds-lid/`. Installed Realistic insert/eject
previews pass at **58.1/58.6 fps**. MODEL_HANDOFF.md records the fresh snapshots,
3,613-face library rebake (11 DS cards), audits and protected-pipeline preservation.
