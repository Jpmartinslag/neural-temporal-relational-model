#!/bin/bash
# Smoke test for Phase 2I SIDE5 feature audit.
# Runs all 9 configs with SEED=0 EPOCHS=1 MASK_WARMUP=0.
# Verifies JSON, CSV total, CSV sector and metadata for each config.
# Fails if any expected artifact is missing or metadata constraints are violated.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2i_side5_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

echo "========================================================"
echo " HERALD Phase 2I — SIDE5 smoke test"
echo " out_smoke : $OUT_SMOKE"
echo " panel     : $PANEL_PATH"
echo " device    : $DEVICE"
echo "========================================================"

mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

"$PYTHON" -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/audit_herald_phase2i_side5_plan.py
echo "py_compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "MISSING input: $f" >&2; exit 1; }
done
echo "input files OK"

common_args() {
  local label=$1
  echo \
    --panel-path "$PANEL_PATH" \
    --splits-path "$SPLITS_PATH" \
    --side-a10-path "$SIDE_A10_PATH" \
    --prediction-output-dir "${OUT_SMOKE}/data_processed" \
    --metrics-path "${OUT_SMOKE}/reports/per_run/${label}.json" \
    --model-card-path "${OUT_SMOKE}/reports/per_run/${label}.md" \
    --epochs 1 \
    --hidden-dim 16 \
    --q-hidden 8 \
    --attn-dim 8 \
    --top-k 5 \
    --mode full \
    --v7-variant learned_regime_gate_sector_enhanced \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --sector-lambda 0.2 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
    --alpha-smooth-lambda 0.001 \
    --rank-lambda 0.02 \
    --lr 0.001 \
    --huber-delta 300 \
    --gate-bias-init 2.0 \
    --alpha-bias-init 0.0 \
    --semi-warmup-epochs 0 \
    --device "$DEVICE" \
    --seed 0 \
    --single-target-year 2021 \
    --run-tag "smoke_${label}"
}

run_one() {
  local label=$1
  local feature_policy=$2
  echo ""
  echo "--- smoke ${label} feature_policy=${feature_policy} ---"
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode no_regime \
    --experiment-label "$label" \
    --feature-policy "$feature_policy" \
    --macro-feature-set none \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label")
  for f in \
    "${OUT_SMOKE}/reports/per_run/${label}.json" \
    "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_total_full_smoke_${label}_seed_0_v1.csv" \
    "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_sector_full_smoke_${label}_seed_0_v1.csv" \
    "${OUT_SMOKE}/metadata/${label}.json"; do
    [ -f "$f" ] || { echo "MISSING artifact: $f" >&2; exit 1; }
    echo "  OK: $f"
  done
}

run_one "side5_full"    "side5_full"
run_one "drop_lag1"     "side5_drop_lag1"
run_one "drop_lag2"     "side5_drop_lag2"
run_one "drop_lag3"     "side5_drop_lag3"
run_one "drop_growth1y" "side5_drop_growth1y"
run_one "drop_growth2y" "side5_drop_growth2y"
run_one "lags_only"     "side5_lags_only"
run_one "growth_only"   "side5_growth_only"
run_one "lag1_growth1y" "side5_lag1_growth1y"

echo ""
echo "Verifying metadata constraints..."
"$PYTHON" - <<PY
import json, sys
from pathlib import Path

out = Path("${OUT_SMOKE}")
SIDE5_ALL = {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"}

expected_by_label = {
    "side5_full":    {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag1":     {"side_lag_2", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag2":     {"side_lag_1", "side_lag_3", "growth_1y", "growth_2y"},
    "drop_lag3":     {"side_lag_1", "side_lag_2", "growth_1y", "growth_2y"},
    "drop_growth1y": {"side_lag_1", "side_lag_2", "side_lag_3", "growth_2y"},
    "drop_growth2y": {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y"},
    "lags_only":     {"side_lag_1", "side_lag_2", "side_lag_3"},
    "growth_only":   {"growth_1y", "growth_2y"},
    "lag1_growth1y": {"side_lag_1", "growth_1y"},
}

errors = []
for label, expected_side5 in expected_by_label.items():
    meta_path = out / "metadata" / f"{label}.json"
    meta = json.loads(meta_path.read_text())
    actual_side5 = set(meta["annual_features"]) & SIDE5_ALL
    ridge_side5 = set(meta.get("ridge_features", [])) & SIDE5_ALL
    if actual_side5 != expected_side5:
        errors.append(f"{label}: SIDE5 mismatch expected={sorted(expected_side5)} got={sorted(actual_side5)}")
    if ridge_side5 != expected_side5:
        errors.append(f"{label}: Ridge SIDE5 mismatch expected={sorted(expected_side5)} got={sorted(ridge_side5)}")
    if meta["manual_flags_in_annual_features"]:
        errors.append(f"{label}: manual_flags_in_annual_features is True")
    if meta["source_flags_in_annual_features"]:
        errors.append(f"{label}: source_flags_in_annual_features is True")
    dropped_in_meta = set(meta.get("dropped_side5_features", []))
    expected_dropped = SIDE5_ALL - expected_side5
    if dropped_in_meta != expected_dropped:
        errors.append(f"{label}: dropped_side5 mismatch expected={sorted(expected_dropped)} got={sorted(dropped_in_meta)}")
    ridge_dropped = set(meta.get("ridge_dropped_side5_features", []))
    if ridge_dropped != expected_dropped:
        errors.append(f"{label}: ridge_dropped_side5 mismatch expected={sorted(expected_dropped)} got={sorted(ridge_dropped)}")
    print(f"  {label}: side5_features={sorted(actual_side5)} ridge_features={sorted(ridge_side5)} dropped={sorted(dropped_in_meta)} OK")

if errors:
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
print("metadata constraints OK")
PY

echo ""
echo "Smoke completed: ${OUT_SMOKE}"
