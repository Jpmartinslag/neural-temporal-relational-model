#!/bin/bash
#SBATCH --job-name=h94-layer1
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=03:00:00
#SBATCH --array=0-29%15
#SBATCH --output=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald94/logs/layer1-%A_%a.out
#SBATCH --error=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald94/logs/layer1-%A_%a.err
set -euo pipefail

cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

# Six scenarios by the five final seeds, 280 zones, twelve rolling origins. The final seeds
# 9701-9705 have never been looked at: every calibration decision in this stage was taken on
# the smoke seeds 9601-9602.
python3 hpc/herald94/run_layer1.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald94/tasks \
  --n-zones 280 --n-score 12
