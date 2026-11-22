"""Validate and summarize a HotSpot Phase 3D grid steady-state output."""

from argparse import ArgumentParser
from math import ceil, floor, isfinite
from pathlib import Path


LAYER_NAMES = {
    0: "lower silicon tier",
    1: "inter-tier TIM",
    2: "upper silicon tier",
    3: "heat spreader",
    4: "heat sink",
}


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--rows", type=int, default=32)
    parser.add_argument("--cols", type=int, default=32)
    parser.add_argument("--power-rows", type=int, default=4)
    parser.add_argument("--power-cols", type=int, default=4)
    parser.add_argument("--hot-tier", type=int, choices=(0, 1), default=0)
    parser.add_argument("--hot-row", type=int, default=1)
    parser.add_argument("--hot-col", type=int, default=1)
    return parser.parse_args()


def read_layers(path, expected_values):
    layers = {}
    layer_id = None
    values = []

    def finish_layer(current_id, current_values):
        if current_id is None:
            return
        if len(current_values) != expected_values:
            raise ValueError(
                f"Layer {current_id} has {len(current_values)} values; "
                f"expected {expected_values}"
            )
        layers[current_id] = current_values

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            finish_layer(layer_id, values)
            layer_id = int(line[len("Layer "):-1])
            if layer_id in layers:
                raise ValueError(f"Duplicate layer {layer_id}")
            values = []
            continue
        if layer_id is None:
            raise ValueError(
                f"Expected a 'Layer N:' header at line {line_number}"
            )
        fields = line.split()
        if len(fields) != 2:
            raise ValueError(f"Invalid grid value at line {line_number}")
        index = int(fields[0])
        expected_index = len(values)
        if index != expected_index:
            raise ValueError(
                f"Layer {layer_id} index {index} at line {line_number}; "
                f"expected {expected_index}"
            )
        temperature = float(fields[1])
        if not isfinite(temperature):
            raise ValueError(
                f"Non-finite temperature at line {line_number}"
            )
        values.append(temperature)

    finish_layer(layer_id, values)
    if set(layers) != set(LAYER_NAMES):
        raise ValueError(
            f"Expected stack layers {sorted(LAYER_NAMES)} "
            f"(including package); found {sorted(layers)}"
        )
    return layers


def hot_tile_grid_bounds(args):
    grid_row_start = args.rows - ceil(
        (args.hot_row + 1) * args.rows / args.power_rows
    )
    grid_row_end = args.rows - floor(
        args.hot_row * args.rows / args.power_rows
    )
    grid_col_start = floor(args.hot_col * args.cols / args.power_cols)
    grid_col_end = ceil((args.hot_col + 1) * args.cols / args.power_cols)
    return grid_row_start, grid_row_end, grid_col_start, grid_col_end


def main():
    args = parse_args()
    if args.rows < 1 or args.cols < 1:
        raise ValueError("grid rows and columns must be positive")
    if args.power_rows < 1 or args.power_cols < 1:
        raise ValueError("power-map rows and columns must be positive")
    if not 0 <= args.hot_row < args.power_rows:
        raise ValueError("hot row must be within the power map")
    if not 0 <= args.hot_col < args.power_cols:
        raise ValueError("hot column must be within the power map")
    layers = read_layers(args.input, args.rows * args.cols)
    print(f"Grid: {args.rows} rows x {args.cols} columns")
    for layer_id, values in layers.items():
        maximum_index = max(range(len(values)), key=values.__getitem__)
        max_row, max_col = divmod(maximum_index, args.cols)
        mean = sum(values) / len(values)
        print(
            f"Layer {layer_id} ({LAYER_NAMES[layer_id]}): "
            f"min={min(values):.2f} K, "
            f"max={max(values):.2f} K at row={max_row}, col={max_col}, "
            f"mean={mean:.2f} K"
        )
    source_layer = args.hot_tier * 2
    row_start, row_end, col_start, col_end = hot_tile_grid_bounds(args)
    source_values = layers[source_layer]
    source_peak = max(
        source_values[row * args.cols + col]
        for row in range(row_start, row_end)
        for col in range(col_start, col_end)
    )
    source_global_peak = max(source_values)
    print(
        f"Hot tile on tier {args.hot_tier} (layer {source_layer}, "
        f"power row={args.hot_row}, col={args.hot_col}) maps to grid "
        f"rows [{row_start}, {row_end}), columns [{col_start}, {col_end}); "
        f"peak in tile={source_peak:.2f} K, "
        f"global layer peak={source_global_peak:.2f} K"
    )
    if source_peak < source_global_peak:
        print("Hot tile check: FAIL (layer peak is outside the hot-tile region)")
    else:
        print("Hot tile check: PASS (hot-tile region contains a layer peak)")
    print(
        "Temperature span across all layers: "
        f"{min(min(values) for values in layers.values()):.2f}-"
        f"{max(max(values) for values in layers.values()):.2f} K"
    )


if __name__ == "__main__":
    main()
