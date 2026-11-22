"""Phase 3D v2 step 1: power-extrapolation datasets (reuses phase3d v1 tooling).

--part train: stack_v3 cases plus 40/50 mW training cases and the original test split.
--part test:  a test-only set at 60 mW, above every training power.
"""

import argparse
import csv
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase3d"))

from generate_stack_dataset import (  # noqa: E402
    POWER_COLS,
    POWER_ROWS,
    TIERS,
    build_cases,
    flatten,
    make_case,
    run_case,
)

HIGH_TRAIN_POWERS_W = (0.04, 0.05)
EXTRAPOLATION_POWER_W = 0.06
BACKGROUNDS_W = (0.004, 0.005, 0.006)
TILES = [(r, c) for r in range(POWER_ROWS) for c in range(POWER_COLS)]
SITES = [(t, tile) for t in range(TIERS) for tile in TILES]


def high_power_train_cases():
    rng = random.Random(3)
    cases = []
    for power in HIGH_TRAIN_POWERS_W:
        for tier, tile in SITES:
            cases.append(
                make_case(
                    f"train_hp_single_t{tier}_r{tile[0]}c{tile[1]}_{round(power * 1e3)}mW",
                    "train", "high_power_single", [(tier, tile)], power,
                )
            )
    for index in range(8):
        power = HIGH_TRAIN_POWERS_W[index % 2]
        tile = rng.choice(TILES)
        cases.append(
            make_case(
                f"train_hp_stacked_{index:02d}_{round(power * 1e3)}mW", "train",
                "high_power_stacked", [(0, tile), (1, tile)], power,
                BACKGROUNDS_W[index % 3],
            )
        )
    for index in range(12):
        power = HIGH_TRAIN_POWERS_W[index % 2]
        lower, upper = rng.sample(TILES, 2)
        cases.append(
            make_case(
                f"train_hp_offset_{index:02d}_{round(power * 1e3)}mW", "train",
                "high_power_offset", [(0, lower), (1, upper)], power,
                BACKGROUNDS_W[index % 3],
            )
        )
    for index in range(8):
        power = HIGH_TRAIN_POWERS_W[index % 2]
        cases.append(
            make_case(
                f"train_hp_many_{index:02d}_{round(power * 1e3)}mW", "train",
                "high_power_many", rng.sample(SITES, 3 + index % 2), power,
                BACKGROUNDS_W[index % 3],
            )
        )
    return cases


def extrapolation_test_cases():
    rng = random.Random(4)
    power = EXTRAPOLATION_POWER_W
    cases = []
    for index in range(8):
        tier, tile = rng.choice(SITES)
        cases.append(
            make_case(f"ext_single_{index:02d}", "test", "extrap_single",
                      [(tier, tile)], power)
        )
    for index in range(4):
        tile = rng.choice(TILES)
        cases.append(
            make_case(f"ext_stacked_{index:02d}", "test", "extrap_stacked",
                      [(0, tile), (1, tile)], power)
        )
    for index in range(4):
        lower, upper = rng.sample(TILES, 2)
        cases.append(
            make_case(f"ext_offset_{index:02d}", "test", "extrap_offset",
                      [(0, lower), (1, upper)], power)
        )
    for index in range(4):
        tier = index % TIERS
        tiles = rng.sample(TILES, 2)
        cases.append(
            make_case(f"ext_dual_{index:02d}", "test", "extrap_dual",
                      [(tier, tile) for tile in tiles], power)
        )
    for index in range(4):
        cases.append(
            make_case(f"ext_many_{index:02d}", "test", "extrap_many",
                      rng.sample(SITES, 3), power)
        )
    return cases


def exclude_held_out(cases):
    """Drop duplicate train cases and any that equal a stack_v2_hard test case."""
    from generate_stack_hard_test import build_cases as hard_cases

    def key(maps):
        return tuple(tuple(flatten(m)) for m in maps)

    blocked = {key(maps) for _, _, _, maps in hard_cases()}
    kept, seen = [], set()
    for case in cases:
        k = key(case[3])
        if case[1] == "train" and (k in blocked or k in seen):
            continue
        seen.add(k)
        kept.append(case)
    return kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("train", "test"), required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--inputs-only", action="store_true")
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    if (dataset / "manifest.tsv").exists() or (dataset / "cases").exists():
        raise FileExistsError(
            f"{dataset} already contains cases; choose a new dataset directory."
        )

    if args.part == "train":
        cases = exclude_held_out(build_cases(True, True) + high_power_train_cases())
    else:
        cases = extrapolation_test_cases()

    dataset.mkdir(parents=True, exist_ok=True)
    with (dataset / "manifest.tsv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(
            ["case", "split", "pattern", "tier0_powers_w", "tier1_powers_w",
             "total_power_w"]
        )
        for index, (name, split, pattern, maps) in enumerate(cases, 1):
            print(f"[{index}/{len(cases)}] Generating {name}", flush=True)
            run_case(name, maps, dataset, args.inputs_only)
            tiers = [flatten(m) for m in maps]
            writer.writerow(
                [name, split, pattern]
                + [",".join(f"{p:.12g}" for p in t) for t in tiers]
                + [f"{sum(sum(t) for t in tiers):.12g}"]
            )
            stream.flush()
    print(f"Dataset generated: {dataset}; cases: {len(cases)}")


if __name__ == "__main__":
    main()
