#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
DATASET_DIR=${DATASET_DIR:-"$ROOT_DIR/phase2/dataset/generated"}
CELLS=${CELLS:-8}
GRID_CASES=${GRID_CASES:-10}

rm -rf "$DATASET_DIR"
mkdir -p "$DATASET_DIR/cases"

manifest="$DATASET_DIR/manifest.tsv"
printf 'case\tsplit\thot_start\thot_cells\tlow_power_w\thigh_power_w\n' > "$manifest"

for case_index in $(seq 0 $((GRID_CASES - 1))); do
  case_name=$(printf 'case_%02d' "$case_index")
  case_dir="$DATASET_DIR/cases/$case_name"
  if [ "$case_index" -lt $((GRID_CASES * 80 / 100)) ]; then
    split=train
  else
    split=test
  fi
  hot_start=$((case_index % CELLS))
  low_power='5e-8'
  if [ "$case_index" -lt 5 ]; then
    high_power='5e-4'
  else
    high_power='3e-4'
  fi

  mkdir -p "$case_dir/outputs"
  python3 "$ROOT_DIR/phase2/block/build_block.py" \
    --cells "$CELLS" \
    --hot-start "$hot_start" \
    --hot-cells 1 \
    --low-power "$low_power" \
    --high-power "$high_power" \
    --output "$case_dir"

  cd "$case_dir"
  "$ROOT_DIR/hotspot" \
    -c "$case_dir/block.config" \
    -p "$case_dir/block.ptrace" \
    -grid_layer_file "$case_dir/block.lcf" \
    -model_type grid \
    -grid_steady_file "$case_dir/outputs/block.grid.steady" \
    -steady_file "$case_dir/outputs/block.steady" \
    > "$case_dir/outputs/hotspot.log" 2>&1

  printf '%s\t%s\t%s\t1\t%s\t%s\n' \
    "$case_name" "$split" "$hot_start" "$low_power" "$high_power" \
    >> "$manifest"
done

printf 'Dataset written to %s\n' "$DATASET_DIR"
printf 'Manifest: %s\n' "$manifest"
