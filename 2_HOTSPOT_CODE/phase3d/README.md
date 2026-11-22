# Phase 3D: Stacked-IC Thermal Modeling

Phase 3D is a proposed extension of the existing 2D power-map workflow to a
stacked 3D integrated circuit. It is separate from Phase 3, which remains the
power-pattern generalization experiment in `phase3/`.

This experiment is separate from Phase 2 and Phase 3. It uses its own scripts
and output directory; it does not overwrite their datasets, checkpoints, or
results.

## Convert LaTeX to Word

`latex_to_word.py` uses [Pandoc](https://pandoc.org/) to convert a `.tex` file
to a Microsoft Word `.docx` document. Install Pandoc and make sure `pandoc` is
available on `PATH`, then run from the repository root:

```powershell
python phase3d/latex_to_word.py paper.tex
```

This creates `paper.docx` next to the input. Choose a different output path
with `--output`, use `--force` to replace an existing output, or pass a Word
reference document to apply its styles:

```powershell
python phase3d/latex_to_word.py paper.tex --output output/paper.docx
python phase3d/latex_to_word.py paper.tex --reference-doc word-template.docx
```

Pandoc converts supported LaTeX constructs; custom commands and package-specific
formatting may need adjustment in the source or the Word document afterward.

## Goal

Adapt the established workflow to generate power inputs for multiple active
tiers, obtain 3D temperature-field ground truth from HotSpot, train models for
the resulting 3D problem, and evaluate them on held-out power patterns or
stack configurations.

The process follows the existing workflow:

1. Define and validate the physical stack and tier-specific power maps.
2. Generate HotSpot inputs and run the 3D grid solver for ground truth.
3. Convert power maps and temperature fields into model-ready tensors.
4. Train candidate models on training cases.
5. Evaluate on held-out cases against HotSpot, reporting error by tier and
   across the stack.
6. Reuse the end-to-end inference and visualization process for new cases.

The workflow is analogous to the 2D work, but the model and physics must
represent the third spatial dimension. The existing Phase 2 PINO/PIKAN
implementations use 2D Fourier layers and a 2D heat-equation residual; they
must not be assumed to support volumetric inputs or outputs as-is.

## First milestone: two-tier HotSpot smoke test

The initial controlled stack is:

- Layer 0: active lower silicon tier, 150 µm thick.
- Layer 1: TIM between tiers, 50 µm thick.
- Layer 2: active upper silicon tier, 150 µm thick.
- Shared footprint: 1 mm × 1 mm.
- Default thermal grid: 32 × 32 cells per layer.
- Default power maps: 4 × 4 tiles per active tier.
- Default source-tier power: 0.5 mW per tile, with one 2 mW tile on the
  lower tier. The other tier receives zero power so its temperature response
  demonstrates conduction through the stack.
- Ambient and package settings: carried over from the Phase 1 HotSpot setup.

These are Phase 1's documented material parameters adapted to a smaller,
two-tier synthetic test. This is a solver/input-pipeline smoke test, not a
validated physical stack or a claim that the dimensions represent a specific
manufacturing process.

### Run in WSL

From the repository root, build HotSpot if needed and run:

```sh
make -j2
bash phase3d/run_stack_smoke_test.sh
```

The script creates `phase3d/smoke_test/` and runs HotSpot for a grid
steady-state solution. In addition to the three configured stack layers,
HotSpot includes its heat-spreader and heat-sink package layers in the grid
output (layers 3 and 4). The output summarizer validates all five layers, the
number and ordering of grid values per layer, and finite temperatures, then
reports each layer's minimum, maximum, mean, and peak location. It also maps
the configured hot power tile to its expected grid-cell region using
HotSpot's floorplan-to-grid indexing convention and checks whether that region
contains the active tier's peak.

The lower tier is hot by default. To move the hot tile to the upper tier,
select another output directory so the existing case is preserved:

```sh
OUTPUT_DIR="$PWD/phase3d/smoke_test_upper" HOT_TIER=1 \
  bash phase3d/run_stack_smoke_test.sh
```

The defaults give the powered tier 0.5 mW on each background tile and 2 mW
on the hot tile. For a separate higher-power diagnostic run, the power values
can be overridden. This is only to make small inter-tier changes easier to
see in HotSpot's two-decimal output; it is not a realistic power target:

```sh
OUTPUT_DIR="$PWD/phase3d/smoke_test_upper_10x" HOT_TIER=1 \
LOW_POWER=0.005 HIGH_POWER=0.02 \
  bash phase3d/run_stack_smoke_test.sh
```

The 10x run gives the powered tier 5 mW per background tile and 20 mW on the
hot tile. Repeat with `HOT_TIER=0` and a different output directory to compare
both source-tier positions.

The script refuses to generate inputs in a non-empty output directory.
Choose a new `OUTPUT_DIR` for another run rather than deleting previous
outputs. Grid and power-map sizes and hot-tile coordinates can also be
overridden with `ROWS`, `COLS`, `POWER_ROWS`, `POWER_COLS`, `HOT_ROW`, and
`HOT_COL`; source-tier powers can be overridden with `LOW_POWER` and
`HIGH_POWER`.

After a successful run, inspect the per-layer summary and share it along with
any HotSpot warnings or errors. We will use the result to verify layer order,
temperature range, cross-tier thermal coupling, and peak location before
deciding whether to build a dataset.

## Second milestone: pattern-held-out dataset

`generate_stack_dataset.py` builds 120 cases on the smoke-test stack, split by
pattern as in Phase 3. Every tile on both tiers has a 5 mW background; hot
tiles are the only difference between cases (10x power levels, per the
precision decision below).

- **Train (96):** one hotspot (10, 20, or 30 mW) on any of the 16 tiles of
  either tier.
- **Test (24), all at 10 mW per hotspot:**
  - `dual_adjacent` (8) and `dual_separated` (8): two hotspots on the same
    tier, 4 of each per tier.
  - `cross_tier_stacked` (4): one hotspot on each tier at the same tile
    position.
  - `cross_tier_offset` (4): one hotspot on each tier at different positions.

Cross-tier patterns exist only in 3D, so they are the most informative test
of whether a model learned inter-tier coupling rather than per-tier maps.
Each test case's total hot power (20 mW) matches a middle training case.

### Generate (WSL)

```sh
cd /mnt/c/Users/PidotKing/Downloads/Research/HotSpot
python3 phase3d/generate_stack_dataset.py
```

This writes `phase3d/dataset/stack_v1/` (inputs, HotSpot outputs and logs per
case, plus `manifest.tsv` once all cases finish). It refuses to run if the
dataset directory already contains cases. `--inputs-only` writes inputs
without running HotSpot.

### Convert to tensors (Windows PowerShell)

```powershell
C:/Users/PidotKing/AppData/Local/Programs/Python/Python311/python.exe phase3d/prepare_stack_tensors.py
```

This writes `train.pt` and `test.pt`. `power` has shape
`(cases, 2, 32, 32)` (lower and upper tier) and `temperature` has shape
`(cases, 3, 32, 32)` (lower tier, TIM, upper tier = HotSpot layers 0-2).
Package layers 3 and 4 are excluded. Power tiles are flipped vertically so
that power and temperature share HotSpot's grid orientation.

## Third milestone: models and evaluation

`stack_models.py` defines three models that map the two tier power maps
`(batch, 2, 32, 32)` to the three layer temperature maps `(batch, 3, 32, 32)`:

- `fno_mlp`: the Phase 2 Fourier operator block with the MLP activation, taking
  two input channels and producing three output channels.
- `fno_kan`: the same, using the Phase 2 KAN-style activation.
- `cnn3d`: a small dilated 3D convolution baseline over a
  (lower tier, TIM, upper tier) volume, with a zero-power slice for the TIM.

These are **data-loss-only** models. Phase 2 added a 2D heat-equation residual;
a 3D residual needs calibrated layer properties and is deferred, so the
`fno_*` models are not called PINO/PIKAN here. Temperatures are normalized per
layer using training statistics, because the upper tier's signal is much
weaker than the lower tier's.

The evaluator also reports `train_mean`, which predicts the average training
temperature map for every case. A model only shows it learned something if it
beats this baseline, so read results against it.

### Train and evaluate (Windows PowerShell)

```powershell
Set-Location C:\Users\PidotKing\Downloads\Research\HotSpot
C:/Users/PidotKing/AppData/Local/Programs/Python/Python311/python.exe phase3d/train_stack_models.py --epochs 1000
C:/Users/PidotKing/AppData/Local/Programs/Python/Python311/python.exe phase3d/evaluate_stack_models.py
```

Training writes `phase3d/checkpoints/stack_v1/` and refuses to overwrite
existing checkpoints; use `--output` and `--seed` for repeat runs. The
evaluator reports MAE, RMSE, and peak error per model, held-out pattern, and
layer, and writes `phase3d/results/stack_v1/metrics.json`. Use several seeds
before drawing conclusions from any difference between models.

### First results (seeds 7, 11, 23; 1000 epochs)

Mean held-out MAE in K over three seeds, with the min–max across seeds in
parentheses. Lower tier / upper tier shown; the TIM tracks the lower tier within
about 0.005 K.

| Pattern | `train_mean` | `cnn3d` | `fno_mlp` | `fno_kan` |
|---|---|---|---|---|
| dual_adjacent (lower) | 0.082 | 0.034 (0.032–0.037) | 0.023 (0.018–0.030) | 0.021 (0.020–0.024) |
| dual_separated (lower) | 0.073 | 0.035 (0.033–0.039) | 0.023 (0.014–0.035) | 0.017 (0.016–0.019) |
| cross_tier_offset (lower) | 0.054 | 0.040 (0.038–0.044) | 0.036 (0.028–0.050) | 0.032 (0.023–0.043) |
| cross_tier_stacked (lower) | 0.056 | 0.057 (0.043–0.067) | 0.038 (0.025–0.058) | 0.040 (0.026–0.059) |
| upper tier, all patterns | 0.014–0.017 | 0.007 | 0.007–0.011 | 0.007–0.012 |

Lower tier + TIM MAE per seed (7, 11, 23): `train_mean` 0.063 (all seeds);
`cnn3d` 0.044, 0.037, 0.043; `fno_mlp` 0.023, 0.030, 0.033; `fno_kan` 0.021,
0.033, 0.026.

- All models beat `train_mean` on the dual patterns. The Fourier models are
  best there (about 3-4x lower error than `train_mean`), and the ordering held on every seed.
- The cross-tier patterns are harder and much more seed-dependent. On
  `cross_tier_stacked`, `cnn3d` is no better than `train_mean`, and the Fourier
  models range from 0.025 to 0.059 K across seeds.
- `fno_kan` vs `fno_mlp`: `fno_kan` has the lower mean on 3 of 4 lower-tier
  patterns, but the seed ranges overlap. No difference is established.
- The upper tier is at or below the 0.01 K label resolution, so this
  comparison says little.
- Seed 7 was the best run for both Fourier models, so single-seed numbers are optimistic.
- All models are data-loss only (no physics residual); the test set is 24 cases.

### Second dataset: cross-tier training cases (`stack_v2`)

`stack_v2` keeps the same 24 test cases and adds 36 training cases that heat
both tiers (12 stacked, 24 offset; none match a test configuration), for 132
training cases in total. Generate it with
`generate_stack_dataset.py --dataset phase3d/dataset/stack_v2 --cross-tier-train`
and train with `--dataset phase3d/dataset/stack_v2`.

Lower-tier held-out MAE in K, mean over seeds 7/11/23 (min–max):

| Pattern | Model | v1 | v2 |
|---|---|---|---|
| cross_tier_offset | `cnn3d` | 0.040 (0.038–0.044) | 0.021 (0.020–0.022) |
| cross_tier_offset | `fno_mlp` | 0.036 (0.028–0.050) | 0.018 (0.017–0.018) |
| cross_tier_offset | `fno_kan` | 0.032 (0.023–0.043) | 0.022 (0.021–0.022) |
| cross_tier_stacked | `cnn3d` | 0.057 (0.043–0.067) | 0.023 (0.022–0.026) |
| cross_tier_stacked | `fno_mlp` | 0.038 (0.025–0.058) | 0.020 (0.019–0.020) |
| cross_tier_stacked | `fno_kan` | 0.040 (0.026–0.059) | 0.021 (0.021–0.022) |

- Cross-tier error roughly halves, and the seed-to-seed spread shrinks from
  about 0.03 K to about 0.001 K. The v1 weakness was a training-data gap, not a model limit.
- Dual-hotspot patterns are essentially unchanged (within seed spread).
- The upper tier improves slightly on the cross-tier patterns (0.006–0.008 K), but it sits at the 0.01 K label resolution, so that is not a meaningful result.
- With v2 the three models are close on the cross-tier patterns (0.018–0.023 K); the model ranking is not established.
- This is a data-coverage result with this training distribution; the test
  patterns are still the same 24 cases and all models are data-loss only.

### Harder generalization test (`stack_v2_hard`)

A test-only set of 32 cases, generated by `generate_stack_hard_test.py`, none of
which overlap `stack_v2`. The `stack_v2` checkpoints (seeds 7/11/23) are scored on
it with `evaluate_stack_models.py --test-dataset phase3d/dataset/stack_v2_hard`.
Patterns (8 cases each): `many_hotspots` (four 20 mW hotspots; training had at most
two), `mixed_power_pair` (cross-tier pair at 10 and 30 mW), `high_power` (40 mW,
above the 30 mW training maximum), `background_shift` (3 or 7 mW background versus
5 mW in training).

Lower-tier MAE in K, mean over 3 seeds (min–max):

| Pattern | `train_mean` | `cnn3d` | `fno_mlp` | `fno_kan` |
|---|---|---|---|---|
| mixed_power_pair | 0.146 | 0.068 (0.066–0.070) | 0.063 (0.061–0.064) | 0.067 (0.066–0.069) |
| many_hotspots | 0.359 | 0.169 (0.142–0.183) | 0.088 (0.069–0.119) | 0.104 (0.091–0.116) |
| high_power | 0.356 | 0.114 (0.108–0.124) | 0.091 (0.088–0.093) | 0.116 (0.109–0.123) |
| background_shift | 0.549 | 0.636 (0.562–0.682) | 0.225 (0.155–0.346) | 0.272 (0.231–0.336) |

- Errors are 3–10x larger than on the in-distribution test (0.02 K), so the
  `stack_v2` result does not carry over unchanged. Models still beat `train_mean`
  on most patterns, though.
- `background_shift` is the weakest. `cnn3d` is worse than `train_mean` on it,
  and the Fourier models cut the baseline error by only about 2-2.5x. The models
  have never seen a different background, so they cannot separate its offset
  from hotspot heating.
- `fno_mlp` has the lowest error on 3 of 4 patterns, and the Fourier models are better on the two
  hardest ones (`many_hotspots`, `background_shift`). `cnn3d` is competitive on
  `mixed_power_pair` and `high_power`.
- Peak error is the poorest metric here: on `high_power`, Fourier peaks are
  underestimated by about 0.3 K (versus 0.9 K for `train_mean`).
- Upper-tier errors are 0.02-0.08 K but sit near label resolution on the milder
  patterns; treat them as weaker evidence.
- Still data-loss-only, single training set, three seeds.

### Varied-background training (`stack_v3`)

`stack_v3` adds 72 training cases to `stack_v2` (204 training cases; the original
24 test cases are unchanged): 48 with backgrounds of 2/4/6/8 mW (single, same-tier
pair, and cross-tier pair hotspots) and 24 with 3-5 hotspots. Hotspot power stays
at or below 30 mW; the 3 and 7 mW test backgrounds and 40 mW hotspots remain unseen.
Generate with `generate_stack_dataset.py --dataset phase3d/dataset/stack_v3
--cross-tier-train --varied-train`. No v3 training case matches an original or hard test case.

Lower-tier MAE in K on the hard set, v2 -> v3 (mean over seeds 7/11/23):

| Pattern | `cnn3d` | `fno_mlp` | `fno_kan` |
|---|---|---|---|
| background_shift | 0.636 -> 0.089 | 0.225 -> 0.023 | 0.272 -> 0.032 |
| many_hotspots | 0.169 -> 0.124 | 0.088 -> 0.068 | 0.104 -> 0.079 |
| mixed_power_pair | 0.068 -> 0.075 | 0.063 -> 0.061 | 0.067 -> 0.065 |
| high_power | 0.114 -> 0.151 | 0.091 -> 0.093 | 0.116 -> 0.108 |

- The background gap is closed for the Fourier models (about 10x lower error,
  now near the in-distribution level of 0.02 K), with seed spread shrinking to
  about 0.001-0.007 K. This is interpolation between trained backgrounds
  (2-8 mW), not extrapolation outside that range.
- `many_hotspots` improves by roughly 20-25% for all models but stays well above
  the in-distribution level (0.07-0.12 K).
- `high_power` (40 mW) is unchanged: it is extrapolation beyond the training
  power range, and extra data inside the range does not fix that.
- `cnn3d` got worse on the original test patterns (for example cross_tier_stacked
  0.023 -> 0.034 K, with peak error 0.018 -> 0.115 K) and on `high_power`. The
  Fourier models are unchanged within seed spread (0.014-0.022 K), so extra data
  did not hurt them.
- Still data-loss-only, 3 seeds, one background family; a different stack or
  power-map resolution would need new data.

## Decisions made and open items

Resolved in version 1:
- **Stack:** controlled synthetic two-tier stack (identical tiers plus TIM), kept
  as a pipeline fixture rather than the SKY130 block.
- **Prediction target:** the three stack-layer temperature maps (lower tier,
  TIM, upper tier) on a 32 x 32 grid; spreader and sink layers are excluded.
- **Models:** `fno_mlp`, `fno_kan`, and a `cnn3d` baseline, all data-loss-only.
  They are not PINO/PIKAN, because no physics residual is used.
- **Evaluation split:** train on single and cross-tier hotspots; hold out
  multi-hotspot patterns, plus a separate harder set (`stack_v2_hard`).
- **Label resolution:** HotSpot is left unmodified; 10x power levels are used.

Open (carried to `phase3d_v2/`): the 3D heat-equation residual, hotspot power
beyond the training range, many-hotspot accuracy, and a PINO-vs-PIKAN comparison.

Do not overwrite Phase 2 or Phase 3 datasets and checkpoints; use separate
`phase3d/` artifacts.

## Summary of version 1

Phase 3D version 1 is complete: a reproducible HotSpot-label to model
pipeline for a two-tier stack, with datasets `stack_v1`, `stack_v2`,
`stack_v3` and the hard test `stack_v2_hard`, all trained with seeds 7, 11, 23.

1. **The pipeline works.** The Fourier models reach about 0.02 K MAE on the
   original held-out patterns, 3-4x below the `train_mean` baseline on dual patterns.
2. **Training-data coverage drove the results more than model choice.**
   Adding both-tier cases (`stack_v2`) halved cross-tier error; varying the
   background (`stack_v3`) cut background-shift error about 10x for the Fourier models.
3. **Known gaps:** hotspot power above the training range (40 mW), 3-5 hotspot
   cases (0.07-0.12 K), and any change to the stack or boundary conditions.
4. **`cnn3d` is the weakest model** and got worse with more varied data.
5. **No PINO-vs-PIKAN conclusion.** `fno_mlp` and `fno_kan` are within seed
   spread on most patterns.
6. **Limits:** 0.01 K label resolution makes upper-tier errors uninformative;
   test sets are small (24 and 32 cases); 3 seeds; one stack design.

Results are in `phase3d/results/` (`stack_v1*`, `stack_v2*`, `stack_v2_hard*`,
`stack_v3*`). Version 2 is planned in [../phase3d_v2/README.md](../phase3d_v2/README.md).

## Status

Version 1 is complete (see the summary above). The smoke-test findings that
shaped the design are kept below.

The initial HotSpot run completed and produced five 32 × 32 output layers.
The specified hot power tile (row 1, column 1) covers grid rows [16, 24) and
columns [8, 16): HotSpot reverses the vertical floorplan coordinate when
numbering grid rows, but preserves the horizontal coordinate. The observed
lower-tier peak at row 16, column 9 is inside that tile's grid footprint, so
the earlier apparent location mismatch was a coordinate-interpretation issue,
not an off-target hotspot. This mapping check is now included in the runner.

With the lower tier powered, temperatures ranged from 318.15-318.32 K; the
upper tier was reported as 318.17-318.17 K. With the upper tier powered,
temperatures ranged from 318.15-318.18 K; the lower tier was reported as
318.17-318.17 K. Both runs placed the source-tier peak inside the configured
hot tile. Since HotSpot writes only two decimal places and the inactive-tier
temperature was nearly flat at that resolution, these runs do not establish
the amount of cross-tier coupling.

The 10x diagnostic runs (not a calibrated power scenario) show clear coupling
and a directional asymmetry:

| Powered tier | Layer 0 (lower) | Layer 1 (TIM) | Layer 2 (upper) | Layer 3 (spreader) |
|---|---|---|---|---|
| Lower (layer 0) | 319.59-319.87 K | 319.46-319.71 K | 318.34-318.37 K | 318.20-318.22 K |
| Upper (layer 2) | 318.35-318.36 K | 318.34-318.37 K | 318.33-318.47 K | 318.20-318.22 K |

HotSpot appends the spreader and heat sink after the last configured layer,
so the sink side is above layer 2. Heat from the lower tier must conduct up
through the TIM and the upper tier, so it runs ~1.4 K above the upper tier's
level and produces a visible (if small) response in the upper tier. Heat from
the upper tier flows directly toward the sink, so the lower tier stays at the
upper tier's ambient level (~318.35 K) with no measurable response. Both
runs again placed the source-tier peak inside the hot tile. Phase 3D models
should therefore expect strongly tier-dependent temperatures: the same power
pattern gives a different thermal result depending on which tier carries it.

Caveat for dataset labels: HotSpot writes grid temperatures with two decimals
(0.01 K). The lower-tier hotspot's imprint on the upper tier spans only
318.34-318.37 K (about 3 quantization steps), so label quantization is a
significant error source for any learned model at these power levels.

Decision: keep HotSpot unmodified and generate the dataset at the higher
(10x) power levels so temperature signals span many 0.01 K steps. Report
results with this quantization floor in mind.
