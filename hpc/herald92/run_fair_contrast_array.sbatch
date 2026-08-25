#!/bin/bash
#SBATCH --job-name=h92-fair
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:40:00
#SBATCH --array=0-59%20
# Slurm opens these before the shell runs; the directory is created at submission time.
#SBATCH --output=hpc_results/herald92/logs/fair-%A_%a.out
#SBATCH --error=hpc_results/herald92/logs/fair-%A_%a.err
set -euo pipefail

cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=2

# Task zero validates the whole array. Guards, mutants and the equality audit must all pass
# on this machine, in this environment, at the real zone count, before any contrast
# arithmetic is written anywhere. The audit is the precondition of the gate: if the pair is
# not matched, the contrast has no meaning and `set -e` stops the array here.
if [ "${SLURM_ARRAY_TASK_ID}" -eq 0 ]; then
  python3 -c 'import sys, numpy; print(sys.version.split()[0], "numpy", numpy.__version__)'
  python3 tests/test_herald92_fair_guards.py
  python3 tests/run_herald92_fair_mutations.py
  python3 src/data/synthetic/audit_fair_pair_v92.py \
    --seeds $(seq 9501 9520) --n-zones 280 \
    --out hpc_results/herald92/fair_equality_audit.json
  touch hpc_results/herald92/VALIDATED_fair_${SLURM_ARRAY_JOB_ID}
fi

python3 hpc/herald92/run_fair_contrast_array.py \
  --task-id "${SLURM_ARRAY_TASK_ID}" \
  --out-dir hpc_results/herald92/tasks_fair \
  --n-zones 280 \
  --n-score 12
