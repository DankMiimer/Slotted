"""BPoole's Game Boy Color Model for the native presentation (Blender 4.5).

blender -b --factory-startup --disable-autoexec --python bpoole_gbc.py -- SOURCE.glb
Then: python -m tools.consolebuild.textured gbc

Source: https://sketchfab.com/3d-models/game-boy-color-model-a3dad19c800f4c61a931865f14870768
CC BY 4.0, BPoole. Processing code MIT. The original download stays untouched in
research/; the registered master and per-corner geometry go to ignored build/.
"""
import json, sys, statistics
from pathlib import Path
from mathutils import Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textured_blender as tb

SOURCE_URL = 'https://sketchfab.com/3d-models/game-boy-color-model-a3dad19c800f4c61a931865f14870768'
CGB_SCALE = 168 / 78
GAME_PAK_MM = (57, 65.5, 7.8)
# The fixed half Game Pak is replaced by the existing independent, ROM-labelled
# Game Pak. Battery contacts/springs sit under the fitted cover and are hidden.
REMOVE = {'Cartridge_low', 'Battery_Metal_01', 'Battery_Metal_02', 'Back_Spring_01',
          'Back_Spring_02', 'Battery_Protrution_01', 'Battery_Protrution_02'}
NAMES = {'Gameboy_Shell_low': 'CGB housing', 'Gameboy_Back_low': 'CGB battery cover',
         'Gameboy_Screen': 'CGB LCD glass', 'Gameboy_Screws': 'CGB rear screws',
         'A_Button': 'Action button A', 'B_Button': 'Action button B',
         'Select_Button': 'SELECT button', 'Start_Button': 'START button',
         'Directional_Button': 'Continuous D-pad', 'Volume_Wheel': 'CGB volume wheel',
         'Gameboy_Switch': 'CGB power switch', 'Gameboy_ChargerBase': 'CGB power socket'}


def seat_cover(shell, cover):
    """Move the displaced battery cover forward until its outer surface continues
    the housing's back surface just outside the opening (median of edge samples)."""
    lo, hi = tb.bounds([cover])
    gaps = []
    for t in [i / 8 for i in range(1, 8)]:
        x, z = lo.x + (hi.x - lo.x) * t, lo.z + (hi.z - lo.z) * t
        for outside, inside in (((x, lo.z - .12), (x, lo.z + .12)), ((x, hi.z + .12), (x, hi.z - .12)),
                                ((lo.x - .12, z), (lo.x + .12, z)), ((hi.x + .12, z), (hi.x - .12, z))):
            a = tb.ray(shell, (outside[0], 40, outside[1]), (0, -1, 0))
            b = tb.ray(cover, (inside[0], 40, inside[1]), (0, -1, 0))
            if a and b:
                gaps.append(b.y - a.y)
    offset = statistics.median(gaps)
    cover.data.transform(Matrix.Translation((0, -offset, 0)))
    cover.data.update()
    return offset, len(gaps)


def main():
    source = Path(sys.argv[sys.argv.index('--') + 1])
    work = tb.ROOT / 'build/textured/gbc'
    objects = tb.import_source(source)
    cart = objects['Cartridge_low']
    cart_lo, cart_hi = tb.bounds([cart])
    shell = objects['Gameboy_Shell_low']
    shell_lo, shell_hi = tb.bounds([shell])
    # Rear lip: lowest height at which a ray from behind the cart's centreline
    # passes the housing's back wall instead of stopping on it. The label is
    # clipped there; below it the wall hides the Game Pak.
    lip_z = None
    for i in range(2000):
        z = cart_lo.z + (cart_hi.z - cart_lo.z) * i / 2000
        hit = tb.ray(shell, (0, 40, z), (0, -1, 0))
        if not hit or hit.y < cart_hi.y:
            lip_z = z
            break
    assert lip_z is not None, 'No rear cartridge opening found'
    mm = GAME_PAK_MM[0] / (cart_hi.x - cart_lo.x)
    cart_centre_y = (cart_lo.y + cart_hi.y) / 2
    for name in REMOVE:
        tb.bpy.data.objects.remove(objects.pop(name), do_unlink=True)
    offset, samples = seat_cover(shell, objects['Gameboy_Back_low'])
    kept = []
    for old, o in sorted(objects.items()):
        o.name = NAMES[old]
        o['source_part'] = old
        kept.append(o)
    centre = (shell_lo + shell_hi) / 2
    k = tb.to_native(kept, centre, mm, CGB_SCALE)
    q = mm * CGB_SCALE  # native units per source unit
    housing_lo, housing_hi = tb.bounds([o for o in kept if o.name == 'CGB housing'])
    all_lo, all_hi = tb.bounds(kept)
    glass = next(o for o in kept if o.name == 'CGB LCD glass')
    glass_lo, glass_hi = tb.bounds([glass])
    registration = dict(
        model='gbc', adapter='bpoole_gbc.py', author='BPoole', title='Game Boy Color Model', url=SOURCE_URL,
        licence='CC-BY-4.0', licence_url='https://creativecommons.org/licenses/by/4.0/',
        source_file=source.name, source_sha256=tb.sha256(source),
        mm_per_source_unit=mm, native_units_per_mm=CGB_SCALE,
        scale_basis='Uniform; source Game Pak width = 57 mm (matches the independent CGB Game Pak)',
        housing_mm=[(shell_hi[i] - shell_lo[i]) * mm for i in range(3)],
        battery_cover_seated_forward_source_units=offset, battery_cover_edge_samples=samples,
        removed_source_parts=sorted(REMOVE),
        spec=dict(ry=housing_hi.z * 100, depth=(housing_hi.y - housing_lo.y) * 50,
                  slot=(lip_z - centre.z) * q),
        cart_label_native=-(cart_centre_y - centre.y) * q - GAME_PAK_MM[2] / 2 * CGB_SCALE,
        native_bounds=[[all_lo.x * 100, all_lo.z * 100, -all_hi.y * 100],
                       [all_hi.x * 100, all_hi.z * 100, -all_lo.y * 100]],
        lcd_glass_mm=[(glass_hi.x - glass_lo.x) * 100 / CGB_SCALE, (glass_hi.z - glass_lo.z) * 100 / CGB_SCALE],
        modifications=['Uniform registration to the native CGB frame', 'Remove the fixed half Game Pak',
                       'Remove battery contacts/springs hidden under the cover',
                       'Seat the displaced battery cover against the housing rim',
                       'Blank the baked game screenshot and exclude fixed Game Pak art from the atlas',
                       'Opaque glass composited over a dark LCD; source normal/ORM maps not rendered'])
    flags = {'CGB housing': dict(role='paint'), 'CGB battery cover': dict(role='paint'),
             'CGB LCD glass': dict(role='lcd')}
    tb.write_corners(kept, work, flags)
    (work / 'registration.json').write_text(json.dumps(registration, indent=2) + '\n')
    target = tb.ROOT / 'theme/art-book-slot/_slot/consoles/gbc'
    # Full-detail textured master (source maps, fixed art) stays in ignored build/.
    tb.export_master_glb(kept, work / 'model-master.glb')
    provenance = dict(source_creator='BPoole', source_licence='CC-BY-4.0', source_url=SOURCE_URL)
    tb.export_geometry_glb(kept, target / 'model.glb', CGB_SCALE, provenance=provenance)
    tb.export_geometry_glb(kept, target / 'model-master.glb', CGB_SCALE, provenance=provenance)
    tb.export_geometry_glb(kept, target / 'model-physical.glb', CGB_SCALE, physical=True, provenance=provenance)
    print('GBC PREPARED', json.dumps(registration['spec']), 'cover offset', round(offset, 4), flush=True)


if __name__ == '__main__':
    main()
