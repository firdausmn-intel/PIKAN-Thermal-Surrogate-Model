"""End-to-end inference and evaluation tool for custom 3D transistor power maps.

Workflow:
1. Generates 3D standard-cell layout files for specified power map.
2. Runs HotSpot FDM solver (via WSL) for exact ground truth steady-state thermal maps.
3. Feeds power map to trained PINO and PIKAN neural operators.
4. Generates predicted thermal maps and computes error & physics metrics.
5. Produces visual PNG comparisons and JSON / text diagnostic reports.
"""

from argparse import ArgumentParser
import json
import os
from pathlib import Path
import subprocess
import sys

import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parent
PHASE2 = ROOT.parent
HOTSPOT_ROOT = PHASE2.parent
PHASE1 = HOTSPOT_ROOT / "phase1"
sys.path.insert(0, str(PHASE1))

from visualize_phase1 import temperature_color, write_png
from train_operator_models import (
    KANActivation,
    MLPActivation,
    OperatorModel,
    POWER_SCALE,
    TEMPERATURE_OFFSET,
    TEMPERATURE_SCALE,
    CELL_PITCH_X_M,
    CELL_PITCH_Y_M,
    DOMAIN_WIDTH_M,
    DOMAIN_HEIGHT_M,
    FRONT_END_CONDUCTIVITY,
    FRONT_END_THICKNESS_M,
    PHYSICS_RESIDUAL_SCALE,
)

PRESETS = {
    "single_center": [5e-8, 5e-8, 5e-8, 4.5e-4, 5e-8, 5e-8, 5e-8, 5e-8],
    "dual_hotspots": [5e-8, 4.0e-4, 5e-8, 5e-8, 3.5e-4, 5e-8, 5e-8, 5e-8],
    "edge_extreme": [5.0e-4, 5e-8, 5e-8, 5e-8, 5e-8, 5e-8, 5e-8, 4.8e-4],
    "alternating": [3.5e-4, 5e-8, 3.5e-4, 5e-8, 3.5e-4, 5e-8, 3.5e-4, 5e-8],
    "gradient_ramp": [5e-8, 1e-4, 2e-4, 3e-4, 4e-4, 5e-4, 2e-4, 5e-8],
    "congested_cluster": [5e-8, 5e-8, 4.2e-4, 4.8e-4, 4.5e-4, 5e-8, 5e-8, 5e-8],
}

ROWS = 256
COLS = 1024
CELLS = 8
SAMPLE_SIZE = 4


def read_layer_zero(path):
    values = []
    active = False
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            active = line == "Layer 0:"
            if values:
                break
            continue
        if active:
            values.append(float(line.split()[1]))
    expected = ROWS * COLS
    if len(values) != expected:
        raise ValueError(f"{path}: expected {expected}, found {len(values)}")
    return torch.tensor(values, dtype=torch.float32).reshape(1, 1, ROWS, COLS)


def make_power_grid(cell_powers):
    values = []
    cell_width = COLS // CELLS
    for column in range(COLS):
        cell = min(CELLS - 1, column // cell_width)
        values.append(cell_powers[cell])
    row = torch.tensor(values, dtype=torch.float32)
    return row.repeat(ROWS).reshape(1, 1, ROWS, COLS)


def denormalize(values):
    return values * TEMPERATURE_SCALE + TEMPERATURE_OFFSET


def compute_pde_residual(temperature_k, power_w):
    """Compute 2D steady-state heat equation residual."""
    power_density = power_w / (CELL_PITCH_X_M * CELL_PITCH_Y_M)
    _, _, height, width = temperature_k.shape
    dx = DOMAIN_WIDTH_M / width
    dy = DOMAIN_HEIGHT_M / height
    center = temperature_k[:, :, 1:-1, 1:-1]
    d2x = (temperature_k[:, :, 1:-1, 2:] - 2 * center + temperature_k[:, :, 1:-1, :-2]) / (dx * dx)
    d2y = (temperature_k[:, :, 2:, 1:-1] - 2 * center + temperature_k[:, :, :-2, 1:-1]) / (dy * dy)
    conduction = FRONT_END_CONDUCTIVITY * FRONT_END_THICKNESS_M * (d2x + d2y)
    source = power_density[:, :, 1:-1, 1:-1]
    res = (conduction + source) / PHYSICS_RESIDUAL_SCALE
    return float(res.abs().mean()), float(res.square().mean().sqrt())


def render(values, output, minimum, maximum):
    height, width = values.shape
    pixels = bytearray()
    for row in reversed(values.tolist()):
        for value in row:
            pixels.extend(temperature_color(value, minimum, maximum))
    write_png(output, pixels, width, height)


def render_comparison(images, output, minimum, maximum):
    panel_names = list(images)
    panel_height, panel_width = images[panel_names[0]].shape
    columns = len(panel_names)
    rows = 1
    gap = 4
    width = columns * panel_width + (columns - 1) * gap
    height = rows * panel_height + (rows - 1) * gap
    pixels = bytearray([255]) * (width * height * 3)
    for index, name in enumerate(panel_names):
        tile = bytearray()
        for row in reversed(images[name].tolist()):
            for value in row:
                tile.extend(temperature_color(value, minimum, maximum))
        tile_col = index
        for row in range(panel_height):
            source = row * panel_width * 3
            image_row = row
            image_col = tile_col * (panel_width + gap)
            target = (image_row * width + image_col) * 3
            pixels[target:target + panel_width * 3] = tile[source:source + panel_width * 3]
    write_png(output, pixels, width, height)


def run_hotspot(sim_dir):
    sim_dir_str = str(sim_dir.resolve()).replace("C:\\", "").replace("\\", "/")
    hotspot_str = str((HOTSPOT_ROOT / "hotspot").resolve()).replace("C:\\", "").replace("\\", "/")
    wsl_sim_dir = f"/mnt/c/{sim_dir_str}"
    wsl_hotspot = f"/mnt/c/{hotspot_str}"
    cmd = (
        f"mkdir -p {wsl_sim_dir}/outputs && "
        f"cd {wsl_sim_dir} && "
        f"{wsl_hotspot} -c block.config -p block.ptrace -grid_layer_file block.lcf "
        f"-model_type grid -grid_steady_file outputs/block.grid.steady "
        f"-steady_file outputs/block.steady > outputs/hotspot.log 2>&1"
    )
    res = subprocess.run(["wsl.exe", "-e", "bash", "-c", cmd], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"HotSpot simulation failed in WSL: {res.stderr}\n{res.stdout}")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        help="Use a predefined power map test preset",
    )
    parser.add_argument(
        "--cell-powers",
        type=float,
        nargs="+",
        help="Explicit list of 8 total power values (W) for the transistor cells",
    )
    parser.add_argument(
        "--checkpoints",
        type=Path,
        default=HOTSPOT_ROOT / "phase2" / "models" / "checkpoints_v2",
        help="Directory with pino.pt and pikan.pt model checkpoints",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HOTSPOT_ROOT / "phase2" / "dataset" / "test_inference_output",
        help="Directory to save test simulation, thermal maps, and reports",
    )
    args = parser.parse_args()

    if args.cell_powers:
        if len(args.cell_powers) != CELLS:
            raise ValueError(f"Expected {CELLS} cell power values, got {len(args.cell_powers)}")
        powers = args.cell_powers
        test_name = "custom_power_map"
    elif args.preset:
        powers = PRESETS[args.preset]
        test_name = f"preset_{args.preset}"
    else:
        powers = PRESETS["dual_hotspots"]
        test_name = "preset_dual_hotspots"

    args.output.mkdir(parents=True, exist_ok=True)
    sim_dir = args.output / "sim"
    sim_dir.mkdir(parents=True, exist_ok=True)

    print(f"=======================================================")
    print(f"=== 3D Transistor Thermal Simulation & AI Inference ===")
    print(f"=======================================================")
    print(f"Test case: {test_name}")
    print(f"Per-cell powers (W): {[f'{p:.2e}' for p in powers]}")
    print(f"Total block power: {sum(powers):.4e} W")
    print(f"Checkpoints directory: {args.checkpoints}")
    print(f"Output directory: {args.output}\n")

    # Step 1: Build block geometry and power files
    print("[1/5] Generating 3D transistor layout and power trace...")
    build_cmd = [
        sys.executable,
        str(HOTSPOT_ROOT / "phase2" / "block" / "build_block.py"),
        "--cell-powers", *[str(p) for p in powers],
        "--output", str(sim_dir),
    ]
    subprocess.run(build_cmd, check=True)

    # Step 2: Run HotSpot FDM Ground Truth
    print("[2/5] Running HotSpot 3D multi-grid FDM numerical solver...")
    run_hotspot(sim_dir)
    print("      -> HotSpot FDM steady-state solve finished successfully.")

    # Step 3: Load ground truth and prepare power tensors
    print("[3/5] Loading FDM ground truth & preparing neural operator tensors...")
    truth_grid = read_layer_zero(sim_dir / "outputs" / "block.grid.steady")
    power_grid = make_power_grid(powers)

    # Pool by sample size (4x4) matching operator resolution
    power_in = F.avg_pool2d(power_grid, SAMPLE_SIZE) / POWER_SCALE
    truth_in = F.avg_pool2d(truth_grid, SAMPLE_SIZE)
    physical_power_pooled = F.avg_pool2d(power_grid, SAMPLE_SIZE)

    # Step 4: Run AI model inference (PINO and PIKAN)
    print("[4/5] Running inference on PINO (MLP) and PIKAN (KAN) operators...")
    models = {}
    predictions = {}
    for name, activation in (("pino", MLPActivation), ("pikan", KANActivation)):
        model = OperatorModel(activation)
        ckpt_path = args.checkpoints / f"{name}.pt"
        if not ckpt_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")
        model.load_state_dict(torch.load(ckpt_path, map_location="cpu", weights_only=True))
        model.eval()
        with torch.no_grad():
            pred_norm = model(power_in)
            pred_k = denormalize(pred_norm)
            predictions[name] = pred_k
        models[name] = model

    # Step 5: Calculate quantitative evaluation metrics
    print("[5/5] Computing accuracy metrics and generating thermal heatmaps...")
    truth_k = truth_in.squeeze()
    pino_k = predictions["pino"].squeeze()
    pikan_k = predictions["pikan"].squeeze()

    pino_err = (pino_k - truth_k).abs()
    pikan_err = (pikan_k - truth_k).abs()

    pino_mae = float(pino_err.mean())
    pikan_mae = float(pikan_err.mean())

    pino_rmse = float((pino_k - truth_k).square().mean().sqrt())
    pikan_rmse = float((pikan_k - truth_k).square().mean().sqrt())

    truth_max = float(truth_k.max())
    truth_min = float(truth_k.min())
    pino_max = float(pino_k.max())
    pikan_max = float(pikan_k.max())

    pino_peak_err = abs(pino_max - truth_max)
    pikan_peak_err = abs(pikan_max - truth_max)

    pino_res_mean, pino_res_rms = compute_pde_residual(predictions["pino"], physical_power_pooled)
    pikan_res_mean, pikan_res_rms = compute_pde_residual(predictions["pikan"], physical_power_pooled)
    truth_res_mean, truth_res_rms = compute_pde_residual(truth_in, physical_power_pooled)

    # Render PNGs
    t_min = min(truth_min, float(pino_k.min()), float(pikan_k.min()))
    t_max = max(truth_max, pino_max, pikan_max)
    err_max = max(float(pino_err.max()), float(pikan_err.max()), 1e-4)

    render(truth_k, args.output / "hotspot_ground_truth.png", t_min, t_max)
    render(pino_k, args.output / "pino_prediction.png", t_min, t_max)
    render(pikan_k, args.output / "pikan_prediction.png", t_min, t_max)
    render(pino_err, args.output / "pino_absolute_error.png", 0.0, err_max)
    render(pikan_err, args.output / "pikan_absolute_error.png", 0.0, err_max)

    render_comparison(
        {"HotSpot (FDM)": truth_k, "PINO (MLP)": pino_k, "PIKAN (KAN)": pikan_k},
        args.output / "prediction_comparison.png",
        t_min,
        t_max,
    )
    render_comparison(
        {"PINO Error": pino_err, "PIKAN Error": pikan_err},
        args.output / "error_comparison.png",
        0.0,
        err_max,
    )

    metrics = {
        "test_name": test_name,
        "cell_powers_w": powers,
        "total_power_w": sum(powers),
        "ground_truth_hotspot": {
            "min_temp_k": truth_min,
            "max_temp_k": truth_max,
            "temp_delta_k": truth_max - truth_min,
            "pde_residual_mean": truth_res_mean,
            "pde_residual_rms": truth_res_rms,
        },
        "pino_mlp": {
            "min_temp_k": float(pino_k.min()),
            "max_temp_k": pino_max,
            "mae_k": pino_mae,
            "rmse_k": pino_rmse,
            "peak_error_k": pino_peak_err,
            "max_pointwise_error_k": float(pino_err.max()),
            "pde_residual_mean": pino_res_mean,
            "pde_residual_rms": pino_res_rms,
        },
        "pikan_kan": {
            "min_temp_k": float(pikan_k.min()),
            "max_temp_k": pikan_max,
            "mae_k": pikan_mae,
            "rmse_k": pikan_rmse,
            "peak_error_k": pikan_peak_err,
            "max_pointwise_error_k": float(pikan_err.max()),
            "pde_residual_mean": pikan_res_mean,
            "pde_residual_rms": pikan_res_rms,
        },
    }

    (args.output / "metrics_report.json").write_text(json.dumps(metrics, indent=2))

    summary_text = f"""
========================================================================
                      THERMAL MAP EVALUATION REPORT
========================================================================
Test Scenario:      {test_name}
Total Power:        {sum(powers):.4e} W
Domain Dimensions:  8 abutted SKY130 inverter cells (11.04 um x 3.20 um)
Grid Resolution:    {ROWS}x{COLS} -> pooled {ROWS // SAMPLE_SIZE}x{COLS // SAMPLE_SIZE}

--- GROUND TRUTH (HotSpot 3D FDM) ---
Min Temperature:    {truth_min:.4f} K
Peak Temperature:   {truth_max:.4f} K
Thermal Gradient:   {truth_max - truth_min:.4f} K

--- PINO OPERATOR (MLP Trunk) ---
Peak Prediction:    {pino_max:.4f} K
Peak Error:         {pino_peak_err:.4f} K
MAE:                {pino_mae:.4f} K
RMSE:               {pino_rmse:.4f} K
Max Point Error:    {float(pino_err.max()):.4f} K
PDE Residual (RMS): {pino_res_rms:.4f}

--- PIKAN OPERATOR (KAN Trunk) ---
Peak Prediction:    {pikan_max:.4f} K
Peak Error:         {pikan_peak_err:.4f} K
MAE:                {pikan_mae:.4f} K
RMSE:               {pikan_rmse:.4f} K
Max Point Error:    {float(pikan_err.max()):.4f} K
PDE Residual (RMS): {pikan_res_rms:.4f}

--- COMPARATIVE SUMMARY ---
MAE Winner:         {'PIKAN' if pikan_mae < pino_mae else 'PINO'} (Difference: {abs(pikan_mae - pino_mae):.4f} K)
Peak Error Winner:  {'PIKAN' if pikan_peak_err < pino_peak_err else 'PINO'} (Difference: {abs(pikan_peak_err - pino_peak_err):.4f} K)
PDE Physics Winner: {'PIKAN' if pikan_res_rms < pino_res_rms else 'PINO'} (Difference: {abs(pikan_res_rms - pino_res_rms):.4f})
========================================================================
Artifacts saved to: {args.output}
  - hotspot_ground_truth.png
  - pino_prediction.png
  - pikan_prediction.png
  - pino_absolute_error.png
  - pikan_absolute_error.png
  - prediction_comparison.png
  - error_comparison.png
  - metrics_report.json
========================================================================
"""
    (args.output / "report.txt").write_text(summary_text)
    print(summary_text)


if __name__ == "__main__":
    main()
