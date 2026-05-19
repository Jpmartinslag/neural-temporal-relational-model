#!/bin/bash
set -euo pipefail

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
OUT_ROOT=${OUT_ROOT:-"hpc_results/herald_regime_discovery_${STAMP}"}
SEEDS=${SEEDS:-"0 1 7 13 17 42 77 99 123 2025"}
EPOCHS=${EPOCHS:-800}
MASK_WARMUP=${MASK_WARMUP:-100}
MAX_PARALLEL=${MAX_PARALLEL:-10}
REGIME_PLAN=${REGIME_PLAN:-discovery}
DEVICE=${DEVICE:-}

mkdir -p "$OUT_ROOT"/{reports/per_run,data_processed,logs,metadata} logs

echo "OUT_ROOT=$OUT_ROOT"
echo "SEEDS=$SEEDS"
echo "EPOCHS=$EPOCHS"
echo "MASK_WARMUP=$MASK_WARMUP"
echo "MAX_PARALLEL=$MAX_PARALLEL"
echo "REGIME_PLAN=$REGIME_PLAN"
echo "DEVICE=${DEVICE:-auto}"
echo "NOTE: use this submit wrapper instead of direct sbatch so OUT_ROOT is unique and audited."

bash -n hpc/regime/run_herald_regime_seed.sh
bash -n hpc/regime/run_herald_regime_array.sbatch
python3 -m py_compile \
  src/modeles/herald_regime_modes.py \
  src/modeles/train_herald_regime_experiment.py \
  hpc/regime/audit_herald_regime_plan.py \
  hpc/regime/aggregate_herald_regime_results.py

python3 hpc/regime/audit_herald_regime_plan.py --root "$OUT_ROOT" --seeds "$SEEDS" --plan "$REGIME_PLAN"

N_SEEDS=$(wc -w <<< "$SEEDS")
ARRAY_MAX=$((N_SEEDS - 1))

sbatch \
  --array=0-"${ARRAY_MAX}"%"${MAX_PARALLEL}" \
  --export=ALL,OUT_ROOT="$OUT_ROOT",SEEDS="$SEEDS",EPOCHS="$EPOCHS",MASK_WARMUP="$MASK_WARMUP",REGIME_PLAN="$REGIME_PLAN",DEVICE="$DEVICE" \
  hpc/regime/run_herald_regime_array.sbatch

cat <<EOF

Monitor:
  squeue -u "$USER"
  sacct -j <JOBID> --format=JobID,JobName%30,State,ExitCode,Elapsed
  tail -f logs/herald-regime-<JOBID>_0.out

Aggregate after finish:
  python3 hpc/regime/aggregate_herald_regime_results.py --root "$OUT_ROOT"
EOF
