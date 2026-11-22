"""Step 2 feasibility: does HotSpot's own steady-state output satisfy a 3D heat balance?

For every cell in the three stack layers (0 lower tier, 1 TIM, 2 upper tier) the
residual is  r = sum_neighbours g * (T_neighbour - T) + P  (watts), using the
layer file for materials and HotSpot's resistor rules (temperature_grid.c,
RCutil.c). Layer 3 (spreader) temperatures come from the label file and act as the
top boundary; side faces are adiabatic. Two vertical-resistance conventions are
compared, and a quantization baseline is computed by adding +-0.005 K rounding noise
to the labels. Read-only: writes nothing.
"""

import argparse
import csv
from pathlib import Path
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase3d"))
import prepare_stack_tensors as pst  # noqa: E402

pst.TARGET_LAYERS = (0, 1, 2, 3)

CHIP = 1e-3
GRID = 32
CELL = CHIP / GRID
AREA = CELL * CELL
# thickness (m), conductivity (W/mK); spreader values are HotSpot defaults.
LAYERS = [(1.5e-4, 100.0), (5e-5, 4.0), (1.5e-4, 100.0), (1e-3, 400.0)]


def vertical_conductance(n, convention):
    rz = [t / (k * AREA) for t, k in LAYERS]
    if convention == "lower_layer_rz":
        return 1.0 / rz[n]
    return 1.0 / (rz[n] / 2 + rz[n + 1] / 2)


def residual(temp, power, convention):
    """temp: (4, 32, 32) K; power: (3, 32, 32) W. Returns (3, 32, 32) W."""
    res = power.clone()
    for n in range(3):
        t, k = LAYERS[n]
        g_lat = k * t  # k * (cell * thickness) / cell
        layer = temp[n]
        d_row = layer[1:] - layer[:-1]
        d_col = layer[:, 1:] - layer[:, :-1]
        res[n][:-1] += g_lat * d_row
        res[n][1:] -= g_lat * d_row
        res[n][:, :-1] += g_lat * d_col
        res[n][:, 1:] -= g_lat * d_col
        g_up = vertical_conductance(n, convention)
        res[n] += g_up * (temp[n + 1] - temp[n])
        if n > 0:
            g_down = vertical_conductance(n - 1, convention)
            res[n] += g_down * (temp[n - 1] - temp[n])
    return res


def block_sum(x, size=8):
    return x.reshape(x.shape[0], GRID // size, size, GRID // size, size).sum(dim=(2, 4))


def rms(x):
    return float(x.pow(2).mean().sqrt())


def load_case(dataset, entry):
    label = dataset / "cases" / entry["case"] / "outputs" / "stack.grid.steady"
    temp = pst.read_layers(label).double()
    tier = [pst.make_power_grid(p).double() / (GRID // pst.POWER_ROWS) ** 2
            for p in entry["powers"]]
    power = torch.stack([tier[0], torch.zeros_like(tier[0]), tier[1]])
    return temp, power


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cases", type=int, default=12, help="cases to check")
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    entries = pst.read_manifest(dataset / "manifest.tsv")
    step = max(1, len(entries) // args.cases)
    entries = entries[::step][: args.cases]
    torch.manual_seed(0)

    for convention in ("lower_layer_rz", "half_plus_half"):
        stats = {n: [] for n in range(3)}
        for entry in entries:
            temp, power = load_case(dataset, entry)
            noisy = temp + (torch.rand_like(temp) - 0.5) * 0.01
            for n in range(3):
                r = residual(temp, power, convention)[n]
                rn = residual(noisy, power, convention)[n]
                coarse = block_sum(r.unsqueeze(0))[0]
                coarse_p = block_sum(power[n].unsqueeze(0))[0]
                stats[n].append(
                    (rms(r), rms(rn - residual(temp, power, convention)[n]),
                     rms(coarse), rms(coarse_p), float(r.sum()), float(power[n].sum()))
                )
        print(f"\nvertical convention: {convention}  ({len(entries)} cases)")
        print("layer | cell residual RMS (W) | rounding-noise RMS (W) | "
              "8x8 block residual RMS (W) | block power RMS (W) | "
              "net residual per case (W) | power per case (W)")
        for n in range(3):
            a = torch.tensor(stats[n])
            m = a.mean(dim=0)
            print(f"  {n}   | {m[0]:.2e} | {m[1]:.2e} | {m[2]:.2e} | {m[3]:.2e} | "
                  f"{m[4]:+.2e} | {m[5]:.2e}")


if __name__ == "__main__":
    main()
