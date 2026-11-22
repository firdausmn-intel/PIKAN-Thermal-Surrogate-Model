"""Generate a deterministic congested 3D HotSpot Phase 1 case."""

from argparse import ArgumentParser
from pathlib import Path


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=64)
    parser.add_argument("--cols", type=int, default=64)
    parser.add_argument("--power-rows", type=int, default=10)
    parser.add_argument("--power-cols", type=int, default=10)
    parser.add_argument("--low-power", type=float, default=0.0005)
    parser.add_argument("--high-power", type=float, default=0.002)
    parser.add_argument("--hotspot-fraction", type=float, default=0.10)
    parser.add_argument("--output", type=Path, default=Path("generated"))
    return parser.parse_args()


def hotspot_cells(rows, cols, fraction):
    target = max(1, round(rows * cols * fraction))
    start = (rows * cols - target) // 2
    return {index for index in range(start, start + target)}


def write_floorplan(path, rows, cols, width, height, layer):
    cell_width = width / cols
    cell_height = height / rows
    with path.open("w", newline="\n") as file:
        for row in range(rows):
            for col in range(cols):
                name = f"L{layer}_R{row}_C{col}"
                x = col * cell_width
                y = row * cell_height
                file.write(
                    f"{name} {cell_width:.12g} {cell_height:.12g} "
                    f"{x:.12g} {y:.12g}\n"
                )


def write_layer_config(path, layers):
    silicon = "1.75e6\n0.01\n0.00015"
    tim = "4e6\n0.25\n0.00005"
    with path.open("w", newline="\n") as file:
        for layer, (material, powered) in enumerate(layers):
            file.write(f"# Layer {layer}\n{layer}\nY\n{powered}\n")
            file.write(f"{silicon if material == 'silicon' else tim}\n")
            file.write(f"layer_{layer}.flp\n\n")


def write_power_trace(
    path,
    rows,
    cols,
    layers,
    low_power,
    high_power,
    hotspot_fraction,
):
    cells = hotspot_cells(rows, cols, hotspot_fraction)
    names = []
    for layer, (_, powered) in enumerate(layers):
        if powered != "Y":
            continue
        for row in range(rows):
            for col in range(cols):
                names.append(f"L{layer}_R{row}_C{col}")
    with path.open("w", newline="\n") as file:
        file.write(" ".join(names) + "\n")
        values = []
        for layer, (_, powered) in enumerate(layers):
            if powered != "Y":
                continue
            for row in range(rows):
                for col in range(cols):
                    index = row * cols + col
                    value = high_power if index in cells else low_power
                    values.append(f"{value:.12g}")
        file.write(" ".join(values) + "\n")


def write_config(path, rows, cols):
    with path.open("w", newline="\n") as file:
        file.write(
            f"""-t_chip 0.00015
-k_chip 100.0
-p_chip 1.75e6
-c_convec 140.4
-r_convec 0.1
-s_sink 0.06
-t_sink 0.0069
-k_sink 400.0
-p_sink 3.55e6
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
""",
    )


def main():
    args = parse_args()
    dimensions = (args.rows, args.cols, args.power_rows, args.power_cols)
    if any(dimension < 1 for dimension in dimensions):
        raise ValueError("grid and power dimensions must be positive")
    if not 0 < args.hotspot_fraction <= 1:
        raise ValueError("hotspot fraction must be greater than 0 and at most 1")
    args.output.mkdir(parents=True, exist_ok=True)
    width = 0.001
    height = 0.001
    layers = [
        ("silicon", "Y"),
        ("tim", "N"),
        ("silicon", "Y"),
        ("tim", "N"),
        ("silicon", "Y"),
    ]
    for layer in range(len(layers)):
        write_floorplan(
            args.output / f"layer_{layer}.flp",
            args.power_rows,
            args.power_cols,
            width,
            height,
            layer,
        )
    write_layer_config(args.output / "phase1.lcf", layers)
    write_power_trace(
        args.output / "phase1.ptrace",
        args.power_rows,
        args.power_cols,
        layers,
        args.low_power,
        args.high_power,
        args.hotspot_fraction,
    )
    write_config(args.output / "phase1.config", args.rows, args.cols)
    with (args.output / "metadata.txt").open("w", newline="\n") as file:
        file.write(
            f"rows={args.rows}\ncols={args.cols}\n"
            f"power_rows={args.power_rows}\n"
            f"power_cols={args.power_cols}\n"
            f"width_m={width}\nheight_m={height}\n"
            "thickness_m=0.00055\n"
            "active_layers=0,2,4\n"
            "low_power_w=0.0005\n"
            "high_power_w=0.002\n"
            f"high_power_fraction={args.hotspot_fraction:.6g}\n"
        )


if __name__ == "__main__":
    main()