# Build and install a development candidate

Slotted needs its native frontend extension as well as its theme. The prepared
build below was host-tested on Ubuntu 24.04 x86-64 under WSL, with AArch64 GCC/G++
13.3.0 (`13.3.0-6ubuntu2~24.04`). The target is the RG34XXSP H700/Knulli library
set. This is a development workflow; a compiled package is not hardware acceptance.

## Prepare a fresh build

Install Python 3.11+, Git, CMake, pkg-config, dpkg-deb, make,
gcc-aarch64-linux-gnu, g++-aarch64-linux-gnu and binutils-aarch64-linux-gnu using
your host's package manager. Install the Python requirements in a virtual
environment. The setup tool does not install global packages or contact a device.

Supply these **AArch64 libraries from your own matching firmware** in a local
directory. Follow symlinks when copying; keep them outside published source:

```text
libasound.so.2       libcurl.so.4              libespeak.so.1
libfreeimage.so.3    libfreetype.so.6          libmali.so
libpulse.so.0        libSDL2_image-2.0.so.0    libSDL2_mixer-2.0.so.0
libSDL2-2.0.so.0     libudev.so.1              libvlc.so.5
```

`libmali.so` is the firmware's Mali library whose runtime SONAME is
`libmali.so.0`. The tool makes its own small EGL linker script. Neither firmware
libraries nor the author's sysroot are redistributed in the standalone bundle.

From a fresh public checkout, choose a new workspace and run:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m tools.frontend.prepare_build \
  --output "$HOME/slotted-sdk" \
  --libraries /absolute/path/to/your/firmware-libraries \
  --download-headers
SLOT_ES_BUILD_ROOT="$HOME/slotted-sdk" sh tools/frontend/build.sh
python3 -m tools.frontend.build_helper \
  --workspace "$HOME/slotted-sdk" --output "$HOME/slotted-sdk/slot-launch"
```

Preparation fetches Knulli frontend commit
`4041b56a714265de81de8165b34fbd10f313a891`, initializes its pinned pugixml
submodule and applies the Slotted extension. It downloads the 17 exact Ubuntu
API-header packages in `release/frontend-headers.json` and SDL 2.32.8 public
headers, verifying SHA-256 before extraction. These are headers, not host
libraries; the compiler's target standard headers take precedence. The build
links the supplied target firmware libraries.

`--packages /absolute/path/to/cached/debs` can reuse the verified 17 `.deb`
downloads from an earlier workspace. The SDL header archive is still fetched
and hash-checked. An existing workspace/output is refused. Keep failed workspaces
for diagnosis and use a different path when preparing another attempt.

The local `build-inputs.json` records library SONAMEs, packages, API/header
hashes and submodules. `native-build.json` records the input receipt hash,
compiler and resulting frontend hash. The helper has a separate adjacent JSON
receipt. Verification rejects altered inputs or patched source. Builds are
repeatable from pinned inputs; byte-identical binaries across paths/hosts have
not been established.

## Create and inspect a complete package

Make a clean public export, then package from its exact verified file manifest:

```sh
python3 -m tools.publication.export --output build/public-candidate
python3 -m tools.slotted.standalone \
  --source build/public-candidate \
  --frontend "$HOME/slotted-sdk/frontend/emulationstation" \
  --helper "$HOME/slotted-sdk/slot-launch" \
  --output build/standalone-candidate
python3 -m tools.slotted.standalone --inspect build/standalone-candidate
```

The bundle contains `payload.tar`, its exact member manifest, the compatible
frontend and `release.json` with checksums and required firmware-library hashes.
It includes Slotted XML/graphics, public shared runtime/models, all prepared
TV/table parts, launch helper, source asset credits and four compiled dependency
notices. Saved top-level `scene-layouts/*.json` profiles generate the packaged
native scenes and take precedence over older prepared derivatives. Packaging
does not rewrite those JSON files, private models, browser drafts or originals.

Inspection checks every archive member, hash, executable mode, required model,
scene-part reference, frontend/helper ABI and capability marker. ROMs, BIOS,
saves, device credentials and firmware libraries are excluded. Public assets
retain their own CC/OFL/CC0 terms, including NonCommercial and ShareAlike; the
MIT license on original code does not grant unrestricted rights to those assets.

If distributing a binary, retain the matching public source export, upstream
pin, build receipts and dependency notices. No Omega Zero code/assets are used.

## Fresh install and existing-device updates

Set `SLOT_DEVICE` to your SSH target using key authentication, or use the ignored
`tools/dev/device.txt`. Return to the frontend and close any running game.

For a device with **no existing Slotted theme**, the complete transaction is:

```sh
python3 -m tools.slotted.install --standalone build/standalone-candidate --activate
```

It checks the frontend, package and all 12 direct firmware-library hashes before
stopping the frontend; a different library set is refused. It then takes a fresh
session-data snapshot, retains startup-hook configuration and the prior binary,
stages and verifies the complete runtime, and binds the candidate through the
existing persistence mechanism. Ordinary Knulli startup owns the frontend
process. A failed transaction retains failed staging/assets and attempts to
restore the previous theme, latest snapshot, hook and frontend before restarting.
Read the transaction status and recovery paths even when the host loses SSH.

The fresh-install path **refuses an existing Slotted folder**. It cannot update
over authored layouts or local model selections. Existing installations can use
the preserving theme-only update:

```sh
python3 -m tools.slotted.install --activate
```

That keeps the installed Slotted `_slot` runtime and frontend. On the historical
migration path it copies runtime from Art Book Slot only if Slotted has none;
`--resync-slot` explicitly opts into copying Art Book Slot again. Keep Art Book
Slot and all recovery binaries until Slotted is accepted. Updating an existing
native frontend/layout set uses the established protected trial/editor workflow,
not the fresh standalone command.

## Verification state, 23 October 2026

A fresh upstream clone/submodule, all 17 verified header downloads, ARM64
frontend build and helper build completed successfully. A complete package from
the verified public source was inspected on the host. Synthetic failure tests
cover unsafe archives, missing parts, altered inputs, preservation and staging
rollback. The new fresh-install transaction has **not been device-tested**.
The installed RG34XXSP binary remains `a1780e4a…` (Slotted/frontend ax).
Native visual regression, measured target performance, interruption trials and
the public-preview acceptance gates remain in the forward plan.
