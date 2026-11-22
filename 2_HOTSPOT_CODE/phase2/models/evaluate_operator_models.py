"""Evaluate saved PINO and PIKAN checkpoints on the held-out split."""

from pathlib import Path
import os

import torch
from torch.nn import functional as F

from train_operator_models import (
    DATASET,
    OperatorModel,
    MLPActivation,
    KANActivation,
    load_split,
    metrics,
)


ROOT = Path(__file__).resolve().parent
CHECKPOINTS = Path(
    os.environ.get("PHASE2_CHECKPOINTS", ROOT / "checkpoints")
)


def main():
    power, target, cases = load_split("test.pt", sample_size=4)
    for name, activation in (("pino", MLPActivation), ("pikan", KANActivation)):
        model = OperatorModel(activation)
        model.load_state_dict(
            torch.load(CHECKPOINTS / f"{name}.pt", map_location="cpu", weights_only=True)
        )
        model.eval()
        with torch.no_grad():
            prediction = model(power)
        mae, peak_error = metrics(prediction, target)
        print(f"{name}: cases={cases} mae_k={mae:.6f} peak_error_k={peak_error:.6f}")


if __name__ == "__main__":
    main()
