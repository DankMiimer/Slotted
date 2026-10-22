# Retro TV model research

Verified against the creators' Sketchfab listings and public model metadata on
2026-10-16. The user selected the Panasonic home TV.

| Candidate | Creator / listed complexity | Fit for this scene | Critical assessment |
|---|---|---|---|
| [Panasonic CRT TV (1990s)](https://sketchfab.com/3d-models/panasonic-crt-tv-1990s-45f7728e4f534d9393ef1d681137b6d9) | DamianToons; 15.9k triangles; CC Attribution | Selected: recognizable domestic 1990s cabinet, large glass, controls below the picture | Best match to a home console. Source television-program imagery must be removed. Near-frontal rendering preserves readable text. |
| [Sony PVM-14L2](https://sketchfab.com/3d-models/sony-pvm-14l2-crt-tv-ab19c2419c2647299ce96d027b3e7f5e) | Poring; 12.5k triangles; CC Attribution | Strong alternative for a professional-monitor aesthetic | Convincing CRT, but a production monitor rather than the requested domestic TV. Deep housing and controls can consume useful picture area at an angle. |
| [Lowpoly Old TV](https://sketchfab.com/3d-models/lowpoly-old-tv-1ab0b494e6e4424eb629ad1963356461) | matoteus; 601 triangles; CC Attribution; separate screen texture | Lightweight stylized alternative | Explicitly replaceable screen map is useful. Lower complexity is not an automatic performance win when the cabinet is pre-rendered; compare silhouette and glass area first. |

At 720×480, the limiting resource is readable screen area, rather than the TV
mesh's triangle count. The selected cabinet is rendered once to a transparent
893×867 image; the frontend draws its live content inside a registered glass
quad. It occupies the full lower 360px height at the right. Artwork keeps its
aspect ratio and text renders for the final glass size (about 324×247px).
There is no second video decoder or real-time TV mesh cost.

The prepared asset retains attribution to DamianToons and
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source's three
screen-material maps are excluded; the six housing maps remain. The blank glass
is replaced by the live metadata surface. Attribution and exact changes are
recorded in `_slot/MODEL_CREDITS.txt` and
`third_party/models/damiantoons-panasonic/source.json`, including source,
prepared-model and image hashes.

Reproduction: download the selected GLB through Sketchfab, then run Blender 4.5
with `--disable-autoexec --python-exit-code 1 --python
tools/consolebuild/import_tv.py -- SOURCE.glb`, followed by
`python -m tools.themebuild.television`. The original download is ignored under
`research/`; only the attributed prepared derivative and runtime image ship.
