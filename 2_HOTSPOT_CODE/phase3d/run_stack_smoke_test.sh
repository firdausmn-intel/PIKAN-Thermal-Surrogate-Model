#!/usr/bin/env bash
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
OUTPUT_DIR=${OUTPUT_DIR:-"$SCRIPT_DIR/smoke_test"}
ROWS=${ROWS:-32}
COLS=${COLS:-32}
POWER_ROWS=${POWER_ROWS:-4}
POWER_COLS=${POWER_COLS:-4}
HOT_TIER=${HOT_TIER:-0}
HOT_ROW=${HOT_ROW:-1}
HOT_COL=${HOT_COL:-1}
LOW_POWER=${LOW_POWER:-0.0005}
HIGH_POWER=${HIGH_POWER:-0.002}

python3 "$SCRIPT_DIR/generate_stack_smoke_test.py" \
  --rows "$ROWS" --cols "$COLS" \
  --power-rows "$POWER_ROWS" --power-cols "$POWER_COLS" \
  --hot-tier "$HOT_TIER" --hot-row "$HOT_ROW" --hot-col "$HOT_COL" \
  --low-power "$LOW_POWER" --high-power "$HIGH_POWER" \
  --output "$OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR/outputs"
cd "$OUTPUT_DIR"
"$REPO_ROOT/hotspot" \
  -c "$OUTPUT_DIR/stack.config" \
  -p "$OUTPUT_DIR/stack.ptrace" \
  -grid_layer_file "$OUTPUT_DIR/stack.lcf" \
  -model_type grid \
  -grid_steady_file "$OUTPUT_DIR/outputs/stack.grid.steady" \
  -steady_file "$OUTPUT_DIR/outputs/stack.steady"

python3 "$SCRIPT_DIR/summarize_stack_output.py" \
  "$OUTPUT_DIR/outputs/stack.grid.steady" \
  --rows "$ROWS" --cols "$COLS" \
  --power-rows "$POWER_ROWS" --power-cols "$POWER_COLS" \
  --hot-tier "$HOT_TIER" --hot-row "$HOT_ROW" --hot-col "$HOT_COL"

echo "Phase 3D smoke-test outputs are in $OUTPUT_DIR/outputs"
