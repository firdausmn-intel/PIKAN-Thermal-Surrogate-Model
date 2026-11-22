"""Convert HotSpot text outputs into PyTorch tensors for Phase 2 training."""

from pathlib import Path
import sys
import os

import torch


ROOT = Path(__file__).resolve().parent
DATASET = Path(os.environ.get("PHASE2_DATASET", ROOT / "generated"))
ROWS = 256
COLS = 1024
CELLS = 8


def read_layer_zero(path):
    values = []
    active = False
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            active = line == "Layer 0:"
            if values:
                break
            continue
        if active:
            values.append(float(line.split()[1]))
    expected = ROWS * COLS
    if len(values) != expected:
        raise ValueError(f"{path}: expected {expected}, found {len(values)}")
    return torch.tensor(values, dtype=torch.float32).reshape(1, ROWS, COLS)


def read_manifest(path):
    entries = []
    lines = path.read_text().splitlines()
    for line in lines[1:]:
        if not line.strip():
            continue
        case, split, hot_start, hot_cells, low_power, high_power = line.split("\t")
        entries.append(
            {
                "case": case,
                "split": split,
                "hot_start": int(hot_start),
                "hot_cells": int(hot_cells),
                "low_power": float(low_power),
                "high_power": float(high_power),
            }
        )
    return entries


def make_power_grid(entry):
    values = []
    cell_width = COLS // CELLS
    for column in range(COLS):
        cell = min(CELLS - 1, column // cell_width)
        value = entry["high_power"] if entry["hot_start"] <= cell < entry["hot_start"] + entry["hot_cells"] else entry["low_power"]
        values.append(value)
    row = torch.tensor(values, dtype=torch.float32)
    return row.repeat(ROWS).reshape(1, ROWS, COLS)


def build_split(entries, split):
    powers = []
    temperatures = []
    case_names = []
    for entry in entries:
        if entry["split"] != split:
            continue
        case_dir = DATASET / "cases" / entry["case"]
        powers.append(make_power_grid(entry))
        temperatures.append(read_layer_zero(case_dir / "outputs/block.grid.steady"))
        case_names.append(entry["case"])
    if not powers:
        raise ValueError(f"No {split} cases found in manifest")
    return {
        "power": torch.stack(powers),
        "temperature": torch.stack(temperatures),
        "cases": case_names,
        "rows": ROWS,
        "cols": COLS,
    }


def main():
    entries = read_manifest(DATASET / "manifest.tsv")
    for split in ("train", "test"):
        payload = build_split(entries, split)
        output = DATASET / f"{split}.pt"
        torch.save(payload, output)
        print(
            f"{split}: cases={len(payload['cases'])} "
            f"power_shape={tuple(payload['power'].shape)} "
            f"temperature_shape={tuple(payload['temperature'].shape)} "
            f"output={output}"
        )


if __name__ == "__main__":
    main()
