#!/bin/bash
# Submit HERALD Phase 3D q_tensor ablation battery.
#
# 6 configs × 10 seeds = 60 runs
# Q0_real           — baseline, real q_tensor
# Q1_zero           — q_tensor zeroed (measures total contribution)
# Q3_spatial_perm   — spatial falsification (destroys ZE identity)
# Q4_effectifs_only — only effectifs_salaries_cvs channel
# Q5_masse_only     — only masse_salariale_cvs channel
# Q6_lag1           — q_tensor shifted 1 year back (recency test)
# Q2 (temporal_perm) excluded: global year permutation is not fold-safe.
#
# Usage:
#   bash hpc/regime/submit_herald_phase3d_qtensor.sh
#
# OUT_ROOT: hpc_results/herald_regime_phase3d_qtensor_<STAMP>_r1
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
REGIME_PLAN=phase3d_qtensor
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_phase3d_qtensor_${STAMP}_r1"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
DEVICE=${DEVICE:-}

PANEL_PATH=${PANEL_PATH:-"data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv"}
SPLITS_PATH=${SPLITS_PATH:-"metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv"}
SIDE_A10_PATH=${SIDE_A10_PATH:-"data/processed/side_creations_a10_ze2020_through_2025_v1.csv"}

EXPECTED_CONFIGS=6

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

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/regime_plan_configs.sh
echo "Shell syntax OK"

"$PYTHON" -m py_compile src/modeles/train_herald_v7.py
"$PYTHON" -m py_compile src/modeles/train_herald_semi_v2.py
"$PYTHON" -m py_compile src/modeles/train_herald_regime_experiment.py
"$PYTHON" -m py_compile hpc/regime/audit_herald_phase3d_qtensor_results.py
echo "Python compile OK"

for f in "$PANEL_PATH" "$SPLITS_PATH" "$SIDE_A10_PATH"; do
  if [ ! -f "$f" ]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done
echo "Input files OK"

if [ -d "$OUT_ROOT" ]; then
  echo "ERROR: OUT_ROOT already exists: $OUT_ROOT" >&2
  exit 1
fi
echo "OUT_ROOT OK: $OUT_ROOT"

n_configs=$(REGIME_PLAN=$REGIME_PLAN bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | grep -v "^#" | grep -c '.')
if [ "$n_configs" -ne "$EXPECTED_CONFIGS" ]; then
  echo "ERROR: expected ${EXPECTED_CONFIGS} configs, got ${n_configs}" >&2
  exit 1
fi
echo "Config count OK: ${n_configs} configs"

# Verify all 7 quarterly_tensor_policy values are present
echo "Verifying quarterly_tensor_policy values:"
REGIME_PLAN=$REGIME_PLAN bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs' | \
  awk '{print "  label=" $4, "q_tensor_policy=" $41}'

# Run tag uniqueness
n_seeds=$(echo "$SEEDS" | wc -w | tr -d ' ')
expected_runs=$((n_configs * n_seeds))

declare -A seen_tags
while IFS= read -r line; do
  tag=$(echo "$line" | awk '{
    mode=$1; variant=$2; sp=$3; label=$4;
    tag="regime_"mode;
    if (variant != "full") tag=tag"_"variant;
    if (sp == "no_source_flags") tag=tag"_no_source_flags";
    if (label != "base") tag=tag"_"label;
    print tag
  }')
  if [ -n "${seen_tags[$tag]+x}" ]; then
    echo "ERROR: duplicate run tag: $tag" >&2
    exit 1
  fi
  seen_tags[$tag]=1
done < <(REGIME_PLAN=$REGIME_PLAN bash -c 'source hpc/regime/regime_plan_configs.sh && plan_configs')
echo "Run tag uniqueness OK"

echo ""
echo "============================================================"
echo " Phase 3D q_tensor Ablation — Submit"
echo " plan      : $REGIME_PLAN"
echo " out_root  : $OUT_ROOT"
echo " configs   : $n_configs"
echo " seeds     : $n_seeds ($SEEDS)"
echo " runs      : $expected_runs"
echo " epochs    : $EPOCHS"
echo " hypothesis: q_tensor causal/local audit (Q2 temporal_perm excluded)"
echo "============================================================"
echo ""

# ---- Launch ----
source hpc/regime/submit_herald_phase_template.sh
