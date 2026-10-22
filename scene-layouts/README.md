# Authored scenes — preserve these files

`snes-panasonic.json` is the user's current saved renderer layout, including the
camera and twelve independently positioned cartridges. It overrides source-code
composition defaults. Do not reframe or replace it during builds or cleanup.

Reopen **Open Scene Editor.cmd** in the project root whenever the scene needs
adjusting. Use **Save layout to renderer** to update this JSON and regenerate
`build/tabletop/assets/layouts/snes-panasonic.scene`. The launcher also regenerates
that derivative from the saved JSON when starting the server. Unsaved browser
drafts stay local until saved.

`n64-panasonic.json` / `nes-panasonic.json` appear once the user saves those
consoles in the editor (console picker); until then the device uses the SNES layout
for them. Treat them exactly like the SNES file. History for them is prefixed
`n64-` / `nes-` in `history/`.

`checkpoints/` contains the exact eight-cartridge layout submitted by the user
before requesting four more. `history/` holds previous versions on future saves.
Retain both across handoffs and storage cleanup. The current JSON takes precedence
over checkpoints. Instructions: `tools/tabletop/editor/README.md`.
