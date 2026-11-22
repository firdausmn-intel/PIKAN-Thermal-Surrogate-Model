"""Generate HotSpot inputs for a two-tier Phase 3D smoke test."""

from argparse import ArgumentParser
from math import isfinite, log2
from pathlib import Path


WIDTH_M = 0.001
HEIGHT_M = 0.001
SILICON_THICKNESS_M = 0.00015
TIM_THICKNESS_M = 0.00005


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=32)
    parser.add_argument("--cols", type=int, default=32)
    parser.add_argument("--power-rows", type=int, default=4)
    parser.add_argument("--power-cols", type=int, default=4)
    parser.add_argument("--hot-tier", type=int, choices=(0, 1), default=0)
    parser.add_argument("--hot-row", type=int, default=1)
    parser.add_argument("--hot-col", type=int, default=1)
    parser.add_argument("--low-power", type=float, default=0.0005)
    parser.add_argument("--high-power", type=float, default=0.002)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "smoke_test",
    )
    return parser.parse_args()


def write_floorplan(path, rows, cols, layer):
    cell_width = WIDTH_M / cols
    cell_height = HEIGHT_M / rows
    with path.open("w", newline="\n") as file:
        for row in range(rows):
            for col in range(cols):
                name = f"T{layer}_R{row}_C{col}"
                x = col * cell_width
                y = row * cell_height
                file.write(
                    f"{name} {cell_width:.12g} {cell_height:.12g} "
                    f"{x:.12g} {y:.12g}\n"
                )


def write_layer_config(path):
    layers = (
        (0, "Y", 1.75e6, 0.01, SILICON_THICKNESS_M, "tier_0.flp"),
        (1, "N", 4e6, 0.25, TIM_THICKNESS_M, "tim.flp"),
        (2, "Y", 1.75e6, 0.01, SILICON_THICKNESS_M, "tier_1.flp"),
    )
    with path.open("w", newline="\n") as file:
        for layer, powered, specific_heat, resistivity, thickness, floorplan in layers:
            file.write(
                f"# Layer {layer}\n{layer}\nY\n{powered}\n"
                f"{specific_heat:g}\n{resistivity:g}\n{thickness:.12g}\n"
                f"{floorplan}\n\n"
            )


def write_power_trace(path, args):
    with path.open("w", newline="\n") as file:
        names = []
        powers = []
        for tier in (0, 1):
            layer = tier * 2
            for row in range(args.power_rows):
                for col in range(args.power_cols):
                    names.append(f"T{layer}_R{row}_C{col}")
                    is_hot = (
                        tier == args.hot_tier
                        and row == args.hot_row
                        and col == args.hot_col
                    )
                    if tier != args.hot_tier:
                        power = 0.0
                    else:
                        power = args.high_power if is_hot else args.low_power
                    powers.append(power)
        file.write(" ".join(names) + "\n")
        file.write(" ".join(f"{power:.12g}" for power in powers) + "\n")


def write_config(path, rows, cols):
    path.write_text(
        f"""-t_chip {SILICON_THICKNESS_M:.12g}
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
        encoding="ascii",
    )


def validate_args(args):
    if args.rows < 1 or args.cols < 1:
        raise ValueError("grid rows and columns must be positive")
    if not log2(args.rows).is_integer() or not log2(args.cols).is_integer():
        raise ValueError("HotSpot grid rows and columns must be powers of two")
    if args.power_rows < 1 or args.power_cols < 1:
        raise ValueError("power-map rows and columns must be positive")
    if not 0 <= args.hot_row < args.power_rows:
        raise ValueError("hot row must be within the power map")
    if not 0 <= args.hot_col < args.power_cols:
        raise ValueError("hot column must be within the power map")
    if not isfinite(args.low_power) or not isfinite(args.high_power):
        raise ValueError("power values must be finite")
    if args.low_power < 0 or args.high_power < 0:
        raise ValueError("power values must be non-negative")
    if args.high_power < args.low_power:
        raise ValueError("high power must be greater than or equal to low power")
    if args.output.exists() and not args.output.is_dir():
        raise FileExistsError(f"{args.output} exists and is not a directory")
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError(
            f"{args.output} is not empty; choose a new output directory "
            "to avoid overwriting existing files"
        )


def main():
    args = parse_args()
    validate_args(args)
    args.output.mkdir(parents=True, exist_ok=True)

    write_floorplan(args.output / "tier_0.flp", args.power_rows, args.power_cols, 0)
    write_floorplan(args.output / "tim.flp", args.power_rows, args.power_cols, 1)
    write_floorplan(args.output / "tier_1.flp", args.power_rows, args.power_cols, 2)
    write_layer_config(args.output / "stack.lcf")
    write_power_trace(args.output / "stack.ptrace", args)
    write_config(args.output / "stack.config", args.rows, args.cols)

    with (args.output / "metadata.txt").open("w", newline="\n") as file:
        file.write(
            "experiment=phase3d_two_tier_smoke_test\n"
            "stack_order=layer_0_tier_0,layer_1_tim,layer_2_tier_1\n"
            f"grid_rows={args.rows}\ngrid_cols={args.cols}\n"
            f"power_rows={args.power_rows}\npower_cols={args.power_cols}\n"
            f"width_m={WIDTH_M:.12g}\nheight_m={HEIGHT_M:.12g}\n"
            f"silicon_thickness_m={SILICON_THICKNESS_M:.12g}\n"
            f"tim_thickness_m={TIM_THICKNESS_M:.12g}\n"
            f"hot_tier={args.hot_tier}\nhot_row={args.hot_row}\n"
            f"hot_col={args.hot_col}\n"
            f"low_power_w={args.low_power:.12g}\n"
            f"high_power_w={args.high_power:.12g}\n"
            "inactive_tier_power_w=0\n"
            "power_units=watts_per_floorplan_tile\n"
        )

    print(f"Generated Phase 3D HotSpot inputs in {args.output}")


if __name__ == "__main__":
    main()
