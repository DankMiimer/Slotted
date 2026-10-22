# Precision implementation evidence

2026-10-13, branch `codex/precision-responsiveness`. The user approved the refined
plan and asked us to revise assumptions as evidence warrants. Direction remains
accurate hardware with restrained cel shading. This is an in-progress record.

## Installed-build correction

Scarab reports 2026/05/11 00:09. Its [release recipe](https://github.com/knulli-cfw/knulli-linux/blob/20260511/package/emulationstation/knulli-emulationstation/knulli-emulationstation.mk)
pins frontend `4041b56a714265de81de8165b34fbd10f313a891`, rather than the newer
`10834d…` inspected during planning. Installed frontend SHA-256:
`d02c1f349952151ba5cd5b67125e848e95279483230d1582203efd44cf37af64`.
The release recipe establishes the source target; no reproducible binary rebuild
has yet established a byte-for-byte match.

The release's VLC stop/release is synchronous. The newer source uses an
asynchronous release. Do not attribute the newer behavior to this device.
The release still reinitializes the window/input/resources/audio after configgen.

## Protected test state

Fresh recoverable snapshot: `/userdata/system/slot-dev/sessions/precision-20261013-01`.
304 save/config/settings/gamelist files and 381 theme/hook files were copied with
SHA-256 verification before launching any test game. Restore preserves modified
and newly created test files separately before restoring the original data.
Runtime restoration is an explicit separate option.

`tools/dev/session_data.py` implements backup/audit/restore. The handheld restarted
during the network outage and received a new address. The persistent snapshot
survived; temporary fixtures had to be uploaded again. Device addresses are kept
only in the ignored connection file.

## Initial timing evidence

| Real PSP return probe | Original synchronous hook | Private-layer overlap prototype |
|---|---:|---:|
| Exit key to eject process start | 1.114 s | 1.004 s |
| Native render loop | 2.288 s | 2.276 s |
| Eject start to native process completion | 2.391 s | 2.401 s |
| Eject start to holder's shelf-ready detection | 4.660 s | 2.704 s |
| One right tap 150 ms after render loop ends | Lost | Lost |

These are captured runs, not uncaptured latency averages. Overlap removes most of
the serial recovery gap but does not meet the input target yet. It remains guarded
by `SLOT_RETURN_ASYNC=1`; the source installation hook does not enable it by default.
An additional return probe made before PPSSPP had finished booting is invalid and
excluded. Future probes must first confirm the running game and a stable game frame.

GBC navigation baseline covered taps, repetition, reversal and a hold. 356 primary
framebuffer samples had a maximum sampling gap of 36.49 ms and one gap over 33.3 ms.
Selection notifications followed taps by roughly 80–130 ms. Framebuffer CRCs and
sampling gaps do not establish internal renderer pacing or prove the stutter fixed.

Raw local evidence stays in ignored `build/precision/`, including the baseline,
overlap traces, composed screenshots and a diagnostic syscall trace. Heavy tracing
adds overhead and is not a normal timing result.

## Reusing the existing CD art surface

PS1 video now uses the art's existing inverse homography, full flat CD canvas,
outer radius and open bore. UMD video uses the same art projection and its smaller
printed canvas, with no invented central hole. Surface descriptions live in the
existing generated `shape.json`, beside the art masks; adding preview metadata
does not invalidate unchanged baked posters or motion textures.

Scarab treats nested shader paths as strings. `./shaders/media.glsl` silently
failed to resolve; `${currentPath}/shaders/media.glsl` works. The shader is one
pass on the existing selected video component. Alpha reveals the background
outside the physical surface and through the PS1 bore. There is one decoder,
the existing three-second delay, silent audio and the existing preview toggle.

Device evidence includes a full-disc gameplay preview and original synthetic
4:3, 16:9 and portrait clips. Their circle/square/grid shapes retain equal scale
in the flat media plane, with only the art's legitimate camera perspective.
The UMD case remains visible around the playing window.

The frontend ignores non-square source pixel metadata. A 320×480 SAR 2:1 fixture
was squeezed; a square-pixel 640×480 copy with the same 4:3 display aspect passed.
`tools/dev/prepare_video.py` prepares corrected copies with ffprobe/ffmpeg, keeps
source files intact and refuses to overwrite outputs. Metadata/cache integration
for general libraries is still to be settled; do not claim all anamorphic clips
are automatically handled by the theme.

The holder's PS1/UMD samples are moved off the live face onto neighboring shelf
art and static console/background points. Clock/status points remain excluded.
This needs a real return regression test before enabling the new helper generally.

## Continuation, 2026-10-14

Picked up from the interrupted session; the device matched the local tree byte-for-byte
before work started. Fresh data snapshot: `resume-20261013-01`.

### Scroll stutter: root cause found and fixed

`tools/dev/frame_pacing.py` timestamps real page flips (fb0 pan offset at about 2 kHz)
instead of sampling pixels. Our own `game-selected` hook was the per-tap stutter. ES
runs event scripts by forking itself on the main thread and waiting for the fork; a
traced tap blocked the main thread for 60–75 ms (clone plus wait4), right as the slide
starts.

| PS1 shelf navigation | Hook installed | Hook removed |
|---|---|---|
| 8 rapid taps, p99 / max frame interval | 67.0 / 67.2 ms | 21.9 / 26.8 ms |
| intervals over 25 ms | 20 | 2 |
| spaced taps, p99 / max | 50.4 / 83.7 ms | 20.9 / 49.7 ms |

The watcher now starts from ES's `start` event (and `game-start` as fallback); the
installer removes only our legacy `game-selected` file. The 650 ms slide length was not
the cause; it stays as the user requested more animation frames.

Remaining: leaving a game whose preview is already playing stalls 105–134 ms. Traced:
one main-thread join of a VLC thread inside `libvlc_media_player_stop`. Neither
`:avcodec-threads=1` nor `:no-audio` changed it (tested, reverted). The installed ES
stops VLC synchronously; newer upstream source releases it asynchronously, so a future
Knulli frontend update should remove this without theme changes.

### Return: overlap enabled by default

Probe: `tools/dev/return_probe.py` (taps every 0.25 s after the eject render loop
ends; the last N taps that moved the cursor were accepted).

| First accepted press after eject motion ends | Synchronous | Overlapped |
|---|---|---|
| PSP Angry Birds (2.1 s eject) | 2.51 s | 0.26–0.30 s |
| GBA (1.4 s eject) | 2.52 s | 0.81–1.01 s |
| PS1 Bugs Bunny (1.2 s eject) | about 2.3 s (Codex) | 1.01–1.07 s |

Final holder, every shelf family (first accepted press after motion ends; taps are
0.25 s apart, so values near 0.3 s mean input was live as the motion ended):

| System | Eject | First accepted | Holder released by |
|---|---|---|---|
| GB / GBC / DS | 2.1 s | 0.28–0.31 s | shelf match or press |
| PSP | 2.1 s | 0.26 s | shelf match |
| SNES / NES / N64 / MD / Pico-8 | 1.4–1.5 s | 0.78–0.81 s | press or shelf match |
| GBA | 1.4 s | 0.81 s | press |
| PS1 | 1.2 s | 1.01 s | press |

All eleven captures have no black cart-band frames after the motion (raw evidence in
ignored `build/resume/*-newholder-1/`).

Timing split (GBA): the gameStop hook releases configgen 0.23 s into the eject; Knulli's
system gameStop scripts, a fixed `time.sleep(0.5)` and interpreter exit take 1.2 s; then
ES needs about 1.1 s (window, textures, input). Short ejects therefore still finish about
0.8–1.0 s before input is live. The remaining gap is outside the theme unless short ejects
are lengthened.

Fixes found while enabling it:
- Holder released on a stale ES selection notification and revealed an empty shelf while
  ES was still loading textures (4 black frames). Now: configgen exit plus an ES page
  flip, then a pixel match; a press with the cart row drawn; or a relaunch. Captures for
  GBA, PSP and PS1 have no black cart-band frames afterwards.
- Relaunch during the hold left the old shelf over the hidden insert for 5 s. ES writing
  `/tmp/game.xml` now releases the holder; a scene lock serializes eject, holder and insert.
  Verified on PS1 with A pressed 0.8–1.3 s after eject.

### PS1 hub edge

The video's antialiased inner edge let printed poster art blend into a coloured fringe
on the left/right of the hub. The shader now draws a 2.5 px moulded hub edge concentric
with the bore, so small poster/video misalignment cannot show. Verified on device.

### Longer short ejects (user approved)

GBA, SNES, NES, N64, MD, Pico-8 and PS1 ejects now last 1.75 s plus the 350 ms hold,
like GB/DS/PSP. New beats instead of slow motion: carts spring part-way out of the slot
and hold (damped spring, about 4% overshoot); the PS1 lid springs open while the disc
spins down one full turn. Real returns: ES is back 0.02–0.07 s before the motion ends;
the probe's second tap (0.26–0.31 s) is accepted on PS1, GBA and SNES; ejects run at
53.6–54.1 fps under capture; no black cart-band frames.

## Next gates
- Prepare measured DMG/PSP reference cards and native visual exemplars. The current
  models remain approximate; no physical-accuracy replacement is accepted yet.
- Verify cartridge-specific and mixed-region video surfaces before expanding the
  full-window treatment beyond optical media.
