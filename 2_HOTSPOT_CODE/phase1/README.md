# Phase 1: Synthetic thermal ground truth

This harness creates the Phase 1 dataset described in the research plan:

- chip footprint: 1.0 mm x 1.0 mm;
- stack thickness: 0.55 mm;
- three powered silicon layers separated by two TIM layers;
- 0.5 mW background power and 2.0 mW hotspot power;
- 10 x 10 physical power tiles per layer, with exactly 10% set to 2.0 mW;
- steady-state 3D grid temperatures produced by HotSpot 6.0.

The default 64 x 64 profile is intended for a quick smoke test. Use 256 x
256 for the planned high-resolution experiment. The generated stack has
uniform material properties, so the runner deliberately leaves HotSpot's
`detailed_3D` mode disabled. This keeps HotSpot's multigrid steady-state solver
available; enabling `detailed_3D` forces a much slower point-iteration solver.
The exact evaluation-node count should be reported from the selected HotSpot
grid configuration rather than assumed.

The physical power-tile count is deliberately separate from the temperature
grid resolution. HotSpot reads each power trace as one line with a fixed input
buffer, so using one named block per grid cell overflows the parser. The
default 10 x 10 power map keeps the trace well within that limit while the
64 x 64 or 256 x 256 grid retains the desired FDM label resolution.

## Build HotSpot in WSL

From an elevated Windows setup or a WSL terminal with sudo access, install
the compiler and Make package once:

```sh
sudo zypper --non-interactive install -y gcc make
```

Then build and run the smoke test:

```sh
cd /mnt/c/Users/PidotKing/Downloads/Research/HotSpot
make -j2
bash phase1/run_phase1.sh
```

For the high-resolution Phase 1 dataset run:

```sh
ROWS=256 COLS=256 bash phase1/run_phase1.sh
```

To alter the physical power-map resolution without altering label resolution:

```sh
POWER_ROWS=10 POWER_COLS=10 bash phase1/run_phase1.sh
```

Outputs are written under `phase1/generated/outputs/`:

- `phase1.grid.steady`: per-grid-cell steady-state temperatures;
- `phase1.steady`: HotSpot's steady-state block temperatures.

Both `.steady` files are plain-text, tab-separated HotSpot output files. Open
them in VS Code to inspect the numeric data. To make layer heatmaps and a
combined overview PNG, run the standard-library visualizer:

```sh
cd /mnt/c/Users/PidotKing/Downloads/Research/HotSpot
python3 phase1/visualize_phase1.py \
	--input phase1/generated/outputs/phase1.grid.steady \
	--output phase1/generated/plots
```

Open `phase1/generated/plots/phase1_overview.png` in VS Code or Windows File
Explorer. The visualizer uses a shared temperature scale across all layers;
individual PNGs are also written as `phase1_layer_<number>.png`.
For research figures, use `phase1_active_silicon_overview.png`, which contains
only the three powered silicon layers: 0, 2, and 4. The seven-panel overview
also includes TIM and package layers and is not a 3D perspective rendering.
For the shape of the hotspot itself, use
`phase1_active_silicon_contrast_overview.png`. It applies an independent
colour scale to each powered layer, so the curved contours remain visible.
The global-scale active overview is the correct figure for comparing absolute
temperatures between layers.
The matching minimum and maximum temperatures are recorded in
`phase1/generated/plots/temperature_range.txt`.
Files ending in `_contrast.png` use an independent colour scale for each layer,
making small within-layer hotspot differences easier to inspect. The overview
panel order and per-layer ranges are listed in `overview_layout.txt`.
The visualizer detects square grid dimensions directly from the output file.

The generated inputs and outputs are reproducible. Do not commit generated
outputs until the experiment configuration has been reviewed and frozen.