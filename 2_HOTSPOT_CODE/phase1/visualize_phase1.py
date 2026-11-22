"""Render HotSpot grid steady-state output as per-layer PNG heatmaps."""

from argparse import ArgumentParser
from pathlib import Path
from struct import pack
from zlib import compress, crc32


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("generated/outputs/phase1.grid.steady"),
    )
    parser.add_argument("--rows", type=int)
    parser.add_argument("--cols", type=int)
    parser.add_argument("--output", type=Path, default=Path("generated/plots"))
    return parser.parse_args()


def read_layers(path, expected_values):
    layers = {}
    current_layer = None
    current_values = []

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Layer ") and line.endswith(":"):
            if current_layer is not None:
                if (
                    expected_values is not None
                    and len(current_values) != expected_values
                ):
                    raise ValueError(
                        f"Layer {current_layer} has {len(current_values)} values; "
                        f"expected {expected_values}."
                    )
                layers[current_layer] = current_values
            current_layer = int(line[len("Layer "):-1])
            current_values = []
            continue
        if current_layer is None:
            raise ValueError("Expected a 'Layer N:' header before temperatures.")
        _, temperature = line.split(maxsplit=1)
        current_values.append(float(temperature))

    if current_layer is not None:
        if (
            expected_values is not None
            and len(current_values) != expected_values
        ):
            raise ValueError(
                f"Layer {current_layer} has {len(current_values)} values; "
                f"expected {expected_values}."
            )
        layers[current_layer] = current_values

    if not layers:
        raise ValueError("No layer temperatures were found.")
    return layers


def png_chunk(kind, data):
    checksum = pack(">I", crc32(kind + data) & 0xFFFFFFFF)
    return pack(">I", len(data)) + kind + data + checksum


def write_png(path, pixels, width, height):
    raw_rows = []
    for row in range(height):
        start = row * width * 3
        raw_rows.append(b"\x00" + bytes(pixels[start:start + width * 3]))
    header = pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", header)
    png += png_chunk(b"IDAT", compress(b"".join(raw_rows), level=9))
    png += png_chunk(b"IEND", b"")
    path.write_bytes(png)


def temperature_color(temperature, minimum, maximum):
    if maximum == minimum:
        fraction = 0.5
    else:
        fraction = (temperature - minimum) / (maximum - minimum)
    fraction = min(1.0, max(0.0, fraction))
    stops = (
        (0.0, (0, 0, 4)),
        (0.25, (87, 15, 109)),
        (0.5, (187, 55, 84)),
        (0.75, (249, 142, 8)),
        (1.0, (252, 255, 164)),
    )
    for (left, start), (right, end) in zip(stops, stops[1:]):
        if fraction <= right:
            ratio = (fraction - left) / (right - left)
            return tuple(
                round(start[index] + ratio * (end[index] - start[index]))
                for index in range(3)
            )
    return stops[-1][1]


def layer_pixels(temperatures, minimum, maximum):
    pixels = bytearray()
    for temperature in reversed(temperatures):
        pixels.extend(temperature_color(temperature, minimum, maximum))
    return pixels


def render_layer(layer, temperatures, output, rows, cols, minimum, maximum):
    pixels = layer_pixels(temperatures, minimum, maximum)
    write_png(output / f"phase1_layer_{layer}.png", pixels, cols, rows)
    local_minimum = min(temperatures)
    local_maximum = max(temperatures)
    contrast_pixels = layer_pixels(temperatures, local_minimum, local_maximum)
    write_png(
        output / f"phase1_layer_{layer}_contrast.png",
        contrast_pixels,
        cols,
        rows,
    )


def render_overview(
    layers,
    output,
    rows,
    cols,
    minimum,
    maximum,
    filename,
    local_contrast=False,
):
    layer_items = list(layers.items())
    columns = min(3, len(layer_items))
    layer_rows = (len(layer_items) + columns - 1) // columns
    gap = 4
    width = columns * cols + (columns - 1) * gap
    height = layer_rows * rows + (layer_rows - 1) * gap
    pixels = bytearray([255]) * (width * height * 3)
    for index, (_, temperatures) in enumerate(layer_items):
        tile_row, tile_col = divmod(index, columns)
        tile_minimum = min(temperatures) if local_contrast else minimum
        tile_maximum = max(temperatures) if local_contrast else maximum
        tile = layer_pixels(temperatures, tile_minimum, tile_maximum)
        for row in range(rows):
            source = row * cols * 3
            image_row = tile_row * (rows + gap) + row
            image_col = tile_col * (cols + gap)
            target = (image_row * width + image_col) * 3
            pixels[target:target + cols * 3] = tile[source:source + cols * 3]
    write_png(output / filename, pixels, width, height)


def main():
    args = parse_args()
    if (args.rows is None) != (args.cols is None):
        raise ValueError("specify both rows and cols, or neither")
    if args.rows is not None and (args.rows < 1 or args.cols < 1):
        raise ValueError("rows and cols must be positive")
    expected_values = None
    if args.rows is not None:
        expected_values = args.rows * args.cols
    layers = read_layers(args.input, expected_values)
    if args.rows is None:
        inferred_size = int(len(next(iter(layers.values()))) ** 0.5)
        if inferred_size * inferred_size != len(next(iter(layers.values()))):
            raise ValueError("grid is not square; specify --rows and --cols")
        args.rows = inferred_size
        args.cols = inferred_size
    temperatures = [value for layer in layers.values() for value in layer]
    minimum = min(temperatures)
    maximum = max(temperatures)
    args.output.mkdir(parents=True, exist_ok=True)
    for layer, layer_temperatures in layers.items():
        render_layer(
            layer,
            layer_temperatures,
            args.output,
            args.rows,
            args.cols,
            minimum,
            maximum,
        )
    render_overview(
        layers,
        args.output,
        args.rows,
        args.cols,
        minimum,
        maximum,
        "phase1_overview.png",
    )
    active_layers = {
        layer: layers[layer] for layer in (0, 2, 4) if layer in layers
    }
    render_overview(
        active_layers,
        args.output,
        args.rows,
        args.cols,
        minimum,
        maximum,
        "phase1_active_silicon_overview.png",
    )
    render_overview(
        active_layers,
        args.output,
        args.rows,
        args.cols,
        minimum,
        maximum,
        "phase1_active_silicon_contrast_overview.png",
        local_contrast=True,
    )
    (args.output / "temperature_range.txt").write_text(
        f"minimum_kelvin={minimum:.2f}\nmaximum_kelvin={maximum:.2f}\n"
    )
    with (args.output / "overview_layout.txt").open("w") as file:
        for index, (layer, temperatures) in enumerate(layers.items()):
            row, col = divmod(index, 3)
            file.write(
                f"row={row} col={col} layer={layer} "
                f"minimum_kelvin={min(temperatures):.2f} "
                f"maximum_kelvin={max(temperatures):.2f}\n"
            )
    print(f"Rendered {len(layers)} layers with range {minimum:.2f}-{maximum:.2f} K.")


if __name__ == "__main__":
    main()