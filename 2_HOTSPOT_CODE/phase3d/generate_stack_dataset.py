"""Generate HotSpot labels for a two-tier single-to-dual hotspot study."""

import argparse
import csv
from pathlib import Path
import random
import subprocess

from generate_stack_smoke_test import (
    write_config,
    write_floorplan,
    write_layer_config,
)


ROOT = Path(__file__).resolve().parents[1]
GRID_ROWS = 32
GRID_COLS = 32
POWER_ROWS = 4
POWER_COLS = 4
TIERS = 2
BACKGROUND_POWER_W = 0.005
TRAIN_HOT_POWERS_W = (0.01, 0.02, 0.03)
TEST_HOT_POWER_W = 0.01

# Tile coordinates are (row, col) in the 4 x 4 power map.
ADJACENT_PAIRS = (
    ((0, 0), (0, 1)),
    ((1, 1), (1, 2)),
    ((2, 2), (2, 3)),
    ((3, 0), (3, 1)),
)
SEPARATED_PAIRS = (
    ((0, 0), (2, 2)),
    ((1, 1), (3, 3)),
    ((0, 3), (2, 1)),
    ((1, 2), (3, 0)),
)
STACKED_TILES = ((1, 1), (2, 2), (0, 3), (3, 0))
OFFSET_PAIRS = (
    ((1, 1), (2, 2)),
    ((2, 2), (1, 1)),
    ((0, 0), (3, 3)),
    ((3, 3), (0, 0)),
)


def background_maps(background=BACKGROUND_POWER_W):
    return [
        [[background] * POWER_COLS for _ in range(POWER_ROWS)]
        for _ in range(TIERS)
    ]


def make_case(name, split, pattern, hot_tiles, hot_power, background=BACKGROUND_POWER_W):
    maps = background_maps(background)
    for tier, (row, col) in hot_tiles:
        maps[tier][row][col] = hot_power
    return name, split, pattern, maps


VARIED_BACKGROUNDS_W = (0.002, 0.004, 0.006, 0.008)


def varied_train_cases():
    """Background-varied and many-hotspot training cases (3 and 7 mW stay unseen)."""
    rng = random.Random(2)
    sites = [(t, (r, c)) for t in range(TIERS)
             for r in range(POWER_ROWS) for c in range(POWER_COLS)]
    cases = []
    for background in VARIED_BACKGROUNDS_W:
        tag = round(background * 1e3)
        for index in range(12):
            power = TRAIN_HOT_POWERS_W[index % len(TRAIN_HOT_POWERS_W)]
            kind = index // 4
            if kind == 0:
                hot = rng.sample(sites, 1)
            elif kind == 1:
                hot = [(0, rng.choice(sites)[1]), (1, rng.choice(sites)[1])]
            else:
                tier = rng.randrange(TIERS)
                tiles = rng.sample([s[1] for s in sites if s[0] == tier], 2)
                hot = [(tier, tile) for tile in tiles]
            cases.append(
                make_case(
                    f"train_bg{tag}mW_{index:02d}", "train", "background_varied",
                    hot, power, background,
                )
            )
    for index in range(24):
        count = 3 + index % 3
        power = TRAIN_HOT_POWERS_W[index % len(TRAIN_HOT_POWERS_W)]
        background = (0.004, 0.005, 0.006)[index % 3]
        cases.append(
            make_case(
                f"train_many_{index:02d}", "train", "many_hotspots_train",
                rng.sample(sites, count), power, background,
            )
        )
    return cases


def cross_tier_train_cases():
    """Both-tier training cases that never reuse a held-out test configuration."""
    test_stacked = set(STACKED_TILES)
    test_offsets = set(OFFSET_PAIRS)
    all_tiles = [(r, c) for r in range(POWER_ROWS) for c in range(POWER_COLS)]
    cases = []

    stacked_tiles = [tile for tile in all_tiles if tile not in test_stacked]
    for index, tile in enumerate(stacked_tiles):
        power = TRAIN_HOT_POWERS_W[index % len(TRAIN_HOT_POWERS_W)]
        cases.append(
            make_case(
                f"train_cross_stacked_r{tile[0]}c{tile[1]}_{round(power * 1e3)}mW",
                "train", "cross_tier_stacked_train",
                [(0, tile), (1, tile)], power,
            )
        )

    candidates = [
        (lower, upper)
        for lower in all_tiles
        for upper in all_tiles
        if lower != upper and (lower, upper) not in test_offsets
    ]
    rng = random.Random(0)
    for index, (lower, upper) in enumerate(rng.sample(candidates, 24)):
        power = TRAIN_HOT_POWERS_W[index % len(TRAIN_HOT_POWERS_W)]
        cases.append(
            make_case(
                f"train_cross_offset_{index:02d}_{round(power * 1e3)}mW",
                "train", "cross_tier_offset_train",
                [(0, lower), (1, upper)], power,
            )
        )
    return cases


def build_cases(cross_tier_train=False, varied_train=False):
    cases = []
    for hot_power in TRAIN_HOT_POWERS_W:
        for tier in range(TIERS):
            for row in range(POWER_ROWS):
                for col in range(POWER_COLS):
                    name = (
                        f"train_single_t{tier}_r{row}c{col}_"
                        f"{round(hot_power * 1e3)}mW"
                    )
                    cases.append(
                        make_case(
                            name, "train", "single_hotspot",
                            [(tier, (row, col))], hot_power,
                        )
                    )

    if cross_tier_train:
        cases.extend(cross_tier_train_cases())
    if varied_train:
        cases.extend(varied_train_cases())

    for tier in range(TIERS):
        for index, pair in enumerate(ADJACENT_PAIRS):
            cases.append(
                make_case(
                    f"test_dual_adjacent_t{tier}_{index:02d}", "test",
                    "dual_adjacent",
                    [(tier, tile) for tile in pair], TEST_HOT_POWER_W,
                )
            )
        for index, pair in enumerate(SEPARATED_PAIRS):
            cases.append(
                make_case(
                    f"test_dual_separated_t{tier}_{index:02d}", "test",
                    "dual_separated",
                    [(tier, tile) for tile in pair], TEST_HOT_POWER_W,
                )
            )

    for index, tile in enumerate(STACKED_TILES):
        cases.append(
            make_case(
                f"test_cross_tier_stacked_{index:02d}", "test",
                "cross_tier_stacked",
                [(0, tile), (1, tile)], TEST_HOT_POWER_W,
            )
        )
    for index, (lower, upper) in enumerate(OFFSET_PAIRS):
        cases.append(
            make_case(
                f"test_cross_tier_offset_{index:02d}", "test",
                "cross_tier_offset",
                [(0, lower), (1, upper)], TEST_HOT_POWER_W,
            )
        )
    return cases


def flatten(tier_map):
    return [power for row in tier_map for power in row]


def write_power_trace(path, maps):
    names = []
    powers = []
    for tier, tier_map in enumerate(maps):
        layer = tier * 2
        for row in range(POWER_ROWS):
            for col in range(POWER_COLS):
                names.append(f"T{layer}_R{row}_C{col}")
                powers.append(tier_map[row][col])
    path.write_text(
        " ".join(names) + "\n"
        + " ".join(f"{power:.12g}" for power in powers) + "\n",
        encoding="ascii",
    )


def write_case_inputs(case_dir, maps):
    case_dir.mkdir(parents=True, exist_ok=False)
    write_floorplan(case_dir / "tier_0.flp", POWER_ROWS, POWER_COLS, 0)
    write_floorplan(case_dir / "tim.flp", POWER_ROWS, POWER_COLS, 1)
    write_floorplan(case_dir / "tier_1.flp", POWER_ROWS, POWER_COLS, 2)
    write_layer_config(case_dir / "stack.lcf")
    write_power_trace(case_dir / "stack.ptrace", maps)
    write_config(case_dir / "stack.config", GRID_ROWS, GRID_COLS)


def run_case(case_name, maps, dataset, inputs_only):
    case_dir = dataset / "cases" / case_name
    write_case_inputs(case_dir, maps)
    if inputs_only:
        return

    outputs = case_dir / "outputs"
    outputs.mkdir()
    with (outputs / "hotspot.log").open("w", encoding="utf-8") as log:
        subprocess.run(
            [
                str(ROOT / "hotspot"),
                "-c", "stack.config",
                "-p", "stack.ptrace",
                "-grid_layer_file", "stack.lcf",
                "-model_type", "grid",
                "-grid_steady_file", "outputs/stack.grid.steady",
                "-steady_file", "outputs/stack.steady",
            ],
            check=True,
            cwd=case_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    label = outputs / "stack.grid.steady"
    if not label.is_file():
        raise FileNotFoundError(f"HotSpot did not create the expected label: {label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "phase3d" / "dataset" / "stack_v1",
    )
    parser.add_argument(
        "--inputs-only",
        action="store_true",
        help="write HotSpot inputs and the manifest without running HotSpot",
    )
    parser.add_argument(
        "--cross-tier-train",
        action="store_true",
        help="add training cases that heat both tiers (held-out tests unchanged)",
    )
    parser.add_argument(
        "--varied-train",
        action="store_true",
        help="add background-varied and many-hotspot training cases (stack_v3)",
    )
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    manifest = dataset / "manifest.tsv"
    if manifest.exists() or (dataset / "cases").exists():
        raise FileExistsError(
            f"{dataset} already contains cases; choose a new dataset "
            "directory rather than overwriting an experiment."
        )

    dataset.mkdir(parents=True, exist_ok=True)
    cases = build_cases(args.cross_tier_train, args.varied_train)
    temporary_manifest = dataset / "manifest.tsv.tmp"
    try:
        with temporary_manifest.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(
                [
                    "case", "split", "pattern", "tier0_powers_w",
                    "tier1_powers_w", "total_power_w",
                ]
            )
            for index, (case_name, split, pattern, maps) in enumerate(cases, 1):
                print(f"[{index}/{len(cases)}] Generating {case_name}", flush=True)
                run_case(case_name, maps, dataset, args.inputs_only)
                tier_powers = [flatten(tier_map) for tier_map in maps]
                writer.writerow(
                    [
                        case_name,
                        split,
                        pattern,
                        ",".join(f"{power:.12g}" for power in tier_powers[0]),
                        ",".join(f"{power:.12g}" for power in tier_powers[1]),
                        f"{sum(sum(powers) for powers in tier_powers):.12g}",
                    ]
                )
                stream.flush()
        temporary_manifest.replace(manifest)
    except Exception:
        if temporary_manifest.exists():
            temporary_manifest.unlink()
        raise

    print(f"Dataset generated: {dataset}")
    print(f"Cases: {len(cases)}; manifest: {manifest}")


if __name__ == "__main__":
    main()
