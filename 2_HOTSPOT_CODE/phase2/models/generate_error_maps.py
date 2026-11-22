"""Generate held-out HotSpot/PINO/PIKAN comparison and error PNGs."""

import os
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent
PHASE1 = ROOT.parent.parent / "phase1"
sys.path.insert(0, str(PHASE1))

from visualize_phase1 import temperature_color, write_png
from train_operator_models import (
    KANActivation,
    MLPActivation,
    OperatorModel,
    TEMPERATURE_OFFSET,
    TEMPERATURE_SCALE,
    load_split,
)


CHECKPOINTS = Path(
    os.environ.get("PHASE2_CHECKPOINTS", ROOT / "checkpoints_v2")
)
OUTPUT = Path(
    os.environ.get(
        "PHASE2_ERROR_MAPS",
        ROOT.parent / "dataset" / "generated_v2" / "error_maps",
    )
)
SAMPLE_SIZE = 4


def denormalize(values):
    return values * TEMPERATURE_SCALE + TEMPERATURE_OFFSET


def render(values, output, minimum, maximum):
    height, width = values.shape
    pixels = bytearray()
    for row in reversed(values.tolist()):
        for value in row:
            pixels.extend(temperature_color(value, minimum, maximum))
    write_png(output, pixels, width, height)


def render_comparison(images, output, minimum, maximum):
    panel_names = list(images)
    panel_height, panel_width = images[panel_names[0]].shape
    columns = 2
    rows = (len(panel_names) + columns - 1) // columns
    gap = 4
    width = columns * panel_width + (columns - 1) * gap
    height = rows * panel_height + (rows - 1) * gap
    pixels = bytearray([255]) * (width * height * 3)
    for index, name in enumerate(panel_names):
        tile = bytearray()
        for row in reversed(images[name].tolist()):
            for value in row:
                tile.extend(temperature_color(value, minimum, maximum))
        tile_row, tile_col = divmod(index, columns)
        for row in range(panel_height):
            source = row * panel_width * 3
            image_row = tile_row * (panel_height + gap) + row
            image_col = tile_col * (panel_width + gap)
            target = (image_row * width + image_col) * 3
            pixels[target:target + panel_width * 3] = tile[
                source:source + panel_width * 3
            ]
    write_png(output, pixels, width, height)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    power, target, cases = load_split("test.pt", SAMPLE_SIZE)
    models = {}
    for name, activation in (("pino", MLPActivation), ("pikan", KANActivation)):
        model = OperatorModel(activation)
        model.load_state_dict(
            torch.load(
                CHECKPOINTS / f"{name}.pt",
                map_location="cpu",
                weights_only=True,
            )
        )
        model.eval()
        with torch.no_grad():
            models[name] = denormalize(model(power)).squeeze(1)
    target = denormalize(target).squeeze(1)

    for index, case_name in enumerate(cases):
        truth = target[index]
        pino = models["pino"][index]
        pikan = models["pikan"][index]
        pino_error = (pino - truth).abs()
        pikan_error = (pikan - truth).abs()
        case_dir = OUTPUT / case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        temperature_min = float(truth.min())
        temperature_max = float(truth.max())
        error_max = max(float(pino_error.max()), float(pikan_error.max()))
        render(truth, case_dir / "hotspot_ground_truth.png", temperature_min, temperature_max)
        render(pino, case_dir / "pino_prediction.png", temperature_min, temperature_max)
        render(pikan, case_dir / "pikan_prediction.png", temperature_min, temperature_max)
        render(pino_error, case_dir / "pino_absolute_error.png", 0.0, error_max)
        render(pikan_error, case_dir / "pikan_absolute_error.png", 0.0, error_max)
        render_comparison(
            {
                "hotspot": truth,
                "pino": pino,
                "pikan": pikan,
            },
            case_dir / "prediction_comparison.png",
            temperature_min,
            temperature_max,
        )
        render_comparison(
            {"pino_error": pino_error, "pikan_error": pikan_error},
            case_dir / "error_comparison.png",
            0.0,
            error_max,
        )
        print(f"{case_name}: wrote {case_dir}")


if __name__ == "__main__":
    main()
