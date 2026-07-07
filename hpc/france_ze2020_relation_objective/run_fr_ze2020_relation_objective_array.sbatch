#!/bin/bash
#SBATCH --job-name=fr_ze2020_rel
#SBATCH --partition=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=10G
#SBATCH --time=02:00:00
#SBATCH --array=0-4
#SBATCH --output=hpc_results/fr_ze2020_relation_objective_default/logs/task_%a.out
#SBATCH --error=hpc_results/fr_ze2020_relation_objective_default/logs/task_%a.err

set -euo pipefail

SEEDS=(42 43 44 45 46)

export SEED="${SEEDS[${SLURM_ARRAY_TASK_ID}]}"

bash hpc/france_ze2020_relation_objective/run_fr_ze2020_relation_objective_task.sh
