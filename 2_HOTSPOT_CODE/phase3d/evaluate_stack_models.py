"""Evaluate Phase 3D models by held-out pattern and by layer."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

import torch

from stack_models import (
    LAYER_NAMES,
    MODELS,
    ROOT,
    case_metrics,
    load_split,
    normalize_power,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "phase3d" / "dataset" / "stack_v1"
    )
    parser.add_argument(
        "--test-dataset", type=Path, default=None,
        help="evaluate on this dataset's test split instead of --dataset's",
    )
    parser.add_argument(
        "--allow-missing", action="store_true",
        help="evaluate only the checkpoints that exist in --checkpoints",
    )
    parser.add_argument(
        "--checkpoints", type=Path, default=ROOT / "phase3d" / "checkpoints" / "stack_v1"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "phase3d" / "results" / "stack_v1"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    train = load_split(args.dataset, "train")
    test = load_split(args.test_dataset or args.dataset, "test")
    truth = test["temperature"]
    power = normalize_power(test["power"])

    predictions = {"train_mean": train["temperature"].mean(dim=0, keepdim=True).expand_as(truth)}
    for name in MODELS:
        checkpoint = args.checkpoints / f"{name}.pt"
        if not checkpoint.is_file():
            if args.allow_missing:
                continue
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model = MODELS[name](state.get("width", 16), state.get("modes", 12))
        model.load_state_dict(state["state_dict"])
        model.eval()
        with torch.no_grad():
            predictions[name] = (
                model(power) * state["temperature_std"] + state["temperature_mean"]
            )

    case_rows = []
    groups = defaultdict(list)
    for model_name, prediction in predictions.items():
        metrics = case_metrics(prediction, truth)
        for index, case in enumerate(test["cases"]):
            row = {
                "model": model_name,
                "case": case,
                "pattern": test["patterns"][index],
            }
            for key, values in metrics.items():
                row[key] = {
                    layer: float(values[index, i])
                    for i, layer in enumerate(LAYER_NAMES)
                }
            case_rows.append(row)
            groups[(model_name, row["pattern"])].append(row)

    summary = []
    print("model / pattern: MAE (K) per layer [lower, tim, upper]; peak error (K)")
    for (model_name, pattern), rows in sorted(groups.items()):
        item = {"model": model_name, "pattern": pattern, "cases": len(rows)}
        for key in ("mae_k", "rmse_k", "peak_error_k"):
            item[key] = {
                layer: sum(row[key][layer] for row in rows) / len(rows)
                for layer in LAYER_NAMES
            }
        summary.append(item)
        mae = [item["mae_k"][layer] for layer in LAYER_NAMES]
        peak = [item["peak_error_k"][layer] for layer in LAYER_NAMES]
        print(
            f"{model_name:10s} {pattern:19s} n={len(rows):2d} "
            f"mae=[{mae[0]:.3f}, {mae[1]:.3f}, {mae[2]:.3f}] "
            f"peak=[{peak[0]:.3f}, {peak[1]:.3f}, {peak[2]:.3f}]"
        )

    report = {
        "experiment": "two-tier single-hotspot training, dual and cross-tier held-out testing",
        "dataset": str(args.dataset),
        "checkpoints": str(args.checkpoints),
        "layers": list(LAYER_NAMES),
        "pattern_summary": summary,
        "case_metrics": case_rows,
    }
    path = args.output / "metrics.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Detailed metrics: {path}")


if __name__ == "__main__":
    main()
