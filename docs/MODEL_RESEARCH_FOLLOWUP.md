# Follow-up research request

**Historical request:** independent work has since resolved several items below.
See [MODEL_INDEPENDENT_RESEARCH.md](MODEL_INDEPENDENT_RESEARCH.md) before reusing
this prompt: the PS1 originals, Vxcl original, CAD assembly, Printables licences,
Sony manual and controlled DS shader comparison no longer need the initial
checks requested here. The unresolved OEM dimensions and registered hinges do.

The first package contains useful source leads and nine downloaded files whose
hashes all check out. Please repair the evidence gaps below. Produce a corrected
research package; do not modify Slotters code or contact creators. Keep the
original report and identify every revised claim explicitly.

1. **Reconcile the documents.** Use one canonical per-feature measurements table
   to generate Markdown, JSON and rigging CSV. Resolve the SP 84/84.6 and
   24.4/24.3 discrepancy, DS card width/height and slot width, GBA label corner
   radius, candidate polygon counts, N64 flap author/licence and unsupported
   extra candidates. List source URL/page/figure, measurement method,
   uncertainty and confidence for each scalar. Unknown is a valid result.

2. **Correct the current-model description.** The current GBA cartridge is not
   a 12-triangle box: the source listing reports 5,802 triangles and our shipped
   derivative has 2,682. It already has an actual label recess, uses image-free
   geometry and inserts label-down. The DS also already inserts label-down and
   has twelve speaker perforations. The user still rejects the GBA cartridge's
   appearance. Diagnose actual silhouette/moulding defects from neutral views,
   not the erroneous primitive/texture explanation.

3. **Supply traceable original-hardware evidence.** Attach the specific Sony
   manual and page for the chosen PS1 revision and each dimensional claim.
   Supply original-hardware photos/diagrams for the N64 bay, GBA slot and both
   hinges. Give actual video links and timestamps showing contact, seating,
   spring doors, lid detents and DS push-push action. Distinguish proposed scene
   timings from measured hardware movement. Define each pivot's origin, axes
   and closed reference pose; show its registration to the console.

4. **Recheck the actual supplied CAD.** Dave Parker's SCAD defines width=57,
   depth=34.4, a 60-mm grip and fillet=1 label corners. Derive its assembled
   envelope from the actual fit transform and explain how the claimed 9.4/7.9/
   6.2-mm thicknesses follow, or retract them. Do not present replacement CAD as
   Nintendo drawings. The `pdaxrom` N64 shell halves measure 116 × 65 mm in the
   broad face plane; explain their intended cartridge and the claimed 75.5-mm
   height. Identify actual N64 flap blade/bearing surfaces rather than using
   full-file bounds, which are about 147.4 and 139.4 mm wide including features.
   Explain what evidence independently establishes the prior 118.5/120.5-mm
   Slotters bay estimates as OEM dimensions; otherwise keep them unverified.

5. **Repair asset provenance.** N64 deep dive says Tetsuo9999 / BY-NC-SA while
   CSV says Humble Bazooka / BY-NC-ND. Provide the exact original author, current
   licence notice, files/version and source links. Give exact repository URLs
   and per-file licences for the GitHub references. Our review could verify
   seven Sketchfab listings and their CC BY 4.0 metadata; it did not obtain or
   inspect their original model archives. Separate your actual mesh inspection
   from scene metadata and thumbnails. Do not infer console-only topology from
   the total count of a scene containing a monitor, controls or accessories.

6. **Inspect the leading PS1 and GBA sources.** If original editable downloads
   are available without bypassing account restrictions, provide them with
   hashes and neutral inspection views. Otherwise give exact acquisition links
   and state what remains unverified. Check one complete PS1 source before
   recommending grafting together two sources. Identify a coherent revision
   rather than silently mixing SCPH-5501 and SCPH-7501 details. Verify real
   separate parts, underside, lid interior, spindle and ports. For GBA compare
   Vxcl and ewaldc2028 against the standard original shell and replacement CAD.

7. **Reframe rendering advice for our actual inputs.** Current native meshes
   contain positions, normals and vertex colours, not UV textures. DS is
   currently excluded from Realistic shader selection, so test that explanation
   before claiming a missing acrylic layer causes its flat look. Cite primary
   technical sources for precision/performance claims and explain the normal
   matrix under nonuniform scale. Your shader needs review of untinted ambient,
   light-facing specular, energy allocation and expression precision. Do not
   promise 60 fps from nominal fillrate. Do not replace approved lit Realistic
   shelf renders with unlit albedo: ES displays those images, while the native
   animation draws actual 3D meshes. Keep baked tint sampling and hand-off
   consistency explicit. Treat material constants as tunable hypotheses unless
   supported by actual measurements.

Return a short change log, canonical measurements/evidence table, asset manifest,
corrected rigging data, unresolved questions and the original references. Preserve
confidence A for official manufacturer drawings/dimensions or standards; file
precision alone does not qualify. Avoid absolute “CAD truth”, “exact OEM” or
“only available model” claims that the evidence does not support.
