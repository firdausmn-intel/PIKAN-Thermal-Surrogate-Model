"""Evaluate residual-loss models: per-pattern MAE/peak error plus heat-balance residual."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import torch

from train_residual_models import (
    build_model,
    heat_balance_residual,
    load_split,
    normalize_power,
    pst,
    with_fixed_spreader,
)

NAMES = ("lower", "tim", "upper")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-dataset", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--models", nargs="+", default=["fno_mlp", "fno_kan"])
    args = parser.parse_args()
    if (args.output / "metrics.json").exists():
        raise FileExistsError(f"{args.output / 'metrics.json'} already exists")

    test = load_split(args.test_dataset, "test")
    truth = test["temperature"]
    power = normalize_power(test["power"])
    true_residual = heat_balance_residual(truth, test["power"]).square().mean().sqrt()

    rows = []
    for name in args.models:
        state = torch.load(args.checkpoints / f"{name}.pt", map_location="cpu",
                           weights_only=True)
        fixed = state.get("boundary", "predicted") == "fixed"
        model = build_model(name, state["width"], state["modes"], 3 if fixed else 4)
        model.load_state_dict(state["state_dict"])
        model.eval()
        with torch.no_grad():
            prediction = model(power) * state["temperature_std"] + state["temperature_mean"]
            if fixed:
                prediction = with_fixed_spreader(
                    prediction, test["power"], state["spreader_resistance"]
                )
            residual = heat_balance_residual(prediction, test["power"])
        error = prediction[:, :3] - truth[:, :3]
        mae = error.abs().mean(dim=(-2, -1))
        peak = (prediction[:, :3].amax(dim=(-2, -1)) - truth[:, :3].amax(dim=(-2, -1))).abs()
        res_rms = residual.square().mean(dim=(1, 2, 3)).sqrt()
        for i, pattern in enumerate(test["patterns"]):
            rows.append((name, pattern, mae[i], peak[i], res_rms[i]))

    groups = defaultdict(list)
    for row in rows:
        groups[(row[0], row[1])].append(row)
    print(f"HotSpot label block residual RMS: {true_residual:.2e} W")
    print("model / pattern: MAE (K) [lower, tim, upper]; peak error (K); block residual RMS (W)")
    summary = []
    for (name, pattern), items in sorted(groups.items()):
        mae = torch.stack([r[2] for r in items]).mean(dim=0)
        peak = torch.stack([r[3] for r in items]).mean(dim=0)
        res = torch.stack([r[4] for r in items]).mean()
        print(f"{name:8s} {pattern:19s} n={len(items):2d} "
              f"mae=[{mae[0]:.3f}, {mae[1]:.3f}, {mae[2]:.3f}] "
              f"peak=[{peak[0]:.3f}, {peak[1]:.3f}, {peak[2]:.3f}] res={res:.2e}")
        summary.append({"model": name, "pattern": pattern, "cases": len(items),
                        "mae_k": dict(zip(NAMES, map(float, mae))),
                        "peak_error_k": dict(zip(NAMES, map(float, peak))),
                        "block_residual_rms_w": float(res)})
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "metrics.json"
    path.write_text(json.dumps({"checkpoints": str(args.checkpoints),
                                "pattern_summary": summary}, indent=2), encoding="utf-8")
    print(f"Detailed metrics: {path}")


if __name__ == "__main__":
    main()
