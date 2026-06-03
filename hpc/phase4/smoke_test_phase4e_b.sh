#!/bin/bash
# Smoke test for Phase 4E-B: 1 epoch, CPU, seed=42, all configs/countries.

set -euo pipefail

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

PYTHON=${PYTHON:-$(command -v python3)}
SMOKE_DIR="hpc_results/smoke_phase4e_b_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$SMOKE_DIR"

echo "=== Phase 4E-B Smoke Test $(date '+%Y-%m-%d %H:%M:%S') ==="
"$PYTHON" hpc/phase4/prepare_phase4e_panel.py --country all
"$PYTHON" -m py_compile hpc/phase4/run_herald_phase4e_a_wrapper.py hpc/phase4/run_herald_phase4e_a2_wrapper.py

PASS=0
FAIL=0
for COUNTRY in fr nl be pt; do
  OUT_ROOT="$SMOKE_DIR/$COUNTRY"
  mkdir -p "$OUT_ROOT"/{reports/per_run,reports/sector,data_processed,logs,metadata}
  expected=$(COUNTRY="$COUNTRY" bash -lc 'source hpc/phase4/phase4e_b_configs.sh && phase4e_b_configs | wc -l')
  echo "[$COUNTRY] smoke expected_configs=${expected}..."
  if SEED=42 COUNTRY="$COUNTRY" OUT_ROOT="$OUT_ROOT" EPOCHS=1 MASK_WARMUP=0 DEVICE=cpu \
      bash hpc/phase4/run_herald_phase4e_b_seed.sh 2>&1 | tail -12; then
    n=$(find "$OUT_ROOT/reports/per_run" -type f -name "*.json" | wc -l)
    if [ "$n" -eq "$expected" ]; then
      echo "[$COUNTRY] PASS"
      PASS=$((PASS+1))
    else
      echo "[$COUNTRY] FAIL: expected ${expected} JSON, got $n"
      FAIL=$((FAIL+1))
    fi
  else
    echo "[$COUNTRY] FAIL"
    FAIL=$((FAIL+1))
  fi
done

echo "=== Smoke 4E-B results: PASS=${PASS} FAIL=${FAIL} ==="
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
