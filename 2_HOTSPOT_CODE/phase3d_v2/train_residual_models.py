"""Train stacked-IC Fourier operators with a 3D heat-balance residual loss.

The model predicts four layers (lower tier, TIM, upper tier, spreader). The loss is
    data MSE (normalized, all 4 layers) + lambda * residual MSE
where the residual is HotSpot's steady-state heat balance on layers 0-2, evaluated
on the de-normalized prediction and summed over blocks (see check_heat_balance.py for
the verified resistor rules). --residual-weight 0 gives a data-only 4-layer control.
Tensors are built in memory from the label files; nothing is written except the
checkpoints.
"""

import argparse
from pathlib import Path
import sys

import torch
from torch import nn
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase3d"))
import prepare_stack_tensors as pst  # noqa: E402
from stack_models import MODELS, normalize_power  # noqa: E402

pst.TARGET_LAYERS = (0, 1, 2, 3)

GRID = 32
CELL = 1e-3 / GRID
AREA = CELL * CELL
# thickness (m), conductivity (W/mK): lower tier, TIM, upper tier, spreader.
LAYERS = [(1.5e-4, 100.0), (5e-5, 4.0), (1.5e-4, 100.0), (1e-3, 400.0)]
G_LATERAL = [k * t for t, k in LAYERS[:3]]
# HotSpot's vertical conductance between layers n and n+1 uses layer n only.
G_VERTICAL = [k * AREA / t for t, k in LAYERS[:3]]
CELLS_PER_TILE = (GRID // pst.POWER_ROWS) ** 2
RESIDUAL_SCALE_W = 5e-3  # block power scale for an 8x8 block


def load_split(dataset, split):
    entries = pst.read_manifest(Path(dataset) / "manifest.tsv")
    return pst.build_split(Path(dataset), entries, split)


def heat_balance_residual(temp, power, block=8):
    """temp: (B, 4, 32, 32) K; power: (B, 2, 32, 32) tile W. Returns (B, 3, G/b, G/b) W."""
    cell_power = power / CELLS_PER_TILE
    zero = torch.zeros_like(cell_power[:, :1])
    cell_power = torch.cat([cell_power[:, :1], zero, cell_power[:, 1:]], dim=1)
    outputs = []
    for n in range(3):
        layer = temp[:, n]
        res = cell_power[:, n].clone()
        d_row = layer[:, 1:] - layer[:, :-1]
        d_col = layer[:, :, 1:] - layer[:, :, :-1]
        res = res + F.pad(G_LATERAL[n] * d_row, (0, 0, 0, 1))
        res = res - F.pad(G_LATERAL[n] * d_row, (0, 0, 1, 0))
        res = res + F.pad(G_LATERAL[n] * d_col, (0, 1, 0, 0))
        res = res - F.pad(G_LATERAL[n] * d_col, (1, 0, 0, 0))
        res = res + G_VERTICAL[n] * (temp[:, n + 1] - layer)
        if n > 0:
            res = res + G_VERTICAL[n - 1] * (temp[:, n - 1] - layer)
        outputs.append(res)
    res = torch.stack(outputs, dim=1)
    return F.avg_pool2d(res, block) * block * block


def temperature_stats(temperature):
    mean = temperature.mean(dim=(0, 2, 3)).reshape(1, -1, 1, 1)
    std = temperature.std(dim=(0, 2, 3)).reshape(1, -1, 1, 1)
    return mean, std


AMBIENT_K = 318.15


def build_model(name, width, modes, outputs=4):
    model = MODELS[name](width, modes)
    model.project[-1] = nn.Conv2d(width, outputs, 1)
    return model


def total_power(tile_power):
    return tile_power.sum(dim=(1, 2, 3)) / CELLS_PER_TILE


def fit_spreader_resistance(train):
    """Slope (K/W) of spreader temperature rise over ambient vs total chip power."""
    rise = train["temperature"][:, 3].mean(dim=(1, 2)) - AMBIENT_K
    p = total_power(train["power"])
    return float((p * rise).sum() / p.square().sum())


def with_fixed_spreader(prediction, tile_power, resistance):
    """Append a uniform spreader layer at ambient + resistance * total power."""
    spreader = AMBIENT_K + resistance * total_power(tile_power)
    plane = spreader.reshape(-1, 1, 1, 1).expand(-1, 1, GRID, GRID)
    return torch.cat([prediction, plane], dim=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="+", choices=["fno_mlp", "fno_kan"],
                        default=["fno_mlp", "fno_kan"])
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--width", type=int, default=16)
    parser.add_argument("--modes", type=int, default=12)
    parser.add_argument("--residual-weight", type=float, default=1.0)
    parser.add_argument("--block", type=int, default=8, choices=[1, 2, 4, 8, 16])
    parser.add_argument(
        "--boundary", choices=["predicted", "fixed"], default="predicted",
        help="fixed: model predicts 3 chip layers; spreader is ambient + R * total power",
    )
    args = parser.parse_args()
    fixed = args.boundary == "fixed"

    existing = [args.output / f"{name}.pt" for name in args.models]
    existing = [path for path in existing if path.exists()]
    if existing:
        raise FileExistsError(f"{existing[0]} already exists; use a new --output")
    args.output.mkdir(parents=True, exist_ok=True)

    train = load_split(args.dataset, "train")
    resistance = fit_spreader_resistance(train) if fixed else None
    if fixed:
        print(f"spreader resistance fitted on training data: {resistance:.4f} K/W")
        train["temperature"] = train["temperature"][:, :3]
    mean, std = temperature_stats(train["temperature"])
    power = normalize_power(train["power"])
    target = (train["temperature"] - mean) / std
    scale = RESIDUAL_SCALE_W * (args.block / 8) ** 2

    for name in args.models:
        torch.manual_seed(args.seed)
        model = build_model(name, args.width, args.modes, 3 if fixed else 4)
        optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
        model.train()
        for epoch in range(1, args.epochs + 1):
            optimizer.zero_grad()
            output = model(power)
            data_loss = F.mse_loss(output, target)
            temperature = output * std + mean
            if fixed:
                temperature = with_fixed_spreader(
                    temperature, train["power"], resistance
                )
            residual = heat_balance_residual(temperature, train["power"], args.block)
            residual_loss = (residual / scale).square().mean()
            loss = data_loss + args.residual_weight * residual_loss
            loss.backward()
            optimizer.step()
            if epoch % 100 == 0 or epoch == args.epochs:
                print(f"{name} epoch {epoch}/{args.epochs} data={data_loss.item():.6f} "
                      f"residual={residual_loss.item():.6f}", flush=True)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "temperature_mean": mean,
                "temperature_std": std,
                "seed": args.seed,
                "epochs": args.epochs,
                "width": args.width,
                "modes": args.modes,
                "residual_weight": args.residual_weight,
                "block": args.block,
                "boundary": args.boundary,
                "spreader_resistance": resistance,
            },
            args.output / f"{name}.pt",
        )
        print(f"{name}: saved {args.output / (name + '.pt')}")


if __name__ == "__main__":
    main()
