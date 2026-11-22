"""Inspect a GDSII cell: list layers present and the cell's bounding box."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gds_parser import parse_gds, flatten_top_structure, polygon_bounds


def main():
    gds_path = Path(sys.argv[1])
    structures, units_per_micron = parse_gds(gds_path)

    top_candidates = [name for name in structures if name and "inv" in name.lower()]
    top_name = top_candidates[0] if top_candidates else next(iter(structures))

    all_layers = set()
    for elements in structures.values():
        for element in elements:
            if element["kind"] in ("boundary", "box"):
                all_layers.add((element["layer"], element["datatype"]))

    flattened = flatten_top_structure(structures, top_name, all_layers)
    min_x, min_y, max_x, max_y = polygon_bounds(flattened)

    print(f"units_per_micron={units_per_micron}")
    print(f"structures={list(structures.keys())}")
    print(f"top_structure={top_name}")
    print(f"bounding_box_microns=({min_x / units_per_micron:.4f}, "
          f"{min_y / units_per_micron:.4f}) to "
          f"({max_x / units_per_micron:.4f}, {max_y / units_per_micron:.4f})")
    print("layers_present (layer, datatype, polygon_count):")
    for layer_key in sorted(flattened):
        print(f"  {layer_key}: {len(flattened[layer_key])} polygons")


if __name__ == "__main__":
    main()
