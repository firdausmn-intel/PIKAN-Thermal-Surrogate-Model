"""Aggregate fno_mlp vs fno_kan over seeds: mean/std, win count, paired sign-flip test."""
import argparse
import csv
import itertools
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETS = {"orig": "in-range", "hard": "hard", "ext": "60 mW extrapolation"}
METRICS = ["mae_k", "peak_error_k"]


def load(seed, key):
    path = ROOT / "phase3d_v2" / "results" / f"power_{key}_seed{seed}" / "metrics.json"
    return json.loads(path.read_text())["pattern_summary"]


def tier_value(entry, metric):
    values = entry[metric]
    return values.get("lower_tier", values.get("lower"))


def per_seed(rows):
    # case-weighted mean over patterns, per model
    out = {}
    for model in ("fno_mlp", "fno_kan"):
        sel = [r for r in rows if r["model"] == model]
        n = sum(r["cases"] for r in sel)
        out[model] = {
            m: sum(tier_value(r, m) * r["cases"] for r in sel) / n for m in METRICS
        }
    return out


def sign_flip_p(diffs):
    # exact two-sided paired permutation test on the mean difference
    obs = abs(sum(diffs))
    count = total = 0
    for signs in itertools.product((1, -1), repeat=len(diffs)):
        total += 1
        if abs(sum(s * d for s, d in zip(signs, diffs))) >= obs - 1e-15:
            count += 1
    return count / total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 23, 31, 41, 53, 67, 79])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"{args.output} already exists")
    args.output.mkdir(parents=True)

    summary, patterns = [], []
    for key, label in SETS.items():
        data = {s: load(s, key) for s in args.seeds}
        agg = {s: per_seed(rows) for s, rows in data.items()}
        for metric in METRICS:
            mlp = [agg[s]["fno_mlp"][metric] for s in args.seeds]
            kan = [agg[s]["fno_kan"][metric] for s in args.seeds]
            diffs = [a - b for a, b in zip(mlp, kan)]  # >0 means KAN lower (better)
            summary.append({
                "test_set": label, "metric": metric, "seeds": len(args.seeds),
                "mlp_mean": st.mean(mlp), "mlp_std": st.stdev(mlp),
                "kan_mean": st.mean(kan), "kan_std": st.stdev(kan),
                "kan_wins": sum(d > 0 for d in diffs),
                "mean_diff_mlp_minus_kan": st.mean(diffs),
                "paired_p": sign_flip_p(diffs),
            })
        pats = sorted({r["pattern"] for r in data[args.seeds[0]]})
        for pat in pats:
            for metric in METRICS:
                vals = {"fno_mlp": [], "fno_kan": []}
                for s in args.seeds:
                    for r in data[s]:
                        if r["pattern"] == pat and r["model"] in vals:
                            vals[r["model"]].append(tier_value(r, metric))
                diffs = [a - b for a, b in zip(vals["fno_mlp"], vals["fno_kan"])]
                patterns.append({
                    "test_set": label, "pattern": pat, "metric": metric,
                    "mlp_mean": st.mean(vals["fno_mlp"]), "mlp_std": st.stdev(vals["fno_mlp"]),
                    "kan_mean": st.mean(vals["fno_kan"]), "kan_std": st.stdev(vals["fno_kan"]),
                    "kan_wins": sum(d > 0 for d in diffs), "seeds": len(diffs),
                    "paired_p": sign_flip_p(diffs),
                })

    for name, rows in (("seed_summary.csv", summary), ("seed_patterns.csv", patterns)):
        with open(args.output / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    print("Lower-tier, mean +- std over seeds (K); wins = seeds where KAN is lower")
    for r in summary:
        print(f"{r['test_set']:22s} {r['metric']:13s} MLP {r['mlp_mean']:.4f}+-{r['mlp_std']:.4f} "
              f"KAN {r['kan_mean']:.4f}+-{r['kan_std']:.4f} KANwins {r['kan_wins']}/{r['seeds']} "
              f"p={r['paired_p']:.3f}")
    print("\nPer-pattern (KAN wins / p<0.05 only shown if p<=0.1):")
    for r in patterns:
        if r["paired_p"] <= 0.1:
            print(f"{r['test_set']:22s} {r['pattern']:20s} {r['metric']:13s} "
                  f"MLP {r['mlp_mean']:.3f} KAN {r['kan_mean']:.3f} wins {r['kan_wins']}/{r['seeds']} p={r['paired_p']:.3f}")


if __name__ == "__main__":
    main()
