#!/bin/bash
#SBATCH --job-name=fr_ze2020_dg_rank
#SBATCH --array=0-4
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00

set -euo pipefail

SEEDS=(42 43 44 45 46)
export SEED="${SEEDS[$SLURM_ARRAY_TASK_ID]}"

bash hpc/france_ze2020_dynamic_graph/run_fr_ze2020_dynamic_graph_ranker_task.sh

