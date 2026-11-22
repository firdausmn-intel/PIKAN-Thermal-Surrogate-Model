"""Generate a test-only Phase 3D set that stresses generalization beyond stack_v2."""

import argparse
import csv
from pathlib import Path
import random

from generate_stack_dataset import (
    POWER_COLS,
    POWER_ROWS,
    ROOT,
    TIERS,
    flatten,
    run_case,
)


BACKGROUND_W = 0.005
ALL_TILES = [(r, c) for r in range(POWER_ROWS) for c in range(POWER_COLS)]


def make_case(name, pattern, hot, background=BACKGROUND_W):
    """hot is a list of (tier, (row, col), power_w)."""
    maps = [
        [[background] * POWER_COLS for _ in range(POWER_ROWS)] for _ in range(TIERS)
    ]
    for tier, (row, col), power in hot:
        maps[tier][row][col] = power
    return name, "test", pattern, maps


def build_cases():
    rng = random.Random(1)
    cases = []

    # More hotspots than any training case, at an in-range power.
    for index in range(8):
        sites = rng.sample([(t, tile) for t in range(TIERS) for tile in ALL_TILES], 4)
        cases.append(
            make_case(
                f"hard_many_hotspots_{index:02d}", "many_hotspots",
                [(t, tile, 0.02) for t, tile in sites],
            )
        )

    # Cross-tier pairs with unequal powers.
    pairs = rng.sample([(a, b) for a in ALL_TILES for b in ALL_TILES if a != b], 4)
    for index, (lower, upper) in enumerate(pairs):
        for tag, (p_low, p_up) in (("lo", (0.01, 0.03)), ("hi", (0.03, 0.01))):
            cases.append(
                make_case(
                    f"hard_mixed_power_{index:02d}_{tag}", "mixed_power_pair",
                    [(0, lower, p_low), (1, upper, p_up)],
                )
            )

    # Hotspot power above the 30 mW training maximum.
    for index, tile in enumerate(rng.sample(ALL_TILES, 4)):
        cases.append(
            make_case(
                f"hard_high_power_single_{index:02d}", "high_power",
                [(index % TIERS, tile, 0.04)],
            )
        )
    for index, tile in enumerate(rng.sample(ALL_TILES, 4)):
        cases.append(
            make_case(
                f"hard_high_power_stacked_{index:02d}", "high_power",
                [(0, tile, 0.04), (1, tile, 0.04)],
            )
        )

    # Background different from the 5 mW used in training.
    for background in (0.003, 0.007):
        for index in range(4):
            lower, upper = rng.sample(ALL_TILES, 2)
            cases.append(
                make_case(
                    f"hard_background_{round(background * 1e3)}mW_{index:02d}",
                    "background_shift",
                    [(0, lower, 0.01), (1, upper, 0.01)],
                    background,
                )
            )
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "phase3d" / "dataset" / "stack_v2_hard"
    )
    parser.add_argument("--inputs-only", action="store_true")
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    if (dataset / "manifest.tsv").exists() or (dataset / "cases").exists():
        raise FileExistsError(
            f"{dataset} already contains cases; choose a new dataset directory."
        )

    dataset.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
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
