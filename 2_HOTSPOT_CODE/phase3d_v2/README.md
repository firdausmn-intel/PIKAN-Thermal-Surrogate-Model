# Phase 3D Version 2 (planned, not started)

Follow-up to [Phase 3D version 1](../phase3d/README.md). Version 1 stays
unchanged: its datasets, checkpoints, and results in `phase3d/` are the
baseline that version 2 is compared against. New artifacts go in
`phase3d_v2/`.

## Starting point (from version 1)

- Fourier models (`fno_mlp`, `fno_kan`) reach about 0.02 K MAE on the original
  held-out patterns; `cnn3d` is weaker.
- Training-data coverage mattered more than model choice.
- Open gaps: hotspot power above the training range (40 mW, 0.09-0.12 K MAE),
  3-5 hotspot cases (0.07-0.12 K), and any change to the stack or boundary
  conditions.
- All models are data-loss-only, so version 1 gives no PINO-vs-PIKAN comparison.

## Goals (to confirm before starting)

1. **Power extrapolation:** train to a higher power range, then test on a
   power level above it (for example, train to 50 mW, test at 60 mW).
   A cheap test of whether the gap is coverage.
2. **3D physics residual:** add a heat-equation loss that mirrors HotSpot's
   discretized thermal network, with per-layer conductivities and the sink
   boundary taken from HotSpot rather than guessed. This is the larger task.
3. **PINO vs PIKAN:** only once goal 2 exists, with more seeds and a larger
   test set. Until then, do not label the models PINO or PIKAN.
4. **Better label resolution (optional):** version 1 accepted HotSpot's 0.01 K
   output precision. Revisit only if the upper-tier results need it.

## Step 1 result: power extrapolation (done)

Dataset `power_train`: `stack_v3` cases plus 40/50 mW cases (singles on every
tile and tier, stacked, offset, and 3-4 hotspot cases), 291 training cases after
removing duplicates and any case equal to a `stack_v2_hard` test case. Test set
`power_ext_test`: 24 cases at 60 mW (above the 50 mW training maximum). Models,
seeds (7/11/23), and training settings are unchanged from version 1.
Generator: `generate_power_dataset.py`.

Lower-tier MAE in K at 60 mW, mean over seeds (peak error in parentheses for `fno_mlp`):

| Pattern | `train_mean` | `cnn3d` | `fno_mlp` | `fno_kan` |
|---|---|---|---|---|
| extrap_single | 0.430 | 0.139 | 0.110 (0.32) | 0.123 |
| extrap_dual | 0.771 | 0.252 | 0.182 (0.50) | 0.212 |
| extrap_offset | 0.683 | 0.245 | 0.225 (0.35) | 0.215 |
| extrap_stacked | 0.683 | 0.293 | 0.226 (0.60) | 0.227 |
| extrap_many | 0.994 | 0.374 | 0.269 (0.79) | 0.269 |

Hard set (`stack_v2_hard`), v3 -> `power_train`, lower-tier MAE:

| Pattern | `fno_mlp` | `fno_kan` | `cnn3d` |
|---|---|---|---|
| high_power (40 mW) | 0.093 -> 0.093 | 0.108 -> 0.091 | 0.151 -> 0.113 |
| many_hotspots | 0.068 -> 0.071 | 0.079 -> 0.087 | 0.124 -> 0.130 |
| background_shift | 0.023 -> 0.029 | 0.032 -> 0.037 | 0.089 -> 0.119 |

The original 24-case test is essentially unchanged for the Fourier models
(0.015-0.022 K); `cnn3d` is slightly worse (0.033-0.053 K).

Findings:
- Extrapolation to 60 mW still beats `train_mean` by about 2.5-4x, but errors
  (0.11-0.27 K) are 5-10x larger than in-range, and peaks are under-predicted by
  0.3-0.8 K.
- Putting 40 mW in the training range did **not** fix the 40 mW hard-set cases
  (`fno_mlp` stayed at 0.093 K, `fno_kan` 0.108 -> 0.091 K). The 40 mW gap
  was therefore not mainly a coverage problem; the models under-fit hotter, sharper
  peaks even for powers they have seen. Likely contributors (not yet tested):
  the 12 x 12 Fourier-mode truncation, training length, and data-only loss.
- `many_hotspots` and `background_shift` did not improve and are slightly worse.
- The Fourier models and `fno_mlp` vs `fno_kan` remain within seed spread.
- Not tested: whether a physics residual would fix the peak under-prediction.

Implication for step 2: more training power coverage is not the answer to the
peak-height error. Before building the residual, check whether a larger/longer
model (more modes, more epochs) closes the gap. If it does, the residual is not
needed for this problem; if not, the residual becomes the next candidate.

## Step 1b result: capacity test (done, single seed)

`fno_mlp`, seed 7, trained on `power_train`; one factor changed at a time
(`--modes`, `--width`, `--epochs` in `train_stack_models.py`). Lower-tier MAE in K:

| Test | Base (m12, w16, 1000 ep) | A: m16 | B: 3000 ep | C: m16, w32, 3000 ep |
|---|---|---|---|---|
| 60 mW single | 0.110 | 0.108 | 0.109 | 0.117 |
| 60 mW dual | 0.171 | 0.193 | 0.338 | 0.354 |
| 60 mW offset | 0.229 | 0.226 | 0.296 | 0.374 |
| 60 mW stacked | 0.229 | 0.229 | 0.273 | 0.360 |
| 60 mW many | 0.275 | 0.275 | 0.450 | 0.549 |
| hard high_power (40 mW) | 0.095 | 0.092 | 0.090 | 0.082 |
| hard many_hotspots | 0.071 | 0.069 | 0.089 | 0.089 |
| hard background_shift | 0.033 | 0.022 | 0.020 | 0.021 |
| original test (4 patterns) | 0.016-0.021 | 0.014-0.019 | 0.015-0.020 | 0.014-0.020 |

- More Fourier modes alone (A) changes almost nothing.
- Training longer or making the model larger (B, C) improves in-range accuracy
  slightly but makes 60 mW extrapolation clearly **worse** (for example
  `extrap_many` 0.275 -> 0.549 K for C). That pattern is consistent with the
  model fitting the training power range more tightly without learning how
  temperature scales beyond it.
- The 40 mW hard-set error moves only 0.095 -> 0.082 K at best. Capacity and
  training length do not close the high-power gap.
- The `background_shift` change (0.033 -> 0.020-0.022 K) is a single-seed
  difference and appeared in all three runs; it may reflect seed variation
  rather than a real effect, so it is not claimed as an improvement.
- Caveat: single seed, one model, and the base values come from the seed-7
  run, so changes below about 0.01 K should not be read as meaningful.

Conclusion: the high-power and extrapolation errors are not fixed by adding
power coverage (step 1) or capacity/training length (step 1b). A data-only loss
has no mechanism to make temperature scale with power outside the data. This
is the case for step 2 (physics residual); it is not yet shown that the
residual fixes it.

## Step 2a result: heat-balance feasibility check (done)

`check_heat_balance.py` (read-only) rebuilds the cell-by-cell heat balance of the
three stack layers from the layer file and HotSpot's resistor rules
(`temperature_grid.c`, `RCutil.c`), and applies it to HotSpot's own labels. For each
cell: `r = sum over neighbours g * (T_neighbour - T) + P` (W). Layer 3 (spreader)
temperatures from the label file are the top boundary; side faces are adiabatic.
Conductances: lateral `g = k * t` per cell face; vertical `g = 1 / rz` of the **lower**
layer only (HotSpot's `find_res` returns `layers[lower].rz` between adjacent layers, not
half-plus-half). Confirmed on labels: that convention balances energy; the
half-plus-half convention misses by +79% and +125% of layer power.

Results (24 cases each, lower-layer-rz convention):

| Dataset | Layer 0 block residual / block power | Layer 2 block residual / block power | Net residual per case / power per case |
|---|---|---|---|
| `power_train` | 3.3e-4 / 7.3e-3 W | 3.0e-4 / 7.4e-3 W | about 4e-5 W / 0.1 W |
| `power_ext_test` (60 mW) | 3.1e-4 / 1.4e-2 W | 3.3e-4 / 1.4e-2 W | about 5e-5 W / 0.13 W |
| `stack_v2_hard` | 3.4e-4 / 8.3e-3 W | 3.8e-4 / 8.4e-3 W | about 6e-5 W / 0.10 W |

(Blocks are 8 x 8 cells, one power tile.)

- The residual built from the layer file and HotSpot's rules is physically
  correct: per-tile energy balance holds to about 2-5% and total energy to under
  0.1%, including the 40-60 mW cases.
- At **cell** level the residual (1.2-1.8e-4 W RMS) is no larger than the effect of
  0.01 K label rounding (1.9e-4 W RMS), and is comparable to the power in one cell
  (about 8e-5 W at 5 mW per tile). So the labels cannot confirm the balance
  cell by cell; the residual is only checkable at tile level or above. Model
  predictions are continuous, so this limit applies to checking against labels, not
  to using the residual as a training loss.
- The footprint is only 1 mm of a 30 mm spreader and 60 mm sink, so most heat leaves
  sideways into the package periphery. Modelling that is not needed: a model that also
  predicts the spreader layer (layer 3) closes the stack residual.

Conclusion: a 3D residual loss is feasible. Not yet shown that it improves
extrapolation. The two-step design would be: (1) extend tensors with layer 3 so the model
predicts four layers; (2) train with data loss plus a residual term in physical
units, then score on the 60 mW set.

## Step 2b result: residual loss (single seed 7, `power_train`)

`train_residual_models.py` (4 output layers, loss = data MSE + weight x block heat-balance
residual) and `evaluate_residual_models.py`. Weights 0 (data-only 4-layer control), 1 and
10. Results in `results/resid_w{0,1,10}_{orig,ext,hard}_seed7`.

- The residual term works as an optimiser target: block residual RMS falls about 8x
  (original test 3e-3 -> 4e-4 W; 60 mW set 3e-2 -> 5e-3 W; HotSpot labels are about 3e-4 W).
- It does **not** reduce temperature error where data-only fails. 60 mW MAE is unchanged
  (e.g. `extrap_many` 0.255 -> 0.265 K for `fno_mlp`, 0.256 -> 0.257 K for `fno_kan`);
  40 mW `high_power` is also unchanged (0.093 -> 0.098 K / 0.092 -> 0.094 K).
- Small gains only in some peak errors (`fno_kan` extrap_dual peak 0.527 -> 0.372 K,
  hard many_hotspots MAE 0.082 -> 0.070 K); these are within what seed spread could explain.
- Weight 10 is worse everywhere (in-range MAE about 0.04 vs 0.02 K; 60 mW MAE up to 0.33 K).
- Conclusion: with the spreader layer also predicted, the balance can be satisfied
  while temperatures are still scaled wrongly, because spreader temperatures are only
  learned from data. The residual does not fix power extrapolation as set up.

## Step 2c result: fixed spreader boundary (single seed 7)

`--boundary fixed`: the model predicts 3 chip layers and the spreader is set to
318.15 K + R x total chip power (R = 0.650 K/W fitted on the training set; the fit holds
to about 0.002 K on the 60 mW set). Results in `results/fixed_w{1,10}_{orig,ext,hard}_seed7`.

- Same outcome as step 2b. At weight 1, 60 mW `extrap_many` MAE is 0.258 K (`fno_kan`)
  and 0.262 K (`fno_mlp`), against 0.256 / 0.255 K data-only; 40 mW `high_power` is 0.094 / 0.098 K
  against 0.092 / 0.093 K. In-range MAE is unchanged (about 0.02 K).
- Weight 10 is again worse (in-range about 0.03-0.04 K, 60 mW up to 0.32 K).
- The block residual on the 60 mW set stays 5e-3 to 8e-3 W, versus 3e-4 W on labels, so
  the residual is not being satisfied outside the training power range.
- Conclusion: a block-level heat-balance loss on the training inputs does not carry the
  temperature-scales-with-power relation to higher power. It does not help in either
  boundary setup.

## Step 3 result: 8-seed comparison (done)

Seeds 7, 11, 23, 31, 41, 53, 67, 79; `power_train`; width 16, 12 modes, 1000 epochs.
Lower-tier errors in K, case-weighted over patterns, mean over seeds. Paired two-sided
sign-flip test over seeds (p = 0.008 is the minimum possible with 8 seeds, i.e. the same
sign in every seed). Scripts: `aggregate_seeds.py`, `aggregate_residual_seeds.py`;
CSVs in `results/seed_comparison/` and `results/residual_seed_comparison/`.

Data-only `fno_mlp` vs `fno_kan` (`power_{orig,hard,ext}_seed*`):

| Test | Metric | `fno_mlp` | `fno_kan` | KAN wins | p |
|---|---|---|---|---|---|
| In-range | MAE | 0.0183 | 0.0201 | 1/8 | 0.18 |
| In-range | peak | 0.0498 | 0.0521 | 2/8 | 0.20 |
| Hard | MAE | 0.0620 | 0.0699 | 0/8 | 0.008 |
| Hard | peak | 0.1327 | 0.1543 | 0/8 | 0.008 |
| 60 mW extrapolation | MAE | 0.1883 | 0.1924 | 2/8 | 0.23 |
| 60 mW extrapolation | peak | 0.4902 | 0.5184 | 0/8 | 0.008 |

Residual (heat-balance, weight 1, fixed spreader; `fixed_w1_*_seed*`), PINO-style
(`fno_mlp` + residual) vs PIKAN-style (`fno_kan` + residual):

| Test | Metric | PINO | PIKAN | PIKAN wins | p |
|---|---|---|---|---|---|
| In-range | MAE | 0.0198 | 0.0207 | 2/8 | 0.57 |
| In-range | peak | 0.0494 | 0.0532 | 2/8 | 0.18 |
| Hard | MAE | 0.0637 | 0.0656 | 1/8 | 0.125 |
| Hard | peak | 0.1383 | 0.1401 | 2/8 | 0.67 |
| 60 mW extrapolation | MAE | 0.1893 | 0.1841 | 8/8 | 0.008 |
| 60 mW extrapolation | peak | 0.5046 | 0.4799 | 8/8 | 0.008 |

Residual vs the same model data-only:

- `fno_kan`: 60 mW peak 0.518 -> 0.480 K (8/8 seeds, p = 0.008); 60 mW MAE
  0.192 -> 0.184 K (8/8); hard peak 0.154 -> 0.140 K (7/8, p = 0.031). In-range unchanged.
- `fno_mlp`: no gain; 60 mW peak 0.490 -> 0.505 K (p = 0.07), hard peak 0.133 -> 0.138 K.

Findings:

- Data-only: `fno_mlp` is slightly better than `fno_kan` on the hard sets and on 60 mW
  peak error (about 10-15%, all 8 seeds); they tie in-range and on 60 mW MAE.
- With the residual, PIKAN-style beats PINO-style on 60 mW extrapolation (all 8 seeds,
  about 5% lower peak error); the other sets tie. The cause is that the residual helps
  `fno_kan` and does not help `fno_mlp`.
- Neither physics-informed model is more accurate than HotSpot (the reference); the
  comparison is surrogate against surrogate.
- Caveats: effects are small; test sets are small (4-8 cases per pattern) and the hard
  and 60 mW sets reuse the same trained models; weight 1 and the fixed spreader were
  chosen after seeing seed-7 results (seed 7 is one of the 8; seeds 11-79 are unselected);
  `fno_mlp` was not tuned separately for the residual; per-pattern p-values are
  uncorrected for multiple comparisons.
- A model linear in power was also tried (seed 7). HotSpot's temperature rise is linear
  in power to 0.001 K mean (0.003 K worst) on the 10/20/30 mW single-hotspot cases, but
  the scaled models were no better than data-only, so power scaling is not the cause of
  the extrapolation error. Not kept as part of the pipeline.

## Summary of version 2 (closed)

Status: complete. Negative results for the extrapolation goal; the 8-seed comparison in
Step 3 gives the PINO-vs-PIKAN result.

- Adding 40/50 mW training cases did not fix 40 mW errors; 60 mW extrapolation stays
  2.5-4x better than `train_mean` but off by 0.11-0.27 K (peaks low by 0.3-0.8 K).
- More Fourier modes, longer training and a wider model (single seed) did not help
  extrapolation; longer or larger training made 60 mW worse.
- A 3D heat-balance residual is physically valid (HotSpot's labels satisfy it to 2-5% per
  8x8 block, and energy is conserved), but as a training loss, with the spreader
  predicted or fixed, it lowered the model's own residual about 8x without improving
  temperature error. Weight 10 hurt.
- Single-seed results stayed within seed spread; the 8-seed Step 3 settles it: data-only
  `fno_mlp` is slightly better, while with the residual `fno_kan` (PIKAN-style) beats
  `fno_mlp` (PINO-style) on 60 mW extrapolation.
- Caveats: the test sets are small; labels are quantized to 0.01 K.

Scripts: `generate_power_dataset.py`, `check_heat_balance.py`,
`train_residual_models.py`, `evaluate_residual_models.py`, `aggregate_seeds.py`,
`aggregate_residual_seeds.py` (plus the width/modes options added to the `phase3d/`
trainers). Datasets, checkpoints and results are generated
artifacts and are not committed.

## Rules

- Keep Phase 2, Phase 3, and `phase3d/` artifacts unchanged.
- Never overwrite datasets or checkpoints; use new directories.
- Use the same seeds (7, 11, 23, plus 31, 41, 53, 67, 79 for Step 3) and the same test sets for comparisons.
- Report the 0.01 K label floor and the small test sets with every result.
