# PS1 disc appearance and motion study

2026-10-09. The user chose [Socket](https://depmots.com/socket) as the main inspiration.
This directory keeps the original local design prototype. The approved design is now
integrated into the PS1 shelf, baker and native helper and tested on the RG34XXSP.

## References and what they contribute

| Reference | Observed behaviour | Adaptation |
|---|---|---|
| [Socket official page](https://depmots.com/socket), [creator's demo](https://www.youtube.com/watch?v=jihWumXoXEk) | Physical media with distinct printed labels, small visible edges, material lighting and a central hub. The PS1 example around 19–20 seconds lowers the selected disc below the shelf; neighbouring discs remain in view. The site's GBA clip shows a turn, downward insertion and an iris transition. The creator identifies Godot as the engine. | Main visual reference: a readable disc face, modest perspective, a thin physical edge and purposeful movement. Keep this project's black background and opaque media. Our PS1 lid/spindle sequence is an original extension of the disc-drop idea. |
| [USB Loader GX disc renderer, pinned source](https://github.com/wiidev/usbloadergx/blob/e25c4f3501ed957b7db73f79c51fdf00715ab2e2/source/GUI/gui_diskcover.cpp) | Draws the disc shadow separately from its face; has distinct tilt and rotation parameters, with spin acceleration/deceleration. | Separate the cast shadow from the printed face and use a brief spin only after seating. Use elapsed time for motion, rather than porting frame-based increments. |
| [WiiFlow Lite coverflow, pinned source](https://github.com/Fledge68/WiiFlow_Lite/blob/69c0d4d61984f4ed6fca51b4520320cadfac960d/source/gui/coverflow.cpp) | Smoothly approaches target positions/angles and supports strong side yaw, mirror and shadow controls. This is a coverflow reference, not evidence of PS1 insertion. | Keep selection movement coherent and the hero artwork legible. Modest yaw is sufficient on a 720×480 panel; reflections and large rotations would compete with the label. |

These are design references. No Socket models, code, sounds or recordings are included in
the theme. No GPL source from the secondary projects is copied into our implementation.

## Disc construction

- One circular printed face with a separate thin edge and centre-bore wall. A black
  underside can be exposed by rotation. Ring geometry uses 96 segments.
- A single perspective camera also projects the console, drive and rigid rear hinge.
  Moving the disc into the drive changes its orientation in space; it does not stretch
  an already tilted screenshot into an ellipse.
- The centre bore uses the 15/120 diameter ratio. Nominal CD-ROM outer diameter,
  bore and substrate thickness are 120 mm, 15 mm and 1.2 mm in
  [ECMA-130, §§8.2/8.6/8.7](https://ecma-international.org/wp-content/uploads/ECMA-130_2nd_edition_june_1996.pdf).
  Prototype edge thickness is stylised for panel visibility, rather than a scale drawing.
- Printed pixels stay opaque. Neighbour dimming changes RGB, and never exposes the
  background through the disc. The bore and the space outside the circle are open.
- Stationary labels do not spin or shimmer. Supersampling keeps the rim, hole and
  lettering crisp. Lighting is restrained so artwork remains the focus.
- A separate shadow softens while the disc is high and tightens as it seats. The lid
  occludes the seated disc during closure. One final scene fade clears every object.

## Prototype timing

| Insert time | Behaviour |
|---|---|
| 0–210 ms | Console rises, rear lid opens and disc gives a small lift. |
| 114–532 ms | Disc tilts from the shelf pose to the drive plane and lowers onto the spindle. |
| 542–675 ms | Brief accelerating turn after seating. |
| 627–807 ms | Lid closes over the disc. |
| 817–941 ms | Entire scene fades to black. |

Insert lasts 950 ms; eject takes 850 ms. Eject omits the spin and ends upright in the
exact original selection pose. Timings are proposals for native implementation, not
measurements of A-button latency on the device.

## Reproduce and inspect

Requirements are already used by the theme builder: Python, Pillow, numpy and ffmpeg.

```powershell
python -m tools.discpreview.preview
```

This writes `build/shots/psx-study/{disc-motion.mp4,disc.png,poses.png,label.png}`.
Default labels are original fictional artwork. No game art is checked in or downloaded
by this tool. Optionally use three local square disc scans:

```powershell
python -m tools.discpreview.preview --labels LEFT.png CENTRE.png RIGHT.png --out-dir build/shots/psx-socket-preview
```

The local real-art example uses European LaunchBox `Disc` records: Tekken 3 database ID
2546 (`r2_ac8c5b9a-73dc-4d2a-ba95-f3fa599b4edb.png`), Crash Bandicoot ID 1006
(`8239ec36-1fd9-43c0-80c8-a15aecfc5445.png`), and Rayman ID 11542
(`0fa417bd-bb80-4c95-932b-850ad8a92071.png`). Sources are the public
[LaunchBox metadata archive](https://gamesdb.launchbox-app.com/Metadata.zip) and its
image host. Downloads and resulting game-art previews stay under ignored `build/`.

The exported movie is 720×480, 324 frames at 60 fps, 5.4 seconds: one selection change,
insert, an illustrative black game interval, eject, then a settled shelf. Generation
asserts a fully black launch endpoint and identical raw idle/eject-end pixels. Both
fictional and real-art contact sheets were visually reviewed, including lid occlusion.
This offline export does **not** establish 60 fps on the RG34XXSP.

## Initial integration plan (completed; results below)

1. Resolve the PS1 library and disc identities. The read-only probe found 25 CHD and
   three CUE files, versus 33 gamelist entries. Inspect the extra entries and CUE tracks
   before choosing what gets a face; do not rewrite the user's gamelist.
2. Extend the regional provider with a separate `Sony Playstation` / `Disc` index.
   The metadata contains 4,650 titles and 6,338 disc image records. Preserve aspect,
   alignment and circular printing. Own labels come first; a logo/text fallback should
   look like a printed disc. Avoid whole-CHD CRC reads. Multi-disc FFIX records lack
   useful disc-number fields in the current index; verify each image/disc mapping and
   region instead of applying one label to all four discs.
3. Bake the tilted shelf face and a flat native-motion texture from the same print.
   Use the existing opaque carousel and family toggle. Keep silent, optional video
   after three seconds, with a lower-disc window that clears the hub and rim.
4. Port the small model to the existing SDL/OpenGL helper, with textured mesh
   triangles for perspective and ring depth. Measure performance on the actual device.
   Preserve the early XML launch trigger and independent return layer. Ring sample
   points must avoid the bore, background and video window.
5. Validate A-button response, whole-disc clearance, scrolling, video on/off, family
   on/off and two composed-LCD return recordings. Preserve saves/settings with a fresh
   `.session` backup; restore and verify originals. PS1 is complete only after these
   device checks pass.

The installed integration bakes 28 regional disc prints from 31 CHD/CUE/BIN files.
US boot serials were verified for FFIX discs 1–4, Spyro 2/3 and Tekken 3. The FFIX US
scan filenames map to their visibly printed disc numbers; ambiguous multi-disc scans
fall back to an original logo/text print. Stale gamelist paths and the old Spyro CUE
reference are preserved. The boot-area probe used official `chdman` and the
[libchdr v5 header layout](https://github.com/rtissera/libchdr/blob/master/include/libchdr/chd.h);
it did not CRC or copy complete CHDs. Identity results stay in the device cache.

`tools/themebuild/discs.py` generates common model assets, homography and console band.
The Pillow-only baker writes shelf/backing PNGs, flat print PNGs and small native TGA
textures. `tools/slotlaunch/psx.h` projects tessellated planes and batches ring-edge
triangles through the existing SDL/GLES renderer. The camera, hinge and elapsed-time
motion match this study, with an exact poster at the return endpoint.

On-device insert captures measured 58.4 fps; composed-LCD eject measured 57.1–57.8 fps.
First insert frames appeared 158–163 ms after helper startup. Final Bugs Bunny/Crash
eight-second returns contain 127/125 samples, with 78/77 settled samples at t≥3 s:
zero black frames, blank rows or ring RGB changes, including release of the existing
independent layer. Video delay/reset, containment and both toggles passed. Held scroll
changed in 123/124 active samples; largest unchanged interval 34.2 ms. Evidence is in
ignored `build/shots/psx-*`. All 14 original saves, gamelist, profile and settings were
restored; one new and one modified save were preserved separately.
