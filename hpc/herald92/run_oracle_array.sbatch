#!/bin/bash
#SBATCH --job-name=h92-oracle
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --array=0-119%24
# Slurm opens these before the shell runs; the directory is created at submission time.
#SBATCH --output=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald92/logs/oracle-%A_%a.out
#SBATCH --error=/home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/herald92/logs/oracle-%A_%a.err
set -euo pipefail

cd /home/jpmartinsd/project_recomm_herald_v6_2025_20260430/dataset
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=2

# The first task carries the validation for the whole array: guards and mutants must pass
# on this machine, in this environment, before any oracle arithmetic is written anywhere.
if [ "${SLURM_ARRAY_TASK_ID}" -eq 0 ]; then
  python3 -c 'import sys, numpy; print(sys.version.split()[0], "numpy", numpy.__version__)'
  python3 tests/test_herald92_guards.py
  python3 tests/run_herald92_mutations.py
  touch hpc_results/herald92/VALIDATED_v3_${SLURM_ARRAY_JOB_ID}
fi

python3 hpc/herald92/run_oracle_array.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald92/tasks_v3 \
  --n-zones 280 \
  --n-score 12
