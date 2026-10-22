"""Makes a copy of Raster Forge that EmulationStation renders on its pixel grid.

    build/.venv/Scripts/python third_party/raster-forge/make_es_font.py

Raster Forge (CC0) ships without hinting tables, so FreeType grid-fits it with its auto-hinter,
which at sizes such as 24 px narrows some stems by a pixel and leaves soft columns. Adding empty
bytecode tables makes FreeType treat it as a hinted TrueType font whose instructions do nothing,
and a gasp table asks for smoothing without grid-fitting. The outlines already sit on a 256-unit
grid (8 px per em), so left alone they render crisp at every multiple of 8 px.
"""
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram

HERE = Path(__file__).resolve().parent


def empty_program():
    program = ttProgram.Program()
    program.fromBytecode(b'')
    return program


def main():
    font = TTFont(HERE / 'RasterForge.ttf')
    for tag in ('fpgm', 'prep'):
        table = newTable(tag)
        table.program = empty_program()
        font[tag] = table
    gasp = newTable('gasp')
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x0002}  # GASP_DOGRAY: smooth, no grid-fitting
    font['gasp'] = gasp
    for record in font['name'].names:
        if record.nameID == 5:
            record.string = record.toUnicode() + '; empty hinting tables for EmulationStation'
    font.save(HERE / 'RasterForge-ES.ttf')


if __name__ == '__main__':
    main()
