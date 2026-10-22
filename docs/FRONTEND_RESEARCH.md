# Frontend, theme and hardware reference notebook

Last reviewed: 2026-10-13. Purpose: retain useful finds for Art Book Slot's precision and animation work. These are design and engineering references; the proposed applications are our conclusions, not claims that the other projects implement our requirements.

Each entry distinguishes the source's documented behavior from what we should study. Source/readme review is complete for the entries below; comparable navigation timings and frame-by-frame animation studies on their target hardware have not been performed. Keep this file tracked under `docs/`: the repository intentionally ignores `research/`, which contains local reference imagery and device material.

## Highest-value references

| Reference and primary source | Documented find | Application to Art Book Slot |
|---|---|---|
| [Socket, creator page](https://www.patreon.com/cw/SocketLauncher) and [official site](https://depmots.com/socket) | Creator describes a launcher for curated collections; public release-post titles show development has progressed beyond the older coming-soon coverage. The official site returned access errors in this review. | Keep the established physical-media/insert direction. Next visual study: compare shelf spacing, rest poses, mechanical timing and material restraint from creator demos. Current access limits mean specific latest features remain unverified. |
| [ZNeko Launcher](https://github.com/zneko-org/zneko-launcher) | Android frontend with Physical View, credited as following Socket's concept; it downloads credited freely licensed physical-media models. | Strong new lead for cartridge/disc/UMD references and model sourcing. Inspect each original model for dimensions, UVs, bore geometry, art separation and triangle cost before considering reuse. The repository is also an application/distribution reference, not a verified source-code implementation to port. |
| [ZNeko model attributions](https://github.com/zneko-org/zneko-launcher/blob/main/models/ATTRIBUTION.md) | Lists original creators and CC BY 4.0 links for CD, DS, GB, N64, NES and UMD models, among others. | A curated starting point for evaluating accurate media geometry. A listed licence does not establish dimensional accuracy or make embedded game art suitable for our package. |
| [Slot](https://github.com/BrandonKowalski/slot) | Focused GB/GBC/GBA frontend for Anbernic handhelds. Current repository lists GPL-3.0. Our prior MIT reference is pinned separately. | Continue studying the physical shelf and locally inspected spring behavior. Preserve the existing pinned-asset boundary when developing original code/assets. |
| [SLOT2](https://github.com/goosetopPM/slot2) | Cartridge/port shelves, several systems, per-game core choices, state previews and PC preview. Cores run in the frontend process. | Useful comparison for system profiles and iteration tools. Its integrated-emulator return path is architecturally different from Knulli's external process/hook/window restoration; its behavior cannot establish achievable return latency here. |

### Specific model leads

All linked through the [attribution list](https://github.com/zneko-org/zneko-launcher/blob/main/models/ATTRIBUTION.md); the original creator pages still need individual inspection before adoption.

| Media | Original creator listing | Question to investigate |
|---|---|---|
| CD | [GAMICO's compact disc](https://skfb.ly/pH6YE) | Is the outer diameter/bore ratio accurate, and are face/rim/bore UVs separate? |
| DS | [littlengvfx's DS cartridge](https://skfb.ly/prISD) | Does it match card thickness, asymmetric corner, notch and contact geometry? |
| GB | [Bob's low-poly Game Boy cartridge](https://skfb.ly/owAGR) | Are the label recess and distinctive side/top mouldings correct? |
| N64 | [c4m5ron's N64 cartridge](https://skfb.ly/pHtoz) | Is the shell useful independently of its game artwork? |
| NES | [ConnorMartin's NES cartridge](https://skfb.ly/6SXXq) | Are ribs, label strip, lower latch recess and thickness faithful? |
| UMD | [Cutlass Digital's PSP UMD](https://skfb.ly/oKtzO) | Are shell window, central hub and edge openings distinct surfaces? |

Do not download/ship a candidate on the strength of this list alone. Record its original source, exact attribution, asset contents and accuracy evaluation in the model manifest if it is selected. Our existing original models remain the current assets.

## Themes and frontends with useful transferable ideas

| Reference and source | Documented find | What to study next | Transfer limit |
|---|---|---|---|
| [WiiFlow Lite](https://github.com/Fledge68/WiiFlow_Lite) | Games/apps displayed with coverflow; multiple coverflow layouts are configurable. | Physical-object spacing, selected-object presentation, perspective and transitions. | Wii renderer and input stack; cover geometry differs from our media. No navigation performance claim inferred. |
| [Pegasus theme system](https://pegasus-frontend.org/docs/themes/overview/) and [gallery](https://pegasus-frontend.org/tools/themes/) | QML themes can define complete screens and interaction logic, rather than predefined views. | Component-based animation and reversible transitions; gallery supplies a broad comparison set. | QML is not Batocera XML. Use design/architecture lessons, not theme files. |
| [gameOS](https://github.com/PlayingKarrde/gameOS) | TV-oriented Pegasus launcher. Its changelog includes return-screen redesign, navigation-performance improvements and fixes for videos playing offscreen. | Coherent launch/return states and explicit video lifecycle. Its own history makes it a useful regression-study source. | TV-sized hierarchy needs adjustment for a 720×480 handheld. Repository lists GPL-3.0. |
| [Arcadeflow](https://github.com/zpaolo11x/Arcadeflow) | Selected-thumbnail videos, separate info preview, adaptive aspect ratios/cropping, small-screen and low-spec options, scrolling/sort cues. | One active preview, crop choices, letter/page navigation and delayed expensive work. | Attract Mode/AM+ scripting and render pipeline. Avoid carrying its many effects into a small handheld unchanged. |
| [Ckau-Book](https://github.com/CkauNui/ckau-book) and [theme XML](https://github.com/CkauNui/ckau-book/blob/master/theme.xml) | Batocera-family theme with animated system-view variants, per-system includes and optional artwork/video addons. XML restricts blur options by architecture/screen size. | Native storyboards, coordinated system-screen animation, feature budgets and clean addon packaging. | Current assets/features may target newer ES versions; repository lists CC BY-NC-SA 4.0. |
| [Atlas](https://github.com/mirko93s/atlas-es) | Built initially for Knulli handhelds; configurable animation/fonts/help icons and options to reduce video/background cost. | Small-screen legibility and practical performance settings. | A useful same-family comparison, not proof that all its claimed frontend compatibility applies to this binary. |
| [Next Pixel](https://github.com/SamYStudiO/es-theme-next-pixel/blob/master/README.md) | Per-system game-art presentation, regional logo/console options, multiple gamelist layouts, support for small 4:3 screens. | Region consistency, matching menu/system/game visuals and aspect-ratio discipline. | Recalbox implementation differs. Its optional full-screen artwork is a presentation reference; retain our black physical shelf default. |
| [Analogue OS Menu for ES-DE](https://github.com/anthonycaccese/analogue-os-menu-es-de) | Author's translation of Analogue's menu design, with list/carousel/grid variants and large fonts for small handheld screens. It documents theme-engine differences. | Strong reference for restrained product typography, selected-state hierarchy and consistent controls. | ES-DE implementation, with openly acknowledged approximation; examine the linked original Analogue references for the intended design. |
| [MinUI](https://github.com/shauninman/MinUI) | Focused launcher/libretro frontend with consistent emulator menus and resume behavior. The original repository is archived. | Predictable controller behavior and continuity when leaving/resuming games. | It deliberately omits themes/artwork; use interaction principles. It supplies no measured comparison for our Knulli return gap. |
| [Daijishō](https://github.com/TapiocaFox/Daijishou) | Platform/player separation, configurable hotkeys, detailed views, search and widgets. | Consistent navigation hierarchy and a clear distinction between browsing and inspecting a game. | Android application; repository serves assets/main-page documentation. Keep the normal physical shelf simpler than its widget screens. |
| [Art Book Next, Batocera edition](https://github.com/anthonycaccese/art-book-next-es) | Existing base theme centred on a coffee-table-book presentation. | Harmonise our system selection, menus, typography and status with its maintained entry points. | It remains a runtime dependency; custom native shelf/launch behavior is ours. |

## Technical findings worth retaining

### Native frontend source

The planning audit initially inspected `10834d004ec3de0808703b46220b6a8574d53218` from a cached newer recipe. Implementation corrected the target to **`4041b56a714265de81de8165b34fbd10f313a891`**, pinned by the installed Scarab release's [20260511 build recipe](https://github.com/knulli-cfw/knulli-linux/blob/20260511/package/emulationstation/knulli-emulationstation/knulli-emulationstation.mk). A byte-for-byte rebuild match is not established. The older links below document the initial audit; [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md) records installed-build evidence.

- [Scarab VideoVlcComponent](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-core/src/components/VideoVlcComponent.cpp) uses synchronous player stop/release and ignores source sample-aspect metadata when setting its video dimensions. Both matter for the current project; the newer asynchronous release is not installed behavior.
- [Scarab ThemeData](https://github.com/knulli-cfw/batocera-emulationstation/blob/4041b56a714265de81de8165b34fbd10f313a891/es-core/src/ThemeData.cpp) treats nested shader properties as strings. Resolve paths with `${currentPath}`. Device tests now confirm full-CD annular alpha and shared art projection, plus UMD-window mapping. Non-square source pixels need corrected preview copies on this frontend.

- [CarouselComponent](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/components/CarouselComponent.cpp): quintic carousel movement and nearby-item creation make both motion continuity and cold-item workload worth profiling. Inspect cursor changes and render preparation rather than assuming a longer slide fixes stutter.
- [FileData](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-app/src/FileData.cpp): external process completion precedes frontend window/input/resources/audio restoration. This supports investigating return orchestration beyond the theme XML.
- [VideoVlcComponent](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/components/VideoVlcComponent.cpp): `minSize` preserves source proportions through crop; the component parses custom shader parameters. This is the first route to test for an annular PS1 preview.
- [ThemeData](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/ThemeData.cpp) and [GLES2 renderer](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/renderers/Renderer_GLES20.cpp): nested custom shaders and GLES shader loading are source-backed features. Installed-build compatibility, alpha masking, coordinate conventions and cost remain to be demonstrated.
- [ES-DE theme documentation](https://gitlab.com/es-de/emulationstation-de/-/blob/master/THEMES.md): use it to discover ideas and references. Keep implementation anchored to the actual Batocera/Knulli engine rather than treating frontend names as equivalent.

### Better hardware references

- [Nintendo's Game Boy technical data](https://www.nintendo.com/en-gb/Support/Legacy-system/Technical-data-619585.html) gives original DMG dimensions, rounded LCD dimensions and pixel resolution. [Sony's original PSP-3000 announcement](https://sonyinteractive.com/en/press-releases/new-psp-playstationportable-comes-with-advanced-high-contrast-lcd-screen-and--built-in-microphone/) gives revision-specific dimensions, display and controls. Current authoring discrepancies and confidence are recorded in [HARDWARE_REFERENCE_CARDS.md](HARDWARE_REFERENCE_CARDS.md); these anchors do not establish every hidden detail.

- [Evan-Amos / Vanamo Online Game Museum](https://commons.wikimedia.org/wiki/User:Evan-Amos): the photographer's own archive, organised by hardware family, includes the systems we need. The author describes the photographs as public domain. Use the relevant original file pages to record exact revision, provenance and views. Photographic perspective still needs correction before dimensional comparison.
- [Nintendo DS Lite product information](https://www.nintendo.com/en-gb/Support/Legacy-system/Product-Information-242119.html): specifies closed dimensions of 133 × 73.9 × 21.5 mm. Search retrieved the manufacturer text although direct page access failed during this review. Use it as an overall dimensional anchor, not a measurement for every subpart.
- [Sony PSP-3004 specifications](https://www.playstation.com/content/dam/global_pdc/en/corporate/support/manuals/psp-docs/psp-3004/PSP-3004_SS%24en.pdf): dimensions and screen information give a model-specific anchor. The text specifies approximately 169.4 × 18.6 × 71.4 mm, excluding largest projections. Match regional/revision details explicitly; other similarly named PSP manuals can contain different thickness values.

For every hardware model, retain a compact reference card: revision/region, official dimensions, front/rear/side/open views, uncertain ratios, logo/legend sources, slot geometry, and camera-aligned comparison images. Measure large silhouette errors before minor details.

## Conclusions to carry into planning

1. Socket and ZNeko are the closest physical-media references. The ZNeko attribution list is the strongest new model-sourcing lead.
2. WiiFlow and Arcadeflow add useful spatial/navigation/video ideas. Their richer effects must pass our own handheld frame budget.
3. Analogue-style hierarchy plus Art Book Next's typography can support the requested finished-product feel without crowding the shelf.
4. A custom video shader is a more promising first experiment than pre-baking opaque black video masks or immediately replacing the frontend.
5. The real device's return and scrolling traces must determine the engineering plan. Other frontends' architecture and demonstrations cannot stand in for those measurements.

## Next research passes

- Watch creator-authored Socket/ZNeko/WiiFlow demos with a timing sheet: input cue, motion start, focus settle, preview onset, launch and first usable return.
- Inspect original candidate models individually and compare them against manufacturer/photo references. Record discrepancies; retain only candidates that improve accuracy.
- Compare one same-family Knulli theme with our own shelf under the same library/media settings, separating common frontend cost from our template cost.
- Test shader support on the installed binary before designing all masks. Record shader source/API, alpha behavior and timing in this notebook.
- Add new finds with primary source links, review date, observed behavior, transferable idea and outstanding questions. Keep unverified leads labelled.

## Plan-refinement findings, 2026-10-13

- User chose accurate hardware with restrained cel shading. This is recorded as the visual direction in [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md).
- The inspected Knulli [border shader](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/resources/shaders/border.glsl) carries local vertex position separately from texture UVs. It uses output dimensions/offset to evaluate shape boundaries. This is a concrete reference for keeping a media mask independent of video crop coordinates.
- The inspected [Shader.cpp](https://github.com/knulli-cfw/batocera-emulationstation/blob/10834d004ec3de0808703b46220b6a8574d53218/es-core/src/renderers/Shader.cpp) and GLES2 draw path provide shader loading and uniform plumbing. Installed-build compatibility, cropped-coordinate behavior and edge blending still need a device proof. Arbitrary second mask textures have not been established by this review; prefer analytic circle/rounded-shape prototypes first.
- Local `animation-layer.h` uses private double buffers but still gets its scene from SDL readback. `slot-launch.c` presents through SDL and drains events. Protecting display pixels therefore does not prove that eject can run concurrently with ES window/input restoration. The plan now makes that an explicit architecture gate.
- Local `umd.py`/`render.py` preserve a printed UMD center rather than the PS1's open bore. Video masks must follow each physical surface; a shared circle shader must not imply an identical hole for every disc type.
- Local `cartridge-console.h` blends orientation basis vectors in several alignment paths. Such blends need not retain a rigid orthonormal basis. Review rigid rotation before carrying a frozen preview through native loading.
- Existing shader/renderer source supplies a more actionable technical reference than general theme demonstrations. The research list remains a design input; actual device traces decide the implementation paths.
