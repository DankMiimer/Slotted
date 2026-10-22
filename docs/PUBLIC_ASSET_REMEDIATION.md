# Public asset derivatives

The 23 October 2026 public asset update removes a Kirby sticker from the selected
Game Boy's external albedo and all 68 affected rendered copies. It also removes
two decorative Retro TV decals of uncertain provenance from the public base-color
and ORM maps, the prepared GLB and the derived TV sprite.

The Game Boy remains Bram Verheyen's **CC BY-NC 4.0** model. The Retro TV remains
Denys Hroshko's **CC BY-NC 4.0** model. These edits do not make either model MIT,
public domain or commercially unrestricted. Original source and license links
are retained in [CREDITS.md](../CREDITS.md) and the model records. Hardware
identifying marks remain; no brand endorsement or comprehensive rights clearance
is claimed. Other NC/SA assets retain their conditions in [LICENSE_SCOPE.md](../LICENSE_SCOPE.md).

The repairs used generated replacement texture patches, integrated only inside
specified atlas rectangles. Every RGBA texel outside the GB rectangle
`[450,438,550,598]` and Retro rectangle `[704,948,980,1392]` matches its input.
GB repaint alpha was restored inside the repaired area; native fallback colors,
paint weights and texture hashes were refreshed. All GB geometry, normals,
indices and UVs remain unchanged. The Retro GLB was repacked without retaining
unreferenced copies of the old embedded images; its non-image buffer views and
normal map remain unchanged. Rendered derivatives were rebuilt through the
project's native renderer/Blender pipeline.

`release/asset-derivatives.json` pins the exact original and public-output hashes.
The exporter selects these reviewed copies without modifying the development
originals. Public clones already contain the corrected targets and can re-export
without the private originals or an image-generation service. A changed original,
derivative or unreviewed input fails validation instead of being accepted silently.

For a source-based GB texture rebuild in a public checkout, the reviewed shipped
albedo is reapplied only when the regenerated atlas matches outside the repair
rectangle. A changed UV layout or unrelated texels requires a new asset review.
Routine theme builds use the prepared corrected assets. Prepared Retro sources
already contain the corrected maps.

Private historical originals are retained outside the current public file set.
Earlier Git commits may still contain the previously uploaded artwork: this is
a forward update and does not erase repository history. No creator contact or
permission to third-party character art is implied by these changes.
