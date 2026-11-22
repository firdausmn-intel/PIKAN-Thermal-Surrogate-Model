"""Models and data helpers for the Phase 3D two-tier thermal experiment.

Inputs are per-tier power maps with shape (batch, 2, rows, cols). Targets are
temperature maps for the lower tier, TIM, and upper tier with shape
(batch, 3, rows, cols). Only data loss is used; no physics residual.
"""

from pathlib import Path
import sys

import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase2" / "models"))

from train_operator_models import (  # noqa: E402
    KANActivation,
    MLPActivation,
    OperatorBlock,
)

POWER_OFFSET_W = 0.005
POWER_SCALE_W = 0.025
LAYER_NAMES = ("lower_tier", "tim", "upper_tier")


class StackOperator(nn.Module):
    """Fourier operator mapping 2 tier power maps to 3 layer temperature maps."""

    def __init__(self, activation, width=16, modes=12):
        super().__init__()
        self.lift = nn.Conv2d(2, width, 1)
        self.blocks = nn.Sequential(
            OperatorBlock(width, modes, modes, activation),
            OperatorBlock(width, modes, modes, activation),
        )
        self.project = nn.Sequential(
            nn.Conv2d(width, width, 1), nn.GELU(), nn.Conv2d(width, 3, 1)
        )

    def forward(self, power):
        return self.project(self.blocks(self.lift(power)))


class Stack3DCNN(nn.Module):
    """Dilated 3D convolution baseline over the (lower, TIM, upper) depth axis."""

    def __init__(self, width=8, dilations=(1, 2, 4, 8)):
        super().__init__()
        layers = []
        in_channels = 1
        for dilation in dilations:
            layers += [
                nn.Conv3d(
                    in_channels, width, kernel_size=3,
                    padding=(1, dilation, dilation),
                    dilation=(1, dilation, dilation),
                ),
                nn.GELU(),
            ]
            in_channels = width
        layers.append(nn.Conv3d(width, 1, kernel_size=1))
        self.network = nn.Sequential(*layers)

    def forward(self, power):
        # The TIM layer dissipates no power, so it is a zero slice between tiers.
        volume = torch.stack(
            [power[:, 0], torch.zeros_like(power[:, 0]), power[:, 1]], dim=1
        ).unsqueeze(1)
        return self.network(volume).squeeze(1)


MODELS = {
    "fno_mlp": lambda width=16, modes=12: StackOperator(MLPActivation, width, modes),
    "fno_kan": lambda width=16, modes=12: StackOperator(KANActivation, width, modes),
    "cnn3d": lambda width=16, modes=12: Stack3DCNN(),
}


def load_split(dataset, split):
    payload = torch.load(
        Path(dataset) / f"{split}.pt", map_location="cpu", weights_only=False
    )
    return payload


def normalize_power(power):
    return (power - POWER_OFFSET_W) / POWER_SCALE_W


def temperature_stats(temperature):
    mean = temperature.mean(dim=(0, 2, 3)).reshape(1, 3, 1, 1)
    std = temperature.std(dim=(0, 2, 3)).reshape(1, 3, 1, 1)
    return mean, std


def case_metrics(prediction_k, truth_k):
    """Per-case, per-layer MAE, RMSE, and peak error in kelvin."""
    error = prediction_k - truth_k
    return {
        "mae_k": error.abs().mean(dim=(-2, -1)),
        "rmse_k": error.square().mean(dim=(-2, -1)).sqrt(),
        "peak_error_k": (
            prediction_k.amax(dim=(-2, -1)) - truth_k.amax(dim=(-2, -1))
        ).abs(),
    }
