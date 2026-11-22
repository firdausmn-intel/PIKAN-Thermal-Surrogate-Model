"""Train Phase 3D stacked-IC models on HotSpot tensors (data loss only)."""

import argparse
from pathlib import Path

import torch
from torch.nn import functional as F

from stack_models import (
    MODELS,
    ROOT,
    case_metrics,
    load_split,
    normalize_power,
    temperature_stats,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "phase3d" / "dataset" / "stack_v1"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "phase3d" / "checkpoints" / "stack_v1"
    )
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--width", type=int, default=16, help="Fourier operator channels")
    parser.add_argument("--modes", type=int, default=12, help="retained Fourier modes (max 16)")
    args = parser.parse_args()

    existing = [args.output / f"{name}.pt" for name in args.models]
    existing = [path for path in existing if path.exists()]
    if existing:
        raise FileExistsError(
            f"{existing[0]} already exists; choose a new --output directory "
            "rather than overwriting a checkpoint."
        )
    args.output.mkdir(parents=True, exist_ok=True)

    train = load_split(args.dataset, "train")
    test = load_split(args.dataset, "test")
    mean, std = temperature_stats(train["temperature"])
    train_power = normalize_power(train["power"])
    train_target = (train["temperature"] - mean) / std
    test_power = normalize_power(test["power"])

    for name in args.models:
        torch.manual_seed(args.seed)
        model = MODELS[name](args.width, args.modes)
        parameters = sum(parameter.numel() for parameter in model.parameters())
        optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
        model.train()
        for epoch in range(1, args.epochs + 1):
            optimizer.zero_grad()
            loss = F.mse_loss(model(train_power), train_target)
            loss.backward()
            optimizer.step()
            if epoch % 100 == 0 or epoch == args.epochs:
                print(f"{name} epoch {epoch}/{args.epochs} loss={loss.item():.6f}", flush=True)

        model.eval()
        with torch.no_grad():
            prediction = model(test_power) * std + mean
        metrics = case_metrics(prediction, test["temperature"])
        torch.save(
            {
                "state_dict": model.state_dict(),
                "temperature_mean": mean,
                "temperature_std": std,
                "seed": args.seed,
                "epochs": args.epochs,
                "width": args.width,
                "modes": args.modes,
            },
            args.output / f"{name}.pt",
        )
        print(
            f"{name}: parameters={parameters} "
            f"test_mae_k={metrics['mae_k'].mean():.4f} "
            f"test_peak_error_k={metrics['peak_error_k'].mean():.4f}"
        )


if __name__ == "__main__":
    main()
