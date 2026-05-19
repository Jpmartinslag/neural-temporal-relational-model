#!/bin/bash
# Smoke test for Phase 2K latent-regime dimension audit.
# Runs 5 configs (L1_gate, L3_gate, L5_gate, L3_both, AUTO5_l1_005) with SEED=0 EPOCHS=1.
# Validates artifacts, metadata.latent_regime_dim, and AUTO5 mask fields.
set -euo pipefail

PYTHON=${PYTHON:-python3}
STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_SMOKE=${OUT_SMOKE:-"hpc_results/herald_phase2k_latent_dim_smoke_${STAMP}"}
PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}
DEVICE=${DEVICE:-cpu}

echo "========================================================"
echo " HERALD Phase 2K — latent dim smoke test"
echo " out_smoke : $OUT_SMOKE"
echo " panel     : $PANEL_PATH"
echo " device    : $DEVICE"
echo "========================================================"

if [ -d "$OUT_SMOKE" ]; then
  echo "ERROR: OUT_SMOKE already exists: $OUT_SMOKE" >&2
  echo "       Set STAMP or OUT_SMOKE to a new value." >&2
  exit 1
fi
mkdir -p "${OUT_SMOKE}"/{reports/per_run,data_processed,logs,metadata}

"$PYTHON" -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_v6.py \
  src/modeles/train_herald_v7.py \
  src/modeles/train_herald_semi_v2.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/audit_herald_phase2k_latent_dim.py
echo "py_compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  [ -f "$f" ] || { echo "MISSING input: $f" >&2; exit 1; }
done
echo "input files OK"

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
    --sector-lambda 0.2 \
    --alpha-smooth-lambda 0.001 \
    --smooth-regime-source none \
    --device "$DEVICE" \
    --seed 0 \
    --single-target-year 2021
}

run_config() {
  local label=$1
  local variant=$2
  local latent_dim=$3
  local l1_lambda=$4
  local auto_mask=$5

  echo ""
  echo "--- smoke ${label} (variant=${variant} latent_dim=${latent_dim} l1=${l1_lambda} auto_mask=${auto_mask}) ---"
  local extra_args=()
  if [ "$auto_mask" = "auto" ]; then
    extra_args+=(--latent-dim-auto-mask)
  fi
  "$PYTHON" src/modeles/train_herald_regime_experiment.py \
    --regime-mode no_regime \
    --experiment-label "$label" \
    --feature-policy side5_lag1_growth1y \
    --macro-feature-set none \
    --drop-source-flags \
    --regime-metadata-path "${OUT_SMOKE}/metadata/${label}.json" \
    $(common_args "$label" "$variant") \
    --latent-regime-dim "$latent_dim" \
    --latent-dim-l1-lambda "$l1_lambda" \
    --run-tag "smoke_${label}" \
    "${extra_args[@]+"${extra_args[@]}"}"

  for f in \
    "${OUT_SMOKE}/reports/per_run/${label}.json" \
    "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_total_full_smoke_${label}_seed_0_v1.csv" \
    "${OUT_SMOKE}/data_processed/herald_semi_v2_predictions_sector_full_smoke_${label}_seed_0_v1.csv" \
    "${OUT_SMOKE}/metadata/${label}.json"; do
    [ -f "$f" ] || { echo "MISSING artifact: $f" >&2; exit 1; }
    echo "  OK: $f"
  done
}

run_config L1_gate learned_regime_gate_sector_enhanced 1 0.0 fixed
run_config L3_gate learned_regime_gate_sector_enhanced 3 0.0 fixed
run_config L5_gate learned_regime_gate_sector_enhanced 5 0.0 fixed
run_config L3_both learned_regime_both_sector_enhanced 3 0.0 fixed
run_config AUTO5_l1_005 learned_regime_gate_sector_enhanced 5 0.005 auto

echo ""
echo "Verifying metadata constraints..."
"$PYTHON" - <<PY
import json, sys
from pathlib import Path

out = Path("${OUT_SMOKE}")
errors = []

checks = [
    ("L1_gate",      1, False),
    ("L3_gate",      3, False),
    ("L5_gate",      5, False),
    ("L3_both",      3, False),
    ("AUTO5_l1_005", 5, True),
]

for label, expected_dim, expect_auto in checks:
    jpath = out / "reports" / "per_run" / f"{label}.json"
    data = json.loads(jpath.read_text())
    # The JSON key is under the run_key; iterate to find it
    for run_key, rv in data.items():
        actual_dim = rv.get("latent_regime_dim")
        auto_mask  = rv.get("latent_dim_auto_mask", False)
        if actual_dim != expected_dim:
            errors.append(f"{label}: latent_regime_dim={actual_dim}, expected {expected_dim}")
        if auto_mask != expect_auto:
            errors.append(f"{label}: latent_dim_auto_mask={auto_mask}, expected {expect_auto}")
        if expect_auto:
            mask_vals = rv.get("latent_dim_mask_values")
            eff_dim   = rv.get("latent_dim_effective_dim")
            if mask_vals is None:
                errors.append(f"{label}: latent_dim_mask_values missing")
            elif len(mask_vals) != expected_dim:
                errors.append(f"{label}: mask_values length={len(mask_vals)}, expected {expected_dim}")
            if eff_dim is None:
                errors.append(f"{label}: latent_dim_effective_dim missing")
        print(f"  {label}: latent_dim={actual_dim} auto_mask={auto_mask} "
              f"mask_values={rv.get('latent_dim_mask_values')} "
              f"effective_dim={rv.get('latent_dim_effective_dim')}")
        break

if errors:
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
print("metadata constraints OK")
PY

echo ""
echo "Smoke completed: ${OUT_SMOKE}"
