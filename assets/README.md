# Public build assets

The public source export populates `tabletop/`, `source-furniture/` and
`restore-map.json` here from explicitly reviewed inputs. These are byte-for-byte
copies of the selected prepared assets and the three furniture source GLBs.
Run `python -m tools.publication.restore_assets` to restore their expected local
build/research paths. Existing differing files are never overwritten.

Each restore-map entry records original path, destination, SHA-256 and license
context. Creator attribution and change records are in the root `CREDITS.md`,
`release/model-licenses.json` and the relevant per-model provenance. Some assets
are NonCommercial/ShareAlike; root MIT does not override their terms.

This development checkout keeps these copies in ignored source/build locations
until an export is made. Device snapshots, private models, library artwork and
arbitrary research downloads are not part of this pack. Use your own properly
licensed game labels; neutral editor cartridge faces may appear blank.
