#!/bin/bash
# Submit HERALD Phase 4B — nl battery (side5_full features).
#
# 3 configs × 20 seeds = 60 runs
#   side5_full_no_tensor      — lag_1/2/3 + growth_1y/2y, no tensor
#   side5_full_tensor_lag1    — + tensor effectifs_lag1
#   side5_full_tensor_lag2    — + tensor lag2 (2-year shift)
set -euo pipefail

COUNTRY=nl
export COUNTRY

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_phase4b_${COUNTRY}_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025 3 5 11 19 23 29 31 37 101 303"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

EXPECTED_CONFIGS=3

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

bash -n hpc/phase4/run_herald_phase4b_seed.sh
bash -n hpc/phase4/phase4b_configs.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile \
  hpc/phase4/prepare_phase4_panel.py \
  hpc/phase4/run_herald_phase4_wrapper.py \
  hpc/phase4/audit_phase4_results.py \
  src/modeles/train_herald_regime_experiment.py
echo "Python compile OK"

"$PYTHON" - <<PY
import pandas as pd, sys
p = pd.read_csv("data/processed/phase4/${COUNTRY}/panel_ze2020.csv")
missing = [c for c in ["side_lag_2","side_lag_3","growth_2y"] if c not in p.columns]
if missing:
    sys.exit(f"Phase 4B columns missing: {missing} — run prepare_phase4_panel.py --country ${COUNTRY}")
print(f"Phase 4B panel OK: {p['side_lag_2'].notna().sum()}/{len(p)} rows with lag_2")
PY

n_configs=$(COUNTRY=$COUNTRY bash -c 'source hpc/phase4/phase4b_configs.sh && phase4b_configs' | grep -c '.')
if [ "$n_configs" -ne "$EXPECTED_CONFIGS" ]; then
  echo "ERROR: expected ${EXPECTED_CONFIGS} configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs}"

n_seeds=$(echo "$SEEDS" | wc -w | tr -d ' ')
expected_runs=$((n_configs * n_seeds))

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi
echo "OUT_ROOT OK: $OUT_ROOT"

echo ""
echo "============================================================"
echo " Phase 4B — NL Battery (side5_full)"
echo " out_root : $OUT_ROOT"
echo " configs  : $n_configs (side5_full_no_tensor / side5_full_tensor_lag1 / side5_full_tensor_lag2)"
echo " seeds    : $n_seeds ($SEEDS)"
echo " runs     : $expected_runs"
echo " epochs   : $EPOCHS"
echo " features : side5_full — lag_1/2/3 + growth_1y/2y"
echo "============================================================"
echo ""

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}

bash -n hpc/phase4/run_herald_phase4b_array.sbatch
echo "sbatch script syntax OK"

ARRAY_MAX=$(($(echo "$SEEDS" | wc -w) - 1))
EXCLUDE_NODE=${EXCLUDE_NODE:-hpcgpu02}

JOB_ID=$(sbatch \
  --parsable \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --exclude="${EXCLUDE_NODE}" \
  --export=ALL,COUNTRY="${COUNTRY}",SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",DEVICE="${DEVICE}" \
  hpc/phase4/run_herald_phase4b_array.sbatch)

echo ""
echo "============================================================"
echo " Phase 4B NL submitted"
echo " Job ID  : ${JOB_ID}"
echo " OUT_ROOT: ${OUT_ROOT}"
echo " Seeds   : $((ARRAY_MAX + 1)) tasks  (array 0-${ARRAY_MAX}%${MAX_PARALLEL})"
echo ""
echo " Audit quando terminar:"
echo "   python3 hpc/phase4/audit_phase4_results.py --root ${OUT_ROOT} --france-wmape 0.020398"
echo "============================================================"
