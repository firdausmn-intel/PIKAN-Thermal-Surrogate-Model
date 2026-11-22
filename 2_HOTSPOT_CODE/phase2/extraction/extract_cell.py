"""Extract SKY130 sky130_fd_sc_hd__inv_1 layer rectangles from GDS + LEF.

Real geometry sources:
- GDS (poly, diffusion, li1, licon1, mcon): from the cell's own physical
  layout, converted from Manhattan polygons to (x, y, width, height) rects
  in microns, relative to the cell's own (0, 0) origin.
- met1 (VGND/VPWR power rails): from the cell's LEF abstract, which is the
  official PDK-declared abutment geometry for this cell (not present as
  drawn GDS boundaries in this particular repository's GDS export).

met2 is intentionally not extracted here: a standalone standard cell has no
met2 in either its GDS or LEF. met2 only appears once a power grid is
synthesized across a placed row/block, so it is added procedurally by
build_block.py and documented there as synthetic, not PDK-sourced.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gds_parser import parse_gds, flatten_top_structure

# SKY130 GDS (layer, datatype) drawing pairs used by this cell.
GDS_LAYERS = {
    "nwell": (64, 20),
    "diff": (65, 20),
    "poly": (66, 20),
    "licon1": (66, 44),
    "li1": (67, 20),
    "mcon": (67, 44),
}

CELL_PITCH_X_UM = 1.380000
CELL_PITCH_Y_UM = 2.720000


def polygon_to_rect(polygon_um):
    xs = [x for x, _ in polygon_um]
    ys = [y for _, y in polygon_um]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return (x0, y0, x1 - x0, y1 - y0)


def extract_gds_rects(gds_path):
    structures, units_per_micron = parse_gds(gds_path)
    top_name = next(iter(structures))
    layers_of_interest = set(GDS_LAYERS.values())
    flattened = flatten_top_structure(structures, top_name, layers_of_interest)

    rects_by_layer = {}
    for layer_name, layer_key in GDS_LAYERS.items():
        polygons = flattened.get(layer_key, [])
        rects = []
        for polygon in polygons:
            polygon_um = [(x / units_per_micron, y / units_per_micron) for x, y in polygon]
            rects.append(polygon_to_rect(polygon_um))
        rects_by_layer[layer_name] = rects
    return rects_by_layer


def extract_lef_met1_rects(lef_path):
    """Pull the RECT lines that appear under 'LAYER met1' blocks in the LEF."""
    text = Path(lef_path).read_text()
    rects = []
    for match in re.finditer(
        r"LAYER met1 ;\s*\n((?:\s*RECT[^\n]*\n)+)", text
    ):
        for rect_line in re.finditer(
            r"RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;",
            match.group(1),
        ):
            x0, y0, x1, y1 = (float(value) for value in rect_line.groups())
            rects.append((x0, y0, x1 - x0, y1 - y0))
    return rects


def main():
    cell_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/mnt/c/Users/PidotKing/Downloads/Research/HotSpot/phase2/pdk/"
        "skywater-pdk-libs-sky130_fd_sc_hd/cells/inv"
    )
    gds_path = cell_dir / "sky130_fd_sc_hd__inv_1.gds"
    lef_path = cell_dir / "sky130_fd_sc_hd__inv_1.lef"

    rects_by_layer = extract_gds_rects(gds_path)
    rects_by_layer["met1"] = extract_lef_met1_rects(lef_path)

    output_path = Path(__file__).resolve().parent / "inv_1_rects.py"
    with output_path.open("w", newline="\n") as file:
        file.write('"""Extracted sky130_fd_sc_hd__inv_1 rectangles, in microns."""\n\n')
        file.write(f"CELL_PITCH_X_UM = {CELL_PITCH_X_UM}\n")
        file.write(f"CELL_PITCH_Y_UM = {CELL_PITCH_Y_UM}\n\n")
        file.write("# (x, y, width, height) tuples, relative to cell origin (0, 0).\n")
        file.write("# nwell/diff/poly/licon1/li1/mcon: from GDS. met1: from LEF.\n")
        file.write("RECTS_BY_LAYER = {\n")
        for layer_name, rects in rects_by_layer.items():
            file.write(f"    {layer_name!r}: [\n")
            for x, y, width, height in rects:
                file.write(
                    f"        ({x:.6f}, {y:.6f}, {width:.6f}, {height:.6f}),\n"
                )
            file.write("    ],\n")
        file.write("}\n")

    for layer_name, rects in rects_by_layer.items():
        print(f"{layer_name}: {len(rects)} rects")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
