# Storage cleanup, 18 October 2026

The active project is now the single `Slot_ESDE` checkout. Removed the clean,
retired `Slot_ESDE-models` and `Slot_ESDE-next-models` Git worktrees with
`git worktree remove --force`, after the source/dependency audit. Their branch
refs `models/dmg-psp-exemplars` (`65ceb249`) and `models/gbc-gba-exemplars`
(`cd6ca964`) remain in the main Git repository. No branch or commit was deleted.

The removed worktrees contained 5.866 GiB. Another 3.891 GiB of generated old
frame sequences and superseded frontend/payload files were deleted from the
active build tree. Source consolidation and recovery records occupy additional
space; these figures are gross removals, not a claim about net disk free space.

Preserved the selected runtime models and all alternative model settings,
textures, labels, hinges/slots, local NeilVFX files and full-detail originals.
Consolidated the still-required SNES/N64/GBA original sources, source archives,
maps and CAD reference inputs into the active `research/` paths. Updated the
quality auditor to verify the **current** selected sources rather than depending
on obsolete checkouts. Desktop probe scripts now use this checkout's libraries.

Recovered the exact prepared Retro TV GLB from `build/model-options/retro/` into
`third_party/models/denys-retro-tv/model.glb`, verifying its recorded SHA-256
`078f02623f47699c8ce413c9f5f803dda339374565bd68cd3b8739ef8136c0ce`.
It had previously existed only in a build directory. Panasonic and PVM prepared
models and source registrations were retained. No current model was replaced.

The roughly 7.5 GB `build/skraper-stage` and other scraper staging/work data were
preserved; they belong to ongoing unrelated work. Current rebuild tooling,
native libraries, source/material preparations and latest home-surface evidence
were also kept. Do not assume every ignored `build/` file is disposable.

## Audit and recovery

- Durable model/source hashes: `docs/BASELINE_ASSET_LOCK.json`, relative to the
  project parent. The lock excludes generated Python bytecode caches.
- Detailed local evidence: `build/storage-cleanup-20261018/`.
- `inventory-before.json`: names/sizes of 108,522 audited files.
- `source-checkpoint.zip`: 1,966 preserved code/asset/document entries from the
  old Git worktrees plus the active source checkpoint; ZIP CRC verified.
- `verified-copies.json`: 2,559 verified source/evidence copies (248.1 MiB).
- `generated-removals.json`: exact paths, sizes and SHA-256 of 11,161 deleted
  generated files. `generated-removal-result.json` records the completed action.
- `historical-evidence/`: compact old build logs, reports and scripts. Retired
  scan trials, old derived meshes, binaries, payloads and raw captures were
  intentionally not kept as extra multi-gigabyte backups.
- `worktrees.json` and `previous-runtime-hashes.json`: historical Git identities
  and runtime comparison hashes, without a dependency on a second checkout.

## Checks completed

- 177 host tests pass, with nine existing skips, before cleanup.
- All protected non-cache files verified after generated-file pruning and again
  after both worktrees were removed. The durable lock has 2,565 entries including
  the recovered exact Retro TV source.
- The quality auditor verifies 11 selected/original source hashes in this checkout.
- Pinned frontend source reapplies; host native SNES front probe builds and renders
  using this checkout's SDL/GLES libraries, GL error 0, 387,738 visible pixels.
- No handheld runtime/configuration/save was changed by this cleanup.

Next implementation state lives in `TABLETOP_HANDOFF.md`.

18 October scene-editor expansion: preserve the additional furniture sources,
original download archives, licences and runtime derivatives listed in
`docs/TABLETOP_FURNITURE_ASSET_LOCK.json`. They supplement the historical baseline
lock; ignored research files in this new inventory are required originals.
