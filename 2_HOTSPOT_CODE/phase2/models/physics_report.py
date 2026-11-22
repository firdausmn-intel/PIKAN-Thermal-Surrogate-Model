"""Report reduced heat-equation residuals for labels and model predictions."""

from pathlib import Path
import os

import torch

from train_operator_models import (
    DATASET,
    KANActivation,
    MLPActivation,
    OperatorModel,
    heat_equation_residual,
    load_split,
    metrics,
)

ROOT = Path(__file__).resolve().parent
CHECKPOINTS = Path(
    os.environ.get("PHASE2_CHECKPOINTS", ROOT / "checkpoints")
)


def residual_summary(values):
    residual = heat_equation_residual(values[0], values[1])
    return float(residual.abs().mean()), float(residual.square().mean().sqrt())


def main():
    power, target, cases = load_split("test.pt", sample_size=4)
    target_residual = heat_equation_residual(target, power)
    print(
        f"hotspot_ground_truth: cases={cases} "
        f"mean_abs={target_residual.abs().mean():.6f} "
        f"rms={target_residual.square().mean().sqrt():.6f}"
    )
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
            prediction = model(power)
        mean_abs, rms = residual_summary((prediction, power))
        mae, peak_error = metrics(prediction, target)
        print(
            f"{name}: mae_k={mae:.6f} peak_error_k={peak_error:.6f} "
            f"residual_mean_abs={mean_abs:.6f} residual_rms={rms:.6f}"
        )


if __name__ == "__main__":
    main()
