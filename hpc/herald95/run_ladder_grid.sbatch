#!/bin/bash
#SBATCH --job-name=h95-ladder
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=03:00:00
#SBATCH --array=0-59%20
#SBATCH --output=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald95/logs/ladder-%A_%a.out
#SBATCH --error=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald95/logs/ladder-%A_%a.err
set -euo pipefail
cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

# Four scenarios by five scales by three seeds. The seeds 9901-9903 have never been
# generated; every calibration decision in this stage was taken on 9891-9892.
python3 hpc/herald95/run_ladder.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald95/tasks \
  --n-zones 280 --n-score 12
