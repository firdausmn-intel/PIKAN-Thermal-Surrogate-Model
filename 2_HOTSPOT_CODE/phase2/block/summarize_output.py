from pathlib import Path

path = Path("outputs/block.grid.steady")
layer = None
temps = {}
for raw_line in path.read_text().splitlines():
    line = raw_line.strip()
    if not line:
        continue
    if line.startswith("Layer") and line.endswith(":"):
        layer = int(line[6:-1])
        temps[layer] = []
    else:
        temps[layer].append(float(line.split()[1]))

for layer_number, values in temps.items():
    print(
        f"layer={layer_number} min={min(values):.9f} "
        f"max={max(values):.9f} n={len(values)}"
    )
