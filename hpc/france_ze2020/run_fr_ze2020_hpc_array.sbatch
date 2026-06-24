#!/bin/bash
#SBATCH --job-name=fr_ze2020_hpc
#SBATCH --partition=fast
#SBATCH --qos=fast
#SBATCH --array=0-4
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=hpc_results/fr_ze2020_hpc_default/logs/task_%a.out
#SBATCH --error=hpc_results/fr_ze2020_hpc_default/logs/task_%a.err

# HERALD -- France ZE2020 HPC array (5 seeds x 4 existing training scripts).
# See reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md.
#
# The --output/--error paths above are a fallback default for a direct
# `sbatch` invocation; submit_fr_ze2020_hpc.sh overrides them with a
# timestamped RUN_ID path and passes RUN_ID via --export so this job and
# run_fr_ze2020_hpc_task.sh agree on where to write.
#
# Array index 0-4 maps to seeds [42, 43, 44, 45, 46] -- 5 seeds, not 1
# (the local smoke run used SEED=42 only). No torch, no GPU: sklearn-only
# (MLPRegressor), CPU partition. ~2-3 min/task expected (HERALD_19 section 7).

set -euo pipefail

WORKDIR="${HOME}/project_recomm_herald_v6_2025_20260430/dataset"
cd "${WORKDIR}"

SEEDS=(42 43 44 45 46)
export SEED="${SEEDS[${SLURM_ARRAY_TASK_ID}]}"
export RUN_ID="${RUN_ID:-default}"

echo "Array task ${SLURM_ARRAY_TASK_ID} -> seed ${SEED}, run ${RUN_ID}"
bash hpc/france_ze2020/run_fr_ze2020_hpc_task.sh
