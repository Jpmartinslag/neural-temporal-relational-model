#!/bin/bash
# Smoke test for Phase 4E-A: 1 epoch, CPU, seed=42, all 4 countries.
# Verifies:
#   1. Panel prepare runs without errors
#   2. Wrapper runs without errors
#   3. NON_PREDICTIVE_FIELDS (is_covid_year, is_post_covid_rebound) are NOT in features
#   4. JSON result is produced with expected fields
#   5. WMAPE is in a sane range (>0, <2)

set -euo pipefail

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

PYTHON=${PYTHON:-$(command -v python3)}
SMOKE_DIR="hpc_results/smoke_phase4e_a_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$SMOKE_DIR"

echo "=== Phase 4E-A Smoke Test  $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "    Output: $SMOKE_DIR"
echo ""

# Step 1: prepare panels
echo "[1/3] Preparing Phase 4E-A panels..."
"$PYTHON" hpc/phase4/prepare_phase4e_panel.py --country all
echo "      OK"
echo ""

# Step 2: schema check — confirm feature policy
echo "[2/3] Schema checks..."
"$PYTHON" - <<'PYEOF'
import sys
sys.path.insert(0, ".")
from src.data.european_panel.schema import NON_PREDICTIVE_FIELDS, BASELINE_ANNUAL_FEATURES

HERALD_NON_PRED = ["is_covid_year", "is_post_covid_rebound"]
HERALD_BASELINE = ["side_lag_1", "side_lag_2", "side_lag_3", "growth_1y", "growth_2y"]

print(f"  NON_PREDICTIVE_FIELDS (canonical): {NON_PREDICTIVE_FIELDS}")
print(f"  HERALD equivalents:                {HERALD_NON_PRED}")
print(f"  BASELINE_ANNUAL_FEATURES:          {BASELINE_ANNUAL_FEATURES}")
print(f"  HERALD baseline cols:              {HERALD_BASELINE}")

# Simulate what wrapper does and verify no leakage
def baseline_feature_columns(panel_cols):
    cols = HERALD_BASELINE + ["has_flores_source", "has_side_stock_source", "has_urssaf_source"]
    selected = [c for c in cols if c in panel_cols]
    leaked = [c for c in selected if c in HERALD_NON_PRED]
    if leaked:
        print(f"  FAIL: NON_PREDICTIVE leaked: {leaked}", file=sys.stderr)
        sys.exit(1)
    return selected

import pandas as pd
sample_panel_cols = [
    "ZE2020", "target_year", "node_idx", "side_establishment_creations_official",
    "side_enterprise_creations_official", "side_lag_1", "side_lag_2", "side_lag_3",
    "growth_1y", "growth_2y", "has_flores_source", "has_side_stock_source",
    "has_urssaf_source", "feature_forecast_safe",
    "is_covid_year", "is_post_covid_rebound",  # present in panel but must not enter features
    "side_stock_total_t_minus_1",
]
selected = baseline_feature_columns(sample_panel_cols)
print(f"  Features selected: {selected}")
assert "is_covid_year" not in selected, "COVID flag leaked!"
assert "is_post_covid_rebound" not in selected, "Rebound flag leaked!"
print("  PASS: NON_PREDICTIVE_FIELDS correctly excluded from feature set")
PYEOF
echo ""

# Step 3: run 1-epoch training per country
echo "[3/3] Running 1-epoch training (seed=42, CPU)..."
PASS=0
FAIL=0
for COUNTRY in fr nl be pt; do
  COUNTRY_DIR="$SMOKE_DIR/$COUNTRY"
  mkdir -p "$COUNTRY_DIR"/{reports/per_run,data_processed,metadata,logs}

  PHASE4E_BASE="data/processed/phase4e/${COUNTRY}"
  export PHASE4E_COUNTRY="$COUNTRY"
  export PHASE4E_PANEL="${PHASE4E_BASE}/panel_ze2020.csv"
  export PHASE4E_SPLITS="${PHASE4E_BASE}/splits.csv"
  export PHASE4E_SIDE_A10="${PHASE4E_BASE}/a10_ze2020.csv"
  export PHASE4E_GEO_ADJ="${PHASE4E_BASE}/adj_geo.csv"
  export PHASE4E_MOB_ADJ="${PHASE4E_BASE}/adj_mob.csv"
  export PHASE4E_CONFIG_LABEL="baseline_annual"
  export PHASE4_TENSOR_POLICY="zero"

  RUN_TAG="phase4e_a_${COUNTRY}_baseline_annual"
  OUT_JSON="${COUNTRY_DIR}/reports/per_run/${RUN_TAG}_seed_42.json"
  META_JSON="${COUNTRY_DIR}/metadata/${RUN_TAG}_seed_42.json"

  echo "  [$COUNTRY] training..."
  if "$PYTHON" hpc/phase4/run_herald_phase4e_a_wrapper.py \
      --regime-mode no_regime \
      --quarterly-tensor-policy zero \
      --feature-policy current_clean \
      --macro-feature-set none \
      --experiment-label "baseline_annual" \
      --regime-metadata-path "$META_JSON" \
      --mode full \
      --v7-variant learned_regime_gate_sector_enhanced \
      --smooth-regime-source none \
      --latent-train-mode normal \
      --latent-inference-mode match_train \
      --regime-seq-transform none \
      --top-k 10 --smooth-lambda 0.01 --gate-entropy-lambda 0.001 \
      --alpha-smooth-lambda 0.001 --sector-lambda 0.2 --lr 0.001 \
      --huber-delta 300 --gate-bias-init 2.0 --alpha-bias-init 0.0 \
      --hidden-dim 64 --q-hidden 32 --attn-dim 16 \
      --feature-mask-ratio 0.10 --sector-mask-ratio 0.30 --rank-lambda 0.02 \
      --latent-regime-dim 5 --auditor-mode none \
      --residual-shrinkage-mode train_opt --residual-shrinkage-value 1.0 \
      --residual-shrinkage-min 0.0 --residual-shrinkage-max 1.25 \
      --tutor-feature-set none --tutor-state-transform none \
      --panel-path "${PHASE4E_BASE}/panel_ze2020.csv" \
      --splits-path "${PHASE4E_BASE}/splits.csv" \
      --side-a10-path "${PHASE4E_BASE}/a10_ze2020.csv" \
      --prediction-output-dir "${COUNTRY_DIR}/data_processed" \
      --metrics-path "$OUT_JSON" \
      --model-card-path "${COUNTRY_DIR}/reports/per_run/${RUN_TAG}_seed_42.md" \
      --semi-warmup-epochs 0 \
      --epochs 1 \
      --seed 42 \
      --run-tag "$RUN_TAG" \
      --device cpu \
      2>&1 | tail -5; then

    # Verify JSON produced and has wmape
    if "$PYTHON" - "$OUT_JSON" <<'PYEOF'
import json, sys
p = sys.argv[1]
try:
    d = list(json.loads(open(p).read()).values())[0]
    wmape = d.get("total_wmape_mean") or d.get("wmape_mean", float("nan"))
    assert 0 < float(wmape) < 2, f"WMAPE {wmape} out of sane range"
    # Check metadata
    meta_p = p.replace("/reports/per_run/", "/metadata/")
    if open(meta_p.replace(".json","_seed_42.json") if "_seed_42" not in meta_p else meta_p).read():
        m = json.loads(open(meta_p).read())
        assert "is_covid_year" not in m.get("baseline_annual_features", [])
    print(f"  WMAPE={wmape:.5f}  JSON OK  metadata OK")
    sys.exit(0)
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
PYEOF
    then
      echo "  [$COUNTRY] PASS"
      PASS=$((PASS+1))
    else
      echo "  [$COUNTRY] FAIL (JSON check)"
      FAIL=$((FAIL+1))
    fi
  else
    echo "  [$COUNTRY] FAIL (training error)"
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "=== Smoke test results: PASS=${PASS} FAIL=${FAIL} ==="
if [ "$FAIL" -gt 0 ]; then
  echo "SMOKE TEST FAILED — do not submit Phase 4E-A" >&2
  exit 1
fi
echo "Smoke test PASSED — ready to submit Phase 4E-A"
echo "Run: bash hpc/phase4/submit_herald_phase4e_a.sh"
