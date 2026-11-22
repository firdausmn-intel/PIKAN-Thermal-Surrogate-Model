"""Convert Phase 3D HotSpot labels into volumetric training tensors.

Power has shape (cases, tiers, rows, cols) and temperature has shape
(cases, layers, rows, cols), where layers are the lower tier, TIM, and upper
tier (HotSpot layers 0-2). Package layers are excluded from the target.
"""

import argparse
import csv
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parent.parent
GRID_ROWS = 32
GRID_COLS = 32
POWER_ROWS = 4
POWER_COLS = 4
TIERS = 2
TARGET_LAYERS = (0, 1, 2)
LAYER_COUNT = 5


def read_layers(path):
    layers = {}
    layer_id = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            layer_id = int(line[len("Layer "):-1])
            if layer_id in layers:
                raise ValueError(f"{path}: duplicate layer {layer_id}")
            layers[layer_id] = []
            continue
        if layer_id is None:
            raise ValueError(f"{path}: temperature before a layer header")
        index, temperature = line.split()
        if int(index) != len(layers[layer_id]):
            raise ValueError(f"{path}: unexpected grid index in layer {layer_id}")
        layers[layer_id].append(float(temperature))

    if set(layers) != set(range(LAYER_COUNT)):
        raise ValueError(f"{path}: expected layers 0-4, found {sorted(layers)}")
    expected = GRID_ROWS * GRID_COLS
    for layer_id in TARGET_LAYERS:
        if len(layers[layer_id]) != expected:
            raise ValueError(
                f"{path}: layer {layer_id} has {len(layers[layer_id])} values; "
                f"expected {expected}"
            )
    return torch.tensor(
        [layers[layer_id] for layer_id in TARGET_LAYERS], dtype=torch.float32
    ).reshape(len(TARGET_LAYERS), GRID_ROWS, GRID_COLS)


def read_manifest(path):
    with path.open(newline="", encoding="utf-8") as stream:
        entries = list(csv.DictReader(stream, delimiter="\t"))
    if not entries:
        raise ValueError(f"Manifest has no cases: {path}")
    tiles = POWER_ROWS * POWER_COLS
    for entry in entries:
        entry["powers"] = []
        for key in ("tier0_powers_w", "tier1_powers_w"):
            powers = [float(value) for value in entry[key].split(",")]
            if len(powers) != tiles:
                raise ValueError(
                    f"{entry['case']}: expected {tiles} {key} values, "
                    f"found {len(powers)}"
                )
            entry["powers"].append(powers)
    return entries


def make_power_grid(tier_powers):
    tile_map = torch.tensor(tier_powers, dtype=torch.float32).reshape(
        POWER_ROWS, POWER_COLS
    )
    # HotSpot numbers grid rows from the top, opposite to floorplan y.
    tile_map = tile_map.flip(0)
    return tile_map.repeat_interleave(
        GRID_ROWS // POWER_ROWS, dim=0
    ).repeat_interleave(GRID_COLS // POWER_COLS, dim=1)


def build_split(dataset, entries, split):
    selected = [entry for entry in entries if entry["split"] == split]
    if not selected:
        raise ValueError(f"No {split} cases in the Phase 3D manifest")
    power = []
    temperature = []
    for entry in selected:
        label = dataset / "cases" / entry["case"] / "outputs" / "stack.grid.steady"
        power.append(
            torch.stack([make_power_grid(powers) for powers in entry["powers"]])
        )
        temperature.append(read_layers(label))
    return {
        "power": torch.stack(power),
        "temperature": torch.stack(temperature),
        "cases": [entry["case"] for entry in selected],
        "patterns": [entry["pattern"] for entry in selected],
        "rows": GRID_ROWS,
        "cols": GRID_COLS,
        "temperature_layers": list(TARGET_LAYERS),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "phase3d" / "dataset" / "stack_v1",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "test"],
        help="splits to convert (use 'test' for the test-only hard set)",
    )
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    entries = read_manifest(dataset / "manifest.tsv")
    for split in args.splits:
        output = dataset / f"{split}.pt"
        if output.exists():
            raise FileExistsError(f"{output} already exists")
    for split in args.splits:
        payload = build_split(dataset, entries, split)
        output = dataset / f"{split}.pt"
        torch.save(payload, output)
        print(
            f"{split}: cases={len(payload['cases'])} "
            f"power_shape={tuple(payload['power'].shape)} "
            f"temperature_shape={tuple(payload['temperature'].shape)} "
            f"output={output}"
        )


if __name__ == "__main__":
    main()
