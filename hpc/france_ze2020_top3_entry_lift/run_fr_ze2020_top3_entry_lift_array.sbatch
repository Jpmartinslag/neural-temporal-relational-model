#!/bin/bash
#SBATCH --job-name=fr_ze2020_t3_lift
#SBATCH --partition=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=10G
#SBATCH --time=02:00:00
#SBATCH --array=0-19
#SBATCH --output=hpc_results/fr_ze2020_top3_entry_lift_default/logs/task_%a.out
#SBATCH --error=hpc_results/fr_ze2020_top3_entry_lift_default/logs/task_%a.err

set -euo pipefail

SEEDS=(42 43 44 45 46)
SCENARIOS=(full_control temporal_shuffle sector_shuffle target_shuffle)

SCENARIO_INDEX=$((SLURM_ARRAY_TASK_ID / ${#SEEDS[@]}))
SEED_INDEX=$((SLURM_ARRAY_TASK_ID % ${#SEEDS[@]}))

export SCENARIO="${SCENARIOS[${SCENARIO_INDEX}]}"
export SEED="${SEEDS[${SEED_INDEX}]}"

bash hpc/france_ze2020_top3_entry_lift/run_fr_ze2020_top3_entry_lift_task.sh
