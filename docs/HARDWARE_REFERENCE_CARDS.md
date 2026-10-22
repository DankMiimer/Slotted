# First precision exemplars

2026-10-13. Overall dimensions anchor these models; they do not certify contours,
printed marks, concealed mechanisms or the final rendered appearance. Ratios below
compare the current authoring parameters, excluding controls and port projections.
Keep presentation scale uniform when refining them.

## DMG-01 Game Boy and Game Pak

| Item | Source-supported target | Current authoring | Finding |
|---|---|---|---|
| Housing width/height/depth | 90 × 148 × 32 mm | 168 × 272 × 60 units | At 1.8667 units/mm, height should be 276.267; current height is 1.54% short. Depth is 0.45% above the dimensional anchor. |
| LCD pixel shape | 160 × 144 | 89 × 80.1 units | Pixel-aspect ratio is correct; absolute opening needs a matched front reference. |
| LCD physical size | Rounded manufacturer figures: 47 × 43 mm | 47.68 × 42.91 mm at housing-width scale | Close to rounded values; do not infer submillimeter precision or change the pixel ratio to match rounded dimensions. |
| Lower-right housing corner | Asymmetric, much broader than other corners | Radius 33 versus 10–12 units | Identity is present; radius/transition and bezel corner geometry remain photograph estimates. |
| Front printing | Revision-specific Nintendo/Game Boy lettering and bezel rules | Open Sans, condensed to a target width | High-priority visual mismatch. Generic type cannot meet the intended printing accuracy. |
| Speaker | Six slanted parallel slots | Alternating vertical positions | Validate slot endpoints and shared angle against an aligned original front photo. |
| Rear loading bay | Cartridge rails, connector, retaining lip, correct exposed height | Procedural recess and slot plane | Measure loaded/ejected clearance together with the Game Pak model. |

Dimension and LCD anchors come from [Nintendo's technical data](https://www.nintendo.com/en-gb/Support/Legacy-system/Technical-data-619585.html)
and [Nintendo's Game Boy history page](https://www.nintendo.com/en-gb/Hardware/Nintendo-History/Game-Boy/Game-Boy-627031.html).
Use the original grey DMG-01, not Pocket or Color. The current cartridge shelf
profile remains a presentation asset; a physical Game Pak width/height/depth card
still needs a measured original reference.

Next exemplar work: fix the body/landmark coordinate system, establish front/rear/
side reference registration, replace generic front printing with accurate original
paths, refine speaker and seam geometry, then review native front/rear/loading poses.
Do not merely stretch the complete assembled model: that would distort the LCD,
D-pad, button circles and printed glyphs.

## PSP-3000 / European PSP-3004 and UMD

| Item | Source-supported target | Current authoring | Finding |
|---|---|---|---|
| Housing width and visible height | 169.4 × 71.4 mm | 480 × 202 units | Height/width ratio differs by only −0.15%; overall front ratio is already close. |
| Body thickness | 18.6 mm excluding largest projections | Depth parameter 54 units across shell | At 2.8335 units/mm, target is 52.704; current parameter is 2.46% thicker. The mesh's true rear/front extents need separate measurement. |
| Display | 4.3-inch diagonal, nominal 16:9, 480 × 272 pixels | 274 × 154 units | Implied diagonal is 4.366 inches at housing-width scale; about +1.5%. Match the actual active opening and lens separately. |
| Front silhouette | Curved shoulders, subtly flattened top/bottom, rounded ends | Handwritten polygon contour | Better dimensions alone will not fix off-brand outlines. Trace landmark ratios from a verified original front view. |
| Controls | Independent direction buttons, textured nub, four glyphs, PS/system buttons | Procedural controls and generic small legends | Validate position, size, spacing and exact PS mark against the 3000 revision. |
| Rear drive | Slim rear ring, proper cover contour, lower hinge and latch | Rigid separate door range and UMD chamber | Review door seam and ring proportions independently of animated clearance. |
| UMD printed window | Continuous printed center; surrounding case retained | Shared art mask/projection, no open bore | Live window mask works on device. Physical case geometry remains a reference-review item. |

Manufacturer anchors: [Sony's original PSP-3000 release and specifications](https://sonyinteractive.com/en/press-releases/new-psp-playstationportable-comes-with-advanced-high-contrast-lcd-screen-and--built-in-microphone/)
and [PSP-3004 specification booklet](https://www.playstation.com/content/dam/global_pdc/en/corporate/support/manuals/psp-docs/psp-3004/PSP-3004_SS%24en.pdf).
The press release's old individual image links returned 404 during this review;
dimensions were available, but those images are not claimed as verified references.
Use a confirmed PSP-3000/3004 photo set before accepting detailed contour changes.

Next exemplar work: measure shell extrema and screen/controls from matched views,
refine contour and marks, and keep the existing rigid hinge relationship. Use
separate plastic/ink/glass appearance with restrained shading; preserve geometry
before adding highlights or more animation.

## Review record required before acceptance

Each exemplar needs a source-linked front/rear/side card, an unlit silhouette,
matched landmark overlay, native pose sheet, triangle/frame measurements and actual
loading-clearance check. Unknown values remain marked as estimates. None of the
current models has been promoted to a physically precise replacement in this slice.
