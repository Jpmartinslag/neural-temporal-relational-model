#!/bin/bash
# Submit HERALD Phase 4 — Pays-Bas battery.
#
# 3 configs × 20 seeds = 60 runs
#   baseline_side2     — side_lag_1 + growth_1y, no tensor
#   qtensor_jobs_lag1  — + CBS employee jobs tensor lag1
#   no_qtensor_control — all features, no tensor (ablation)
#
# Usage:
#   bash hpc/phase4/submit_herald_phase4_nl.sh
#   STAMP=20260601_120000 bash hpc/phase4/submit_herald_phase4_nl.sh
#
# Prerequisite:
#   python3 hpc/phase4/prepare_phase4_panel.py --country nl
#   bash hpc/phase4/smoke_test_phase4_nl.sh
set -euo pipefail

COUNTRY=nl
export COUNTRY

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_phase4_nl_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025 3 5 11 19 23 29 31 37 101 303"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

EXPECTED_CONFIGS=3
EXPECTED_RUNS=60  # 3 × 20

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  # shellcheck disable=SC1090
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi

export PYTHON="${PYTHON:-$(command -v python3)}"

# ---- Preflight ----

bash -n hpc/phase4/run_herald_phase4_seed.sh
bash -n hpc/phase4/phase4_configs.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile hpc/phase4/prepare_phase4_panel.py
"$PYTHON" -m py_compile hpc/phase4/run_herald_phase4_wrapper.py
"$PYTHON" -m py_compile hpc/phase4/audit_phase4_results.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
echo "Python compile OK"

for f in \
  "data/processed/phase4/${COUNTRY}/panel_ze2020.csv" \
  "data/processed/phase4/${COUNTRY}/a10_ze2020.csv" \
  "data/processed/phase4/${COUNTRY}/splits.csv" \
  "data/processed/phase4/${COUNTRY}/adj_geo.csv" \
  "data/processed/phase4/${COUNTRY}/adj_mob.csv" \
  "data/external/netherlands/processed/netherlands_qtensor_jobs_panel.csv"
do
  if [ ! -f "$f" ]; then
    echo "Missing: $f" >&2
    echo "Run: python3 hpc/phase4/prepare_phase4_panel.py --country ${COUNTRY}" >&2
    exit 1
  fi
done
echo "Input files OK"

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi
echo "OUT_ROOT OK: $OUT_ROOT"

n_configs=$(COUNTRY=$COUNTRY bash -c 'source hpc/phase4/phase4_configs.sh && phase4_configs' | grep -c '.')
if [ "$n_configs" -ne "$EXPECTED_CONFIGS" ]; then
  echo "ERROR: expected ${EXPECTED_CONFIGS} configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs}"

n_seeds=$(echo "$SEEDS" | wc -w | tr -d ' ')
expected_runs=$((n_configs * n_seeds))
if [ "$expected_runs" -ne "$EXPECTED_RUNS" ]; then
  echo "WARNING: expected ${EXPECTED_RUNS} runs, will produce ${expected_runs}"
fi

echo ""
echo "============================================================"
echo " Phase 4 — Pays-Bas Battery"
echo " out_root : $OUT_ROOT"
echo " configs  : $n_configs (baseline_side2 / qtensor_jobs_lag1 / no_qtensor_control)"
echo " seeds    : $n_seeds ($SEEDS)"
echo " runs     : $expected_runs"
echo " epochs   : $EPOCHS"
echo " tensor   : CBS 83582NED employee jobs × SBI-A10 × COROP (Q7-equivalent)"
echo "============================================================"
echo ""

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}

bash -n hpc/phase4/run_herald_phase4_array.sbatch
echo "sbatch script syntax OK"

# ---- Submit Slurm array (1 task per seed) ----

ARRAY_MAX=$(($(echo "$SEEDS" | wc -w) - 1))
EXCLUDE_NODE=${EXCLUDE_NODE:-hpcgpu02}

SBATCH_ARGS=(
  --parsable
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}"
  --exclude="${EXCLUDE_NODE}"
  --export=ALL,COUNTRY="${COUNTRY}",SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",DEVICE="${DEVICE}"
)

JOB_ID=$(sbatch "${SBATCH_ARGS[@]}" hpc/phase4/run_herald_phase4_array.sbatch)

echo ""
echo "============================================================"
echo " Phase 4 NL submitted"
echo " Job ID  : ${JOB_ID}"
echo " OUT_ROOT: ${OUT_ROOT}"
echo " Seeds   : $((ARRAY_MAX + 1)) tasks  (array 0-${ARRAY_MAX}%${MAX_PARALLEL})"
echo ""
echo " Monitor:"
echo "   squeue -u \$USER"
echo "   sacct -j ${JOB_ID} --format=JobID,JobName%40,State,ExitCode,Elapsed"
echo "   find ${OUT_ROOT}/reports/per_run -name '*.json' | wc -l  # progress"
echo "   tail -f ${OUT_ROOT}/logs/*.out"
echo ""
echo " Audit when done:"
echo "   python3 hpc/phase4/audit_phase4_results.py --root ${OUT_ROOT} --france-wmape 0.020398"
echo "============================================================"
