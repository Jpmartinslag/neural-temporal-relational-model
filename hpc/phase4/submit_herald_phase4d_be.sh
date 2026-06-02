#!/bin/bash
# Submit HERALD Phase 4D — BE battery (functional graphs: commuting + sector similarity).
# 10 configs × 20 seeds = 200 runs
set -euo pipefail

COUNTRY=be
export COUNTRY

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_phase4d_${COUNTRY}_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025 3 5 11 19 23 29 31 37 101 303"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

EXPECTED_CONFIGS=10

if [ -f "${HOME}/venvs/herald-v5-env.sh" ]; then
  source "${HOME}/venvs/herald-v5-env.sh"
elif [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
  source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  conda activate "${CONDA_ENV:-mineru}"
fi
export PYTHON="${PYTHON:-$(command -v python3)}"

# ── Syntax checks ────────────────────────────────────────────────────────────
bash -n hpc/phase4/run_herald_phase4d_seed.sh
bash -n hpc/phase4/phase4d_configs.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile \
  hpc/phase4/prepare_phase4_panel.py \
  hpc/phase4/run_herald_phase4_wrapper.py \
  hpc/phase4/audit_phase4_results.py \
  src/modeles/train_herald_regime_experiment.py
echo "Python compile OK"

# ── Config count check ───────────────────────────────────────────────────────
n_configs=$(COUNTRY=$COUNTRY bash -c 'source hpc/phase4/phase4d_configs.sh && phase4d_configs' | grep -c '.')
if [ "$n_configs" -ne "$EXPECTED_CONFIGS" ]; then
  echo "ERROR: expected ${EXPECTED_CONFIGS} configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs}"

# ── Graph file existence check ───────────────────────────────────────────────
"$PYTHON" hpc/phase4/audit_phase4d_plan.py --country "$COUNTRY" --quiet
echo "Graph audit OK"

# ── OUT_ROOT guard ───────────────────────────────────────────────────────────
n_seeds=$(echo "$SEEDS" | wc -w | tr -d ' ')
expected_runs=$((n_configs * n_seeds))
if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi
echo "OUT_ROOT OK: $OUT_ROOT"

echo ""
echo "============================================================"
echo " Phase 4D — BE Battery (functional graphs)"
echo " out_root : $OUT_ROOT"
echo " configs  : $n_configs"
echo " seeds    : $n_seeds  ($SEEDS)"
echo " runs     : $expected_runs"
echo " epochs   : $EPOCHS"
echo "============================================================"
echo ""

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata}

bash -n hpc/phase4/run_herald_phase4d_array.sbatch
echo "sbatch syntax OK"

ARRAY_MAX=$(($(echo "$SEEDS" | wc -w) - 1))
EXCLUDE_NODE=${EXCLUDE_NODE:-hpcgpu02}

JOB_ID=$(sbatch \
  --parsable \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --exclude="${EXCLUDE_NODE}" \
  --export=ALL,COUNTRY="${COUNTRY}",SEEDS="${SEEDS}",OUT_ROOT="${OUT_ROOT}",EPOCHS="${EPOCHS}",MASK_WARMUP="${MASK_WARMUP}",DEVICE="${DEVICE}" \
  hpc/phase4/run_herald_phase4d_array.sbatch)

echo ""
echo "============================================================"
echo " Phase 4D BE submitted"
echo " Job ID  : ${JOB_ID}"
echo " OUT_ROOT: ${OUT_ROOT}"
echo " Seeds   : $((ARRAY_MAX + 1)) tasks  (array 0-${ARRAY_MAX}%${MAX_PARALLEL})"
echo ""
echo " Audit quando terminar:"
echo "   python3 hpc/phase4/audit_phase4d_results.py --root ${OUT_ROOT} --phase4a-wmape 0.070913 --phase4c-wmape 0.073808"
echo "============================================================"
