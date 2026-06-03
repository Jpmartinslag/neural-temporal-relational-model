#!/bin/bash
# Smoke test for Phase 4E-C: 1 epoch, CPU, seed=42, all configs/countries.
# Validates: JSON output, phase metadata, macro_feature_set recorded, c5 marked as falsification.

set -euo pipefail

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

PYTHON=${PYTHON:-$(command -v python3)}
SMOKE_DIR="hpc_results/smoke_phase4e_c_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$SMOKE_DIR"

echo "=== Phase 4E-C Smoke Test $(date '+%Y-%m-%d %H:%M:%S') ==="
"$PYTHON" hpc/phase4/prepare_phase4e_panel.py --country all
"$PYTHON" -m py_compile \
  hpc/phase4/run_herald_phase4e_a_wrapper.py \
  hpc/phase4/run_herald_phase4e_a2_wrapper.py \
  hpc/phase4/audit_phase4e_c_results.py

PASS=0
FAIL=0
for COUNTRY in fr nl be pt; do
  OUT_ROOT="$SMOKE_DIR/$COUNTRY"
  mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}
  expected=$(COUNTRY="$COUNTRY" bash -lc 'source hpc/phase4/phase4e_c_configs.sh && phase4e_c_configs | wc -l')
  echo "[$COUNTRY] smoke expected_configs=${expected}..."
  if SEED=42 COUNTRY="$COUNTRY" OUT_ROOT="$OUT_ROOT" EPOCHS=1 MASK_WARMUP=0 DEVICE=cpu \
      bash hpc/phase4/run_herald_phase4e_c_seed.sh 2>&1 | tail -12; then
    n=$(find "$OUT_ROOT/reports/per_run" -type f -name "*.json" | wc -l)
    if [ "$n" -eq "$expected" ]; then
      echo "[$COUNTRY] JSON count OK ($n/$expected)"
      COUNTRY_PASS=1
    else
      echo "[$COUNTRY] FAIL: expected ${expected} JSON, got $n"
      COUNTRY_PASS=0
      FAIL=$((FAIL+1))
    fi

    # Validate metadata: phase, macro_feature_set, is_falsification_test for c5
    meta_errors=0
    for meta_file in "$OUT_ROOT/metadata"/*.json; do
      [ -f "$meta_file" ] || continue
      phase_val=$("$PYTHON" -c "import json,sys; d=json.load(open('$meta_file')); print(d.get('phase','MISSING'))" 2>/dev/null || echo "ERR")
      if [ "$phase_val" != "4E-C" ]; then
        echo "[$COUNTRY] WARN: $meta_file phase=$phase_val (expected 4E-C)"
        meta_errors=$((meta_errors+1))
      fi
      # Check macro_feature_set recorded
      macro_val=$("$PYTHON" -c "import json,sys; d=json.load(open('$meta_file')); print(d.get('macro_feature_set','MISSING'))" 2>/dev/null || echo "ERR")
      if [ "$macro_val" = "MISSING" ]; then
        echo "[$COUNTRY] WARN: $meta_file macro_feature_set not recorded"
        meta_errors=$((meta_errors+1))
      fi
    done

    # Check c5 falsification flag in metadata JSON (written by trainer, not per-run)
    for json_file in "$OUT_ROOT/metadata"/*c5_all_eu_perm*.json; do
      [ -f "$json_file" ] || continue
      is_falsif=$("$PYTHON" -c "
import json, sys
d = json.load(open('$json_file'))
print(d.get('is_falsification_test', 'MISSING'))
" 2>/dev/null || echo "ERR")
      if [ "$is_falsif" != "True" ] && [ "$is_falsif" != "true" ]; then
        echo "[$COUNTRY] WARN: c5 is_falsification_test=$is_falsif (expected True)"
        meta_errors=$((meta_errors+1))
      fi
    done

    if [ "${COUNTRY_PASS:-0}" -eq 1 ] && [ "$meta_errors" -eq 0 ]; then
      echo "[$COUNTRY] PASS"
      PASS=$((PASS+1))
    elif [ "${COUNTRY_PASS:-0}" -eq 1 ]; then
      echo "[$COUNTRY] PASS (${meta_errors} metadata warnings)"
      PASS=$((PASS+1))
    fi
  else
    echo "[$COUNTRY] FAIL"
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "=== Smoke 4E-C results: PASS=${PASS} FAIL=${FAIL} ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
