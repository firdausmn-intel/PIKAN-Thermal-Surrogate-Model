from pathlib import Path

lines = Path("outputs/block.grid.steady").read_text().splitlines()
values = set()
layer = None
for line in lines:
    line = line.strip()
    if line.startswith("Layer") and line.endswith(":"):
        layer = int(line[6:-1])
        if layer > 0:
            break
        continue
    values.add(float(line.split()[1]))
print(sorted(values))
