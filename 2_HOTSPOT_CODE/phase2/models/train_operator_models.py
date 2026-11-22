"""Train compact PINO and PIKAN operator baselines on HotSpot tensors."""

from argparse import ArgumentParser
import os
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F


ROOT = Path(__file__).resolve().parent.parent
DATASET = Path(
    os.environ.get("PHASE2_DATASET", ROOT / "dataset" / "generated")
)
POWER_SCALE = 5e-4
TEMPERATURE_OFFSET = 318.0
TEMPERATURE_SCALE = 10.0
DOMAIN_WIDTH_M = 11.04e-6
DOMAIN_HEIGHT_M = 3.2e-6
CELL_PITCH_X_M = 1.38e-6
CELL_PITCH_Y_M = 2.72e-6
FRONT_END_THICKNESS_M = 3e-7
FRONT_END_CONDUCTIVITY = 100.0
PHYSICS_RESIDUAL_SCALE = 1e8


class SpectralConv2d(nn.Module):
    def __init__(self, channels, modes_y, modes_x):
        super().__init__()
        self.channels = channels
        self.modes_y = modes_y
        self.modes_x = modes_x
        scale = 1 / (channels * channels)
        self.weight = nn.Parameter(
            scale * torch.randn(channels, channels, modes_y, modes_x, 2)
        )

    def forward(self, values):
        batch, _, height, width = values.shape
        transformed = torch.fft.rfft2(values, norm="ortho")
        output = torch.zeros_like(transformed)
        weights = torch.view_as_complex(self.weight)
        rows = min(self.modes_y, height)
        cols = min(self.modes_x, transformed.shape[-1])
        output[:, :, :rows, :cols] = torch.einsum(
            "bcyx,cdyx->bdyx",
            transformed[:, :, :rows, :cols],
            weights[:, :, :rows, :cols],
        )
        return torch.fft.irfft2(output, s=(height, width), norm="ortho")


class KANActivation(nn.Module):
    def __init__(self, channels, knots=8):
        super().__init__()
        self.knots = knots
        self.centers = nn.Parameter(torch.linspace(-1.0, 1.0, knots))
        self.coefficients = nn.Parameter(torch.zeros(channels, knots))
        self.linear = nn.Conv2d(channels, channels, 1)

    def forward(self, values):
        scaled = torch.tanh(values)
        distance = (scaled.unsqueeze(-1) - self.centers).abs()
        basis = F.relu(1.0 - distance * (self.knots - 1))
        nonlinear = torch.einsum("bhyxk,hk->bhyx", basis, self.coefficients)
        return self.linear(values) + nonlinear


class OperatorBlock(nn.Module):
    def __init__(self, channels, modes_y, modes_x, activation):
        super().__init__()
        self.spectral = SpectralConv2d(channels, modes_y, modes_x)
        self.pointwise = nn.Conv2d(channels, channels, 1)
        self.activation = activation(channels)

    def forward(self, values):
        return self.activation(self.spectral(values) + self.pointwise(values))


class OperatorModel(nn.Module):
    def __init__(self, activation, width=16, modes_y=12, modes_x=24):
        super().__init__()
        self.lift = nn.Conv2d(1, width, 1)
        self.blocks = nn.Sequential(
            OperatorBlock(width, modes_y, modes_x, activation),
            OperatorBlock(width, modes_y, modes_x, activation),
        )
        self.project = nn.Sequential(nn.Conv2d(width, width, 1), nn.GELU(), nn.Conv2d(width, 1, 1))

    def forward(self, values):
        return self.project(self.blocks(self.lift(values)))


class MLPActivation(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.network = nn.Sequential(nn.Conv2d(channels, channels, 1), nn.GELU())

    def forward(self, values):
        return self.network(values)


def load_split(filename, sample_size):
    payload = torch.load(DATASET / filename, map_location="cpu", weights_only=False)
    power = payload["power"]
    temperature = payload["temperature"]
    power = F.avg_pool2d(power, sample_size)
    temperature = F.avg_pool2d(temperature, sample_size)
    power = power / POWER_SCALE
    temperature = (temperature - TEMPERATURE_OFFSET) / TEMPERATURE_SCALE
    return power, temperature, payload["cases"]


def metrics(prediction, target):
    prediction = prediction * TEMPERATURE_SCALE + TEMPERATURE_OFFSET
    target = target * TEMPERATURE_SCALE + TEMPERATURE_OFFSET
    error = (prediction - target).abs()
    peak_error = (prediction.amax(dim=(-2, -1)) - target.amax(dim=(-2, -1))).abs()
    return float(error.mean()), float(peak_error.mean())


def heat_equation_residual(prediction, power):
    temperature = prediction * TEMPERATURE_SCALE + TEMPERATURE_OFFSET
    physical_power = power * POWER_SCALE
    power_density = physical_power / (CELL_PITCH_X_M * CELL_PITCH_Y_M)
    _, _, height, width = temperature.shape
    dx = DOMAIN_WIDTH_M / width
    dy = DOMAIN_HEIGHT_M / height
    center = temperature[:, :, 1:-1, 1:-1]
    d2x = (temperature[:, :, 1:-1, 2:] - 2 * center + temperature[:, :, 1:-1, :-2]) / (dx * dx)
    d2y = (temperature[:, :, 2:, 1:-1] - 2 * center + temperature[:, :, :-2, 1:-1]) / (dy * dy)
    conduction = FRONT_END_CONDUCTIVITY * FRONT_END_THICKNESS_M * (d2x + d2y)
    source = power_density[:, :, 1:-1, 1:-1]
    return (conduction + source) / PHYSICS_RESIDUAL_SCALE


def train_model(model, power, target, epochs, learning_rate, physics_weight):
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    for epoch in range(epochs):
        optimizer.zero_grad()
        prediction = model(power)
        loss = F.mse_loss(prediction, target)
        residual = heat_equation_residual(prediction, power)
        loss = loss + physics_weight * residual.square().mean()
        loss.backward()
        optimizer.step()
    return model


def main():
    parser = ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--sample-size", type=int, default=4)
    parser.add_argument("--physics-weight", type=float, default=0.01)
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "checkpoints")
    args = parser.parse_args()
    torch.manual_seed(7)
    args.output.mkdir(parents=True, exist_ok=True)
    train_power, train_temperature, train_cases = load_split("train.pt", args.sample_size)
    test_power, test_temperature, test_cases = load_split("test.pt", args.sample_size)
    models = {
        "pino": OperatorModel(MLPActivation),
        "pikan": OperatorModel(KANActivation),
    }
    for name, model in models.items():
        train_model(
            model,
            train_power,
            train_temperature,
            args.epochs,
            1e-3,
            args.physics_weight,
        )
        model.eval()
        with torch.no_grad():
            prediction = model(test_power)
        mae, peak_error = metrics(prediction, test_temperature)
        torch.save(model.state_dict(), args.output / f"{name}.pt")
        print(f"{name}: test_cases={test_cases} mae_k={mae:.6f} peak_error_k={peak_error:.6f}")


if __name__ == "__main__":
    main()
