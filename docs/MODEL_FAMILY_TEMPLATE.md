# <console revision / media> model slice

Copy this file for the next family. Follow [MODEL_WORKFLOW.md](MODEL_WORKFLOW.md)
and give external modellers [MODEL_INTEGRATION.md](MODEL_INTEGRATION.md).
Leave unknown values and unrun checks explicit.

Date / branch / receiving commit: <values>
Hardware revision / region / colour: <values>
Media revision and connector/label direction: <values>

## Sources and selection

| Candidate URL / creator | Authored or scan | Licence | Complete editable console / media / moving parts | Decision and reason |
|---|---|---|---|---|
| <candidate> | <value> | <exact notice> | <coverage> | <reason> |

Selected download filename / SHA-256: <values>
Ignored research directory: <path>
Committed source metadata / attribution paths: <paths>
Excluded source images, printing or unrelated objects: <list>

## Reference and correction card

Project axes: x right, y up, z towards front. Physical unit: mm.
Confidence: A published/standard, B calculated, C photo/recreation estimate,
D concealed/unverified fit. Cite the source and uncertainty per measurement.

| Landmark | Reference target | Source at one uniform scale | Corrected result | Confidence / uncertainty / citation |
|---|---|---|---|---|
| Console W / H / D, with definition of excluded projections | <values> | <values> | <values> | <evidence> |
| Silhouette / local corner radii | <values> | <values> | <values> | <evidence> |
| LCD W / H / centre / bezel | <values> | <values> | <values> | <evidence> |
| Controls: sizes / spacing / centres | <values> | <values> | <values> | <evidence> |
| Side, rear and bottom ports / landmarks | <values> | <values> | <values> | <evidence> |
| Media W / H / D / label recess | <values> | <values> | <values> | <evidence> |
| Slot mouth / lip / connector floor | <values> | <values> | <values> | <evidence> |
| Hinge / moving-part pivot | <values> | <values> | <values> | <evidence> |

Physical corrections applied, with percentages: <values and affected regions>
Uniform native presentation units per mm: <value>
Prepared GLB axes/metres and export conversion: <values>

## Loading and native rendering

Seated media centre / front and rear planes: <values>
Media approach, alignment, feed and withdrawal: <phases and directions>
Fixed versus moving parts; shared pivot: <names and values>
Sampled clearances and where measured: <values / method / limits>
Label crop / surface / clipping contract: <values>
Preserved insert/eject duration, fades and holds: <values>
Material/normal/printing adaptations: <changes>
Shared theme appearance: support both Cel shaded and Realistic (smooth lighting,
no outlines), plus the shared Console color choice and Original. Name enclosure
paint parts explicitly; preserve screens, controls, marks and media artwork.
Add these options when this family's accurate model is made, not to its older
placeholder. Use the completed six-model appearance workflow as the example.

## Build and evidence

Preparation adapter / prepared-source paths: <paths>
Rebuild commands and pinned tool versions: <commands>
Generated asset paths / native integration paths: <paths>

| Mesh | Master triangles | Runtime triangles / vertices | Budget result |
|---|---:|---:|---|
| Console | <count> | <counts> | <result> |
| Media | <count> | <counts> | <result> |

| Verification | Status | Evidence / exact limitation |
|---|---|---|
| Neutral front/rear/side/top, loaded rear and receiving-commit comparison | Not run | <paths> |
| Native 720x480 insert/eject, free approach, seating and closure | Not run | <paths> |
| Exported-triangle clearances / visible diagnostic positive controls | Not run | <report> |
| Repeated and reverse-order asset hashes | Not run | <report> |
| Unit tests / WSL ARM64 build | Not run | <results> |
| Authorized device preview / game boot and return / accepted input | Not run | <results> |
| Device save/config restore, intended hashes and unrelated-runtime audit | Not run | <snapshot / report> |

## Remaining discrepancies and handoff

1. <Measured discrepancy, size, confidence and next evidence needed.>

Focused commits / suggested integration order: <values>
Device state left behind, if tested: <values>
