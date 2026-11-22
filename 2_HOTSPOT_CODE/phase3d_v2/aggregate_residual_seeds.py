"""Seed comparison of residual (PINO/PIKAN-style) vs data-only, and MLP vs KAN with residual."""
import argparse
import csv
import itertools
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETS = {"orig": "in-range", "hard": "hard", "ext": "60 mW extrapolation"}
METRICS = ["mae_k", "peak_error_k"]
SOURCES = {"data": "power", "resid": "fixed_w1"}


def tier(entry, metric):
    v = entry[metric]
    return v.get("lower_tier", v.get("lower"))


def per_seed(seed, source, key, pattern=None):
    path = ROOT / "phase3d_v2" / "results" / f"{SOURCES[source]}_{key}_seed{seed}" / "metrics.json"
    rows = json.loads(path.read_text())["pattern_summary"]
    out = {}
    for model in ("fno_mlp", "fno_kan"):
        sel = [r for r in rows if r["model"] == model and (pattern is None or r["pattern"] == pattern)]
        n = sum(r["cases"] for r in sel)
        out[model] = {m: sum(tier(r, m) * r["cases"] for r in sel) / n for m in METRICS}
    return out


def patterns_of(seed, source, key):
    path = ROOT / "phase3d_v2" / "results" / f"{SOURCES[source]}_{key}_seed{seed}" / "metrics.json"
    return sorted({r["pattern"] for r in json.loads(path.read_text())["pattern_summary"]})


def p_value(diffs):
    obs = abs(sum(diffs))
    hits = sum(
        abs(sum(s * d for s, d in zip(signs, diffs))) >= obs - 1e-15
        for signs in itertools.product((1, -1), repeat=len(diffs))
    )
    return hits / 2 ** len(diffs)


def compare(label_a, a, label_b, b):
    # difference a - b; positive means b has the lower error
    diffs = [x - y for x, y in zip(a, b)]
    return {
        f"{label_a}_mean": st.mean(a), f"{label_a}_std": st.stdev(a),
        f"{label_b}_mean": st.mean(b), f"{label_b}_std": st.stdev(b),
        f"{label_b}_wins": sum(d > 0 for d in diffs), "seeds": len(diffs),
        "mean_diff": st.mean(diffs), "paired_p": p_value(diffs),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 11, 23, 31, 41, 53, 67, 79])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"{args.output} already exists")
    args.output.mkdir(parents=True)

    rows = []
    for key, set_label in SETS.items():
        scopes = [(None, "all")] + [(p, p) for p in patterns_of(args.seeds[0], "resid", key)]
        for pattern, scope in scopes:
            data = {(s, src): per_seed(s, src, key, pattern) for s in args.seeds for src in SOURCES}
            for metric in METRICS:
                def series(src, model):
                    return [data[(s, src)][model][metric] for s in args.seeds]
                comparisons = {
                    "PINO_vs_PIKAN": compare("PINO", series("resid", "fno_mlp"), "PIKAN", series("resid", "fno_kan")),
                    "mlp_resid_vs_data": compare("data", series("data", "fno_mlp"), "resid", series("resid", "fno_mlp")),
                    "kan_resid_vs_data": compare("data", series("data", "fno_kan"), "resid", series("resid", "fno_kan")),
                }
                for name, r in comparisons.items():
                    rows.append({"test_set": set_label, "scope": scope, "metric": metric,
                                 "comparison": name, **r})

    keys = ["test_set", "scope", "metric", "comparison", "seeds", "mean_diff", "paired_p"]
    fields = keys + sorted({k for r in rows for k in r} - set(keys))
    with open(args.output / "residual_seed_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print("Lower tier, 8 seeds. 'wins' = seeds where the second-named model has lower error.\n")
    for r in rows:
        if r["scope"] != "all":
            continue
        first, second = {"PINO_vs_PIKAN": ("PINO", "PIKAN")}.get(r["comparison"], ("data", "resid"))
        print(f"{r['test_set']:20s} {r['metric']:13s} {r['comparison']:18s} "
              f"{first} {r[first + '_mean']:.4f}+-{r[first + '_std']:.4f} "
              f"{second} {r[second + '_mean']:.4f}+-{r[second + '_std']:.4f} "
              f"{second}wins {r[second + '_wins']}/{r['seeds']} p={r['paired_p']:.3f}")


if __name__ == "__main__":
    main()
