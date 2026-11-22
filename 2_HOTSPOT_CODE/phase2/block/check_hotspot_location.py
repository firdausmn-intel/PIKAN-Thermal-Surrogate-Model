from pathlib import Path

path = Path("outputs/block.grid.steady")
layer = None
layers = {}
for raw_line in path.read_text().splitlines():
    line = raw_line.strip()
    if not line:
        continue
    if line.startswith("Layer") and line.endswith(":"):
        layer = int(line[6:-1])
        layers[layer] = []
    else:
        layers[layer].append(float(line.split()[1]))

rows, cols = 256, 1024
values = layers[0]
grid = [values[row * cols:(row + 1) * cols] for row in range(rows)]

col_max = [max(grid[row][col] for row in range(rows)) for col in range(cols)]
peak_col = col_max.index(max(col_max))
print(f"peak_col={peak_col} of {cols} (cell width in cols = {cols // 8})")
print(f"col 0 max={col_max[0]:.4f} col {cols//8} max={col_max[cols // 8]:.4f} "
      f"col {cols // 2} max={col_max[cols // 2]:.4f} col {cols-1} max={col_max[cols-1]:.4f}")
