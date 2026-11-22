#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CASE_DIR="$ROOT_DIR/phase1/generated"
ROWS=${ROWS:-64}
COLS=${COLS:-64}
POWER_ROWS=${POWER_ROWS:-10}
POWER_COLS=${POWER_COLS:-10}

python3 "$ROOT_DIR/phase1/generate_phase1.py" \
  --rows "$ROWS" --cols "$COLS" \
  --power-rows "$POWER_ROWS" --power-cols "$POWER_COLS" \
  --output "$CASE_DIR"
mkdir -p "$CASE_DIR/outputs"
rm -f "$CASE_DIR"/outputs/*

cd "$CASE_DIR"
"$ROOT_DIR/hotspot" \
  -c "$CASE_DIR/phase1.config" \
  -p "$CASE_DIR/phase1.ptrace" \
  -grid_layer_file "$CASE_DIR/phase1.lcf" \
  -model_type grid \
  -grid_steady_file "$CASE_DIR/outputs/phase1.grid.steady" \
  -steady_file "$CASE_DIR/outputs/phase1.steady"

echo "Phase 1 ground truth written to $CASE_DIR/outputs"