#!/bin/bash
#SBATCH --job-name=fr_ctx_rel
#SBATCH --partition=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=18:00:00
#SBATCH --array=0-4
#SBATCH --output=hpc_results/fr_ze2020_context_sector_relation_default/logs/task_%a.out
#SBATCH --error=hpc_results/fr_ze2020_context_sector_relation_default/logs/task_%a.err

set -euo pipefail

SEEDS=(42 43 44 45 46)
export SEED="${SEEDS[${SLURM_ARRAY_TASK_ID}]}"

bash hpc/france_ze2020_context_sector_relation/run_fr_ze2020_context_sector_relation_task.sh
