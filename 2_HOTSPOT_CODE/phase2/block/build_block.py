"""Tile SKY130 sky130_fd_sc_hd__inv_1 into a small abutted block for HotSpot.

Data provenance (documented explicitly, not asserted uniformly as "real"):
- front_end (poly + diffusion + licon1 contacts): REAL, from GDS.
- li1 (+ mcon contacts): REAL, from GDS.
- met1 (VGND/VPWR rails): REAL, from LEF (official PDK abstract geometry).
- met2: SYNTHETIC. A standalone standard cell has no met2 in either its GDS
  or LEF; met2 only appears once a power grid is synthesized above a placed
  row. The vertical straps here are a documented, illustrative proxy, not
  PDK-sourced data.

Material thermal properties (specific heat, resistivity) below are
approximate bulk literature values for tungsten (li1) and aluminum
(met1/met2), not PDK-calibrated thermal figures; the SKY130 PDK publishes
electrical, not thermal, properties for these layers.
"""

import sys
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "extraction"))

from inv_1_rects import RECTS_BY_LAYER, CELL_PITCH_X_UM, CELL_PITCH_Y_UM

UM_TO_M = 1e-6

# (specific_heat J/(m^3.K), resistivity (m.K)/W, thickness m)
# Thicknesses are nanometer-scale FEOL/BEOL layers, not Phase 1's bulk
# chip/die thickness; using die-scale thickness here would give these
# layers an unrealistically large lateral cross-section, over-conducting
# heat sideways and washing out any local gradient.
LAYER_MATERIALS = {
    "front_end": (1.75e6, 0.01, 3e-7),         # silicon FEOL, ~300nm
    "li1": (2.58e6, 0.00578, 1e-7),            # tungsten, ~100nm, approximate
    "met1": (2.42e6, 0.00422, 3.6e-7),         # aluminum, ~360nm, approximate
    "met2": (2.42e6, 0.00422, 3.6e-7),         # aluminum, ~360nm, approximate
    "tim": (4e6, 0.25, 0.00005),               # same TIM as Phase 1
}

MET2_STRAP_WIDTH_UM = 0.14
MET2_STRAP_PITCH_UM = 0.46


def next_power_of_two(value):
    power = 1
    while power < value:
        power *= 2
    return power


def union_bounds(rects_by_layer):
    """HotSpot requires every layer's own bounding box to match exactly, so
    the true simulation domain must be the union across all layers."""
    all_rects = [rect for rects in rects_by_layer.values() for rect in rects]
    min_x = min(x for x, y, w, h in all_rects)
    min_y = min(y for x, y, w, h in all_rects)
    max_x = max(x + w for x, y, w, h in all_rects)
    max_y = max(y + h for x, y, w, h in all_rects)
    return min_x, min_y, max_x, max_y


def shift_rects(rects, offset_x, offset_y):
    return [(x + offset_x, y + offset_y, w, h) for x, y, w, h in rects]


def add_corner_fillers(rects, domain_width, domain_height, cell_size_um):
    """Force this layer's own bounding box to exactly match the shared
    domain, by adding two epsilon-sized inert units at opposite corners.
    Without this, HotSpot's per-layer get_total_width/height (a bounding
    box of that layer's own units only) would differ across layers and
    HotSpot would refuse to run ("width and height differ across layers").
    """
    return rects + [
        (0.0, 0.0, cell_size_um, cell_size_um),
        (domain_width - cell_size_um, domain_height - cell_size_um, cell_size_um, cell_size_um),
    ]


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--hot-cells", type=int, default=1)
    parser.add_argument("--hot-start", type=int, default=0)
    parser.add_argument("--low-power", type=float, default=5e-8)
    parser.add_argument("--high-power", type=float, default=5e-6)
    parser.add_argument(
        "--cell-powers",
        type=float,
        nargs="+",
        help="Explicit list of total power values (W) per cell instance.",
    )
    parser.add_argument("--cell-size-um", type=float, default=0.02)
    parser.add_argument("--output", type=Path, default=Path("generated"))
    return parser.parse_args()


def tiled_rects_by_cell(layer_names, cell_count):
    """Repeat one or more layers' rectangles across N abutted instances.

    Returns a flat list grouped by cell instance (all of instance 0's
    rects, then all of instance 1's, ...), so callers can recover which
    cell instance a rect belongs to via integer division.
    """
    rects = []
    rects_per_cell = sum(len(RECTS_BY_LAYER[name]) for name in layer_names)
    for instance in range(cell_count):
        offset_x = instance * CELL_PITCH_X_UM
        for layer_name in layer_names:
            for x, y, width, height in RECTS_BY_LAYER[layer_name]:
                rects.append((x + offset_x, y, width, height))
    return rects, rects_per_cell


def met2_straps(cell_count):
    """Synthetic vertical power-grid straps spanning the block height."""
    block_width = cell_count * CELL_PITCH_X_UM
    rects = []
    position = MET2_STRAP_PITCH_UM / 2
    while position < block_width:
        rects.append(
            (position - MET2_STRAP_WIDTH_UM / 2, 0.0, MET2_STRAP_WIDTH_UM, CELL_PITCH_Y_UM)
        )
        position += MET2_STRAP_PITCH_UM
    return rects


def write_floorplan(path, rects_um, layer_prefix):
    with path.open("w", newline="\n") as file:
        for index, (x, y, width, height) in enumerate(rects_um):
            file.write(
                f"{layer_prefix}_{index} {width * UM_TO_M:.9g} "
                f"{height * UM_TO_M:.9g} {x * UM_TO_M:.9g} {y * UM_TO_M:.9g}\n"
            )


def write_layer_config(path, layer_order):
    with path.open("w", newline="\n") as file:
        for layer_index, (layer_name, powered) in enumerate(layer_order):
            specific_heat, resistivity, thickness = LAYER_MATERIALS[layer_name]
            file.write(f"# Layer {layer_index}: {layer_name}\n")
            file.write(f"{layer_index}\nY\n{powered}\n")
            file.write(f"{specific_heat:.6g}\n{resistivity:.6g}\n{thickness:.6g}\n")
            file.write(f"layer_{layer_index}_{layer_name}.flp\n\n")


def write_power_trace(path, layer_order, rects_by_layer, rects_per_cell_by_layer, filler_count, hot_start=0, hot_cells=1, low_power_total=5e-8, high_power_total=5e-4, cell_powers=None):
    """Distribute a realistic TOTAL power per cell across its real shapes,
    weighted by each shape's area. Assigning the same flat power value to
    every shape regardless of size (poly, each diffusion, each of 11 licon
    contacts) would overcount total cell power by roughly the shape count,
    and applying tile-scale (Phase 1) power values to micron-scale real
    transistor features produces unphysical power density and temperatures.
    """
    names = []
    values = []
    for layer_index, (layer_name, powered) in enumerate(layer_order):
        if powered != "Y":
            continue
        rects = rects_by_layer[layer_name]
        rects_per_cell = rects_per_cell_by_layer[layer_name]
        real_count = len(rects) - filler_count
        num_cells = real_count // rects_per_cell
        for cell_instance in range(num_cells):
            cell_rects = rects[cell_instance * rects_per_cell:(cell_instance + 1) * rects_per_cell]
            cell_area = sum(width * height for _, _, width, height in cell_rects)
            if cell_powers is not None and cell_instance < len(cell_powers):
                total_power = cell_powers[cell_instance]
            else:
                is_hot = hot_start <= cell_instance < hot_start + hot_cells
                total_power = high_power_total if is_hot else low_power_total
            for offset, (_, _, width, height) in enumerate(cell_rects):
                index = cell_instance * rects_per_cell + offset
                names.append(f"{layer_name}_{index}")
                area_fraction = (width * height) / cell_area if cell_area else 0.0
                values.append(total_power * area_fraction)
        for index in range(real_count, len(rects)):
            names.append(f"{layer_name}_{index}")
            values.append(0.0)
    with path.open("w", newline="\n") as file:
        file.write(" ".join(names) + "\n")
        file.write(" ".join(f"{value:.9g}" for value in values) + "\n")


def write_config(path, rows, cols, domain_width_um, domain_height_um):
    """Microscale package: Phase 1's chip-scale package (3cm spreader default,
    6cm sink) was never overridden here before, and completely dominated our
    ~11 x 3.2 um die, washing out any local gradient. Spreader/sink are now
    explicitly sized just larger than the die footprint, using an epoxy
    mold-compound-like encapsulant (not a metal heatsink) and a board-level
    convective resistance appropriate for a small, unheatsinked die. These
    are illustrative engineering approximations, not a specific real
    substrate/board spec.
    """
    max_extent_m = max(domain_width_um, domain_height_um) * UM_TO_M
    spreader_side_m = max_extent_m * 3
    sink_side_m = max_extent_m * 6
    with path.open("w", newline="\n") as file:
        file.write(
            f"""-t_chip 0.00015
-k_chip 100.0
-p_chip 1.75e6
-s_spreader {spreader_side_m:.9g}
-t_spreader 2e-06
-k_spreader 5.0
-p_spreader 1.65e6
-c_convec 0.001
-r_convec 100.0
-s_sink {sink_side_m:.9g}
-t_sink 5e-06
-k_sink 5.0
-p_sink 1.65e6
-t_interface 2.0e-05
-k_interface 4.0
-p_interface 4.0e6
-model_secondary 0
-ambient 318.15
-init_temp 318.15
-model_type grid
-grid_rows {rows}
-grid_cols {cols}
-grid_map_mode center
-thermal_threshold 354.95
-wrap_l2 0
-model_rim 0
"""
        )


def main():
    args = parse_args()
    if args.hot_cells < 0 or args.hot_cells > args.cells:
        raise ValueError("hot-cells must be between 0 and cells")
    if args.hot_start < 0 or args.hot_start + args.hot_cells > args.cells:
        raise ValueError("hot-start plus hot-cells must fit within cells")
    args.output.mkdir(parents=True, exist_ok=True)

    rects_by_layer = {}
    rects_per_cell_by_layer = {}
    rects_by_layer["front_end"], rects_per_cell_by_layer["front_end"] = (
        tiled_rects_by_cell(["poly", "diff", "licon1"], args.cells)
    )
    rects_by_layer["li1"], rects_per_cell_by_layer["li1"] = tiled_rects_by_cell(
        ["li1", "mcon"], args.cells
    )
    rects_by_layer["met1"], rects_per_cell_by_layer["met1"] = tiled_rects_by_cell(
        ["met1"], args.cells
    )
    rects_by_layer["met2"] = met2_straps(args.cells)

    layer_order = [
        ("front_end", "Y"),
        ("li1", "N"),
        ("met1", "N"),
        ("met2", "N"),
    ]

    # HotSpot derives the shared chip width/height from layer 0's own
    # bounding box, then uses every layer's absolute coordinates directly.
    # Real SKY130 rails legitimately extend below y=0 and above the nominal
    # cell pitch (rows share/straddle their boundary rails), so every
    # layer must be shifted into one common, non-negative coordinate
    # system, and every layer's own bounding box must match exactly.
    min_x, min_y, max_x, max_y = union_bounds(rects_by_layer)
    domain_width_um = max_x - min_x
    domain_height_um = max_y - min_y
    for layer_name in rects_by_layer:
        shifted = shift_rects(rects_by_layer[layer_name], -min_x, -min_y)
        rects_by_layer[layer_name] = add_corner_fillers(
            shifted, domain_width_um, domain_height_um, args.cell_size_um
        )
    filler_count = 2

    for layer_index, (layer_name, _) in enumerate(layer_order):
        write_floorplan(
            args.output / f"layer_{layer_index}_{layer_name}.flp",
            rects_by_layer[layer_name],
            layer_name,
        )

    write_layer_config(args.output / "block.lcf", layer_order)
    write_power_trace(
        args.output / "block.ptrace",
        layer_order,
        rects_by_layer,
        rects_per_cell_by_layer,
        filler_count,
        args.hot_start,
        args.hot_cells,
        args.low_power,
        args.high_power,
        cell_powers=args.cell_powers,
    )

    rows = next_power_of_two(max(1, round(domain_height_um / args.cell_size_um)))
    cols = next_power_of_two(max(1, round(domain_width_um / args.cell_size_um)))
    write_config(args.output / "block.config", rows, cols, domain_width_um, domain_height_um)

    with (args.output / "metadata.txt").open("w", newline="\n") as file:
        file.write(
            f"cell=sky130_fd_sc_hd__inv_1\n"
            f"cell_count={args.cells}\n"
            f"hot_cells={args.hot_cells}\n"
            f"hot_start={args.hot_start}\n"
            f"cell_pitch_x_um={CELL_PITCH_X_UM}\n"
            f"cell_pitch_y_um={CELL_PITCH_Y_UM}\n"
            f"block_width_um={domain_width_um}\n"
            f"block_height_um={domain_height_um}\n"
            f"grid_rows={rows}\n"
            f"grid_cols={cols}\n"
            f"low_power_total_per_cell_w={args.low_power}\n"
            f"high_power_total_per_cell_w={args.high_power}\n"
            f"cell_powers={args.cell_powers}\n"
            "front_end_source=GDS (poly, diff, licon1)\n"
            "li1_source=GDS (li1, mcon)\n"
            "met1_source=LEF (VGND/VPWR abutment rails)\n"
            "met2_source=SYNTHETIC (procedural power-grid proxy, not PDK data)\n"
            "material_note=li1/met1/met2 thermal properties are approximate "
            "bulk tungsten/aluminum literature values, not PDK-calibrated\n"
            "package_note=microscale package (mold-compound-like spreader/sink "
            "sized to the die, board-level r_convec), not Phase 1's chip-scale "
            "package; illustrative approximation, not a specific board spec\n"
        )

    print(f"grid_rows={rows} grid_cols={cols}")
    print(f"block: {args.output}")


if __name__ == "__main__":
    main()
