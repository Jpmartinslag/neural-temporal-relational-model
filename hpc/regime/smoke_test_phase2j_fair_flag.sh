#!/bin/bash
# Smoke test for Phase 2J fair flag comparison.
# Runs 2 configs with SEED=0 EPOCHS=1 MASK_WARMUP=0.
# Verifies JSON, CSV total, CSV sector and metadata for each config.
# Validates that the no-flags variant has no manual flags in metadata,
# and that the flags variant has manual flags in metadata.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2j_fair_flag_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

echo "========================================================"
echo " HERALD Phase 2J — fair flag comparison smoke test"
echo " out_smoke : $OUT_SMOKE"
echo " panel     : $PANEL_PATH"
echo " device    : $DEVICE"
echo "========================================================"

if [ -d "$OUT_SMOKE" ]; then
  echo "ERROR: OUT_SMOKE already exists: $OUT_SMOKE" >&2
  echo "       Set STAMP or OUT_SMOKE to a new value to avoid overwriting." >&2
  exit 1
fi
mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

"$PYTHON" -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/audit_herald_phase2j_fair_flag.py
echo "py_compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "MISSING input: $f" >&2; exit 1; }
done
echo "input files OK"

"$PYTHON" hpc/regime/audit_herald_phase2j_fair_flag.py
echo "preflight audit OK"

common_args() {
  local label=$1
  local variant=$2
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
    --v7-variant "$variant" \
    --feature-mask-ratio 0.10 \
    --sector-mask-ratio 0.30 \
    --smooth-lambda 0.01 \
    --gate-entropy-lambda 0.001 \
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

echo ""
echo "--- smoke lag1_growth1y_nf (no_regime, learned_regime_gate_sector_enhanced) ---"
"$PYTHON" src/modeles/train_herald_regime_experiment.py \
  --regime-mode no_regime \
  --experiment-label lag1_growth1y_nf \
  --feature-policy side5_lag1_growth1y \
  --macro-feature-set none \
  --drop-source-flags \
  --regime-metadata-path "${OUT_SMOKE}/metadata/lag1_growth1y_nf.json" \
  $(common_args "lag1_growth1y_nf" "learned_regime_gate_sector_enhanced") \
  --sector-lambda 0.2 \
  --alpha-smooth-lambda 0.001

for f in \
  "${OUT_SMOKE}/reports/per_run/lag1_growth1y_nf.json" \
  "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_total_full_smoke_lag1_growth1y_nf_seed_0_v1.csv" \
  "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_sector_full_smoke_lag1_growth1y_nf_seed_0_v1.csv" \
  "${OUT_SMOKE}/metadata/lag1_growth1y_nf.json"; do
  [ -f "$f" ] || { echo "MISSING artifact: $f" >&2; exit 1; }
  echo "  OK: $f"
done

echo ""
echo "--- smoke lag1_growth1y_flags (manual_flags, full) ---"
"$PYTHON" src/modeles/train_herald_regime_experiment.py \
  --regime-mode manual_flags \
  --experiment-label lag1_growth1y_flags \
  --feature-policy side5_lag1_growth1y \
  --macro-feature-set none \
  --drop-source-flags \
  --regime-metadata-path "${OUT_SMOKE}/metadata/lag1_growth1y_flags.json" \
  $(common_args "lag1_growth1y_flags" "full") \
  --sector-lambda 0.1 \
  --alpha-smooth-lambda 0.001 \
  --smooth-regime-source explicit

for f in \
  "${OUT_SMOKE}/reports/per_run/lag1_growth1y_flags.json" \
  "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_total_full_smoke_lag1_growth1y_flags_seed_0_v1.csv" \
  "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_sector_full_smoke_lag1_growth1y_flags_seed_0_v1.csv" \
  "${OUT_SMOKE}/metadata/lag1_growth1y_flags.json"; do
  [ -f "$f" ] || { echo "MISSING artifact: $f" >&2; exit 1; }
  echo "  OK: $f"
done

echo ""
echo "Verifying metadata constraints..."
"$PYTHON" - <<PY
import json, sys
from pathlib import Path

out = Path("${OUT_SMOKE}")
SIDE5_ALL = {"side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"}
SIDE2 = {"side_lag_1", "growth_1y"}
SOURCE_FLAGS = {"has_flores_source", "has_side_stock_source", "has_urssaf_source"}

errors = []

# --- lag1_growth1y_nf ---
meta = json.loads((out / "metadata" / "lag1_growth1y_nf.json").read_text())
side5_actual = set(meta["annual_features"]) & SIDE5_ALL
ridge_actual = set(meta.get("ridge_features", [])) & SIDE5_ALL
source_actual = set(meta["annual_features"]) & SOURCE_FLAGS

if side5_actual != SIDE2:
    errors.append(f"lag1_growth1y_nf: SIDE features={sorted(side5_actual)}, expected={sorted(SIDE2)}")
if ridge_actual != SIDE2:
    errors.append(f"lag1_growth1y_nf: Ridge SIDE features={sorted(ridge_actual)}, expected={sorted(SIDE2)}")
if meta["manual_flags_in_annual_features"]:
    errors.append("lag1_growth1y_nf: manual_flags_in_annual_features must be False")
if meta["manual_flags_in_regime_vector"]:
    errors.append("lag1_growth1y_nf: manual_flags_in_regime_vector must be False")
if meta["source_flags_in_annual_features"]:
    errors.append("lag1_growth1y_nf: source_flags_in_annual_features must be False")
if source_actual:
    errors.append(f"lag1_growth1y_nf: source flags in features: {sorted(source_actual)}")
print(f"  lag1_growth1y_nf : side5={sorted(side5_actual)} ridge={sorted(ridge_actual)} "
      f"manual_flags={meta['manual_flags_in_annual_features']} "
      f"source_flags={meta['source_flags_in_annual_features']}")

# --- lag1_growth1y_flags ---
meta = json.loads((out / "metadata" / "lag1_growth1y_flags.json").read_text())
side5_actual = set(meta["annual_features"]) & SIDE5_ALL
ridge_actual = set(meta.get("ridge_features", [])) & SIDE5_ALL
source_actual = set(meta["annual_features"]) & SOURCE_FLAGS

if side5_actual != SIDE2:
    errors.append(f"lag1_growth1y_flags: SIDE features={sorted(side5_actual)}, expected={sorted(SIDE2)}")
if ridge_actual != SIDE2:
    errors.append(f"lag1_growth1y_flags: Ridge SIDE features={sorted(ridge_actual)}, expected={sorted(SIDE2)}")
if not meta["manual_flags_in_annual_features"]:
    errors.append("lag1_growth1y_flags: manual_flags_in_annual_features must be True")
if not meta["manual_flags_in_regime_vector"]:
    errors.append("lag1_growth1y_flags: manual_flags_in_regime_vector must be True")
if meta["source_flags_in_annual_features"]:
    errors.append("lag1_growth1y_flags: source_flags_in_annual_features must be False")
if source_actual:
    errors.append(f"lag1_growth1y_flags: source flags in features: {sorted(source_actual)}")
print(f"  lag1_growth1y_flags: side5={sorted(side5_actual)} ridge={sorted(ridge_actual)} "
      f"manual_flags={meta['manual_flags_in_annual_features']} "
      f"source_flags={meta['source_flags_in_annual_features']}")

if errors:
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
print("metadata constraints OK — inputs are comparable and clean")
PY

echo ""
echo "Smoke completed: ${OUT_SMOKE}"
