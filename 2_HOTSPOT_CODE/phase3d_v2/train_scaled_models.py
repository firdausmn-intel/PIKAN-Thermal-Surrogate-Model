"""Train stacked-IC Fourier operators that scale exactly with total power.

    T = AMBIENT + P_total * g(P / P_total)

g is the same Fourier operator used in version 1 (MLP or KAN activation) and predicts
the temperature rise per watt from the power map normalised to its own total. Scaling
every input power by a constant therefore scales the rise by the same constant, which
the data-only and residual models had to learn from examples. The loss is the same
normalised data MSE as version 1 on the 3 chip layers; --residual-weight adds the
heat-balance residual (fixed spreader boundary), default 0.
"""

import argparse
from pathlib import Path

import torch
from torch.nn import functional as F

from train_residual_models import (
    AMBIENT_K,
    CELLS_PER_TILE,
    GRID,
    RESIDUAL_SCALE_W,
    build_model,
    fit_spreader_resistance,
    heat_balance_residual,
    load_split,
    temperature_stats,
    total_power,
    with_fixed_spreader,
)

SHAPE_SCALE = GRID * GRID  # cells per layer; makes the normalised shape average 1


def shape_input(tile_power):
    total = total_power(tile_power).reshape(-1, 1, 1, 1)
    return tile_power / CELLS_PER_TILE / total * SHAPE_SCALE, total


def predict_kelvin(model, tile_power, stats):
    """stats = (shape_mean, shape_std, rate_mean, rate_std); returns (B, 3, G, G) K."""
    shape, total = shape_input(tile_power)
    shape_mean, shape_std, rate_mean, rate_std = stats
    rate = model((shape - shape_mean) / shape_std) * rate_std + rate_mean
    return AMBIENT_K + total * rate


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
    parser.add_argument("--residual-weight", type=float, default=0.0)
    args = parser.parse_args()

    existing = [args.output / f"{name}.pt" for name in args.models]
    existing = [path for path in existing if path.exists()]
    if existing:
        raise FileExistsError(f"{existing[0]} already exists; use a new --output")
    args.output.mkdir(parents=True, exist_ok=True)

    train = load_split(args.dataset, "train")
    resistance = fit_spreader_resistance(train)
    chip = train["temperature"][:, :3]
    mean, std = temperature_stats(chip)
    target = (chip - mean) / std

    shape, total = shape_input(train["power"])
    shape_mean, shape_std = shape.mean(), shape.std()
    rate = (chip - AMBIENT_K) / total
    rate_mean, rate_std = temperature_stats(rate)
    stats = (shape_mean, shape_std, rate_mean, rate_std)

    for name in args.models:
        torch.manual_seed(args.seed)
        model = build_model(name, args.width, args.modes, 3)
        optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
        model.train()
        for epoch in range(1, args.epochs + 1):
            optimizer.zero_grad()
            kelvin = predict_kelvin(model, train["power"], stats)
            data_loss = F.mse_loss((kelvin - mean) / std, target)
            loss = data_loss
            residual_loss = torch.zeros(())
            if args.residual_weight > 0:
                full = with_fixed_spreader(kelvin, train["power"], resistance)
                residual = heat_balance_residual(full, train["power"])
                residual_loss = (residual / RESIDUAL_SCALE_W).square().mean()
                loss = data_loss + args.residual_weight * residual_loss
            loss.backward()
            optimizer.step()
            if epoch % 100 == 0 or epoch == args.epochs:
                print(f"{name} epoch {epoch}/{args.epochs} data={data_loss.item():.6f} "
                      f"residual={residual_loss.item():.6f}", flush=True)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "stats": [torch.as_tensor(s) for s in stats],
                "seed": args.seed,
                "epochs": args.epochs,
                "width": args.width,
                "modes": args.modes,
                "residual_weight": args.residual_weight,
                "spreader_resistance": resistance,
                "model_type": "power_scaled",
            },
            args.output / f"{name}.pt",
        )
        print(f"{name}: saved {args.output / (name + '.pt')}")


if __name__ == "__main__":
    main()
