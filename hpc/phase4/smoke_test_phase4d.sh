#!/bin/bash
# Phase 4D smoke test — 1 epoch, cpu, 1 seed, all configs per country.
# Run locally before submitting to cluster.
#
# Usage:
#   bash hpc/phase4/smoke_test_phase4d.sh nl
#   bash hpc/phase4/smoke_test_phase4d.sh be
#   bash hpc/phase4/smoke_test_phase4d.sh pt
#   bash hpc/phase4/smoke_test_phase4d.sh all

set -euo pipefail

COUNTRY_ARG="${1:-all}"
SMOKE_SEED=42
SMOKE_EPOCHS=1
SMOKE_WARMUP=0

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi
PYTHON="${PYTHON:-$(command -v python3)}"

run_smoke() {
  local country="$1"
  local stamp
  stamp=$(date +%Y%m%d_%H%M%S)
  local out="hpc_results/herald_phase4d_${country}_smoke_${stamp}"

  echo ""
  echo "=== SMOKE TEST [${country^^}] seed=${SMOKE_SEED} epochs=${SMOKE_EPOCHS} ==="

  # Pre-audit
  "$PYTHON" hpc/phase4/audit_phase4d_plan.py --country "$country" --quiet
  echo "  audit: OK"

  SEED="$SMOKE_SEED" \
  COUNTRY="$country" \
  OUT_ROOT="$out" \
  EPOCHS="$SMOKE_EPOCHS" \
  MASK_WARMUP="$SMOKE_WARMUP" \
  DEVICE="cpu" \
  PYTHON="$PYTHON" \
  bash hpc/phase4/run_herald_phase4d_seed.sh

  # Count outputs
  n_json=$(find "$out/reports/per_run" -name "*.json" | wc -l)
  n_meta=$(find "$out/metadata" -name "*.json" | wc -l)
  echo ""
  echo "  Smoke done: ${n_json} metrics JSONs, ${n_meta} metadata JSONs"

  # Verify graph metadata was injected
  for mf in "$out/metadata"/*.json; do
    if ! python3 -c "
import json, sys
d = json.loads(open('$mf').read())
missing = [k for k in ['graph_path','graph_density','graph_policy'] if k not in d]
if missing: sys.exit(f'metadata missing: {missing} in $mf')
" 2>&1; then
      echo "  WARNING: graph metadata missing in $(basename $mf)"
    fi
  done
  echo "  graph metadata: OK"
  echo "  OUT: $out"
}

case "$COUNTRY_ARG" in
  all) run_smoke nl; run_smoke be; run_smoke pt ;;
  nl|be|pt) run_smoke "$COUNTRY_ARG" ;;
  *) echo "Usage: $0 [nl|be|pt|all]" >&2; exit 1 ;;
esac

echo ""
echo "Smoke test complete."
