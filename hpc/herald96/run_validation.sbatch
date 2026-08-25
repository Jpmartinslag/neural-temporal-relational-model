#!/bin/bash
#SBATCH --job-name=h96-valid
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=hpc_results/herald96/logs/valid-%j.out
#SBATCH --error=hpc_results/herald96/logs/valid-%j.err
set -euo pipefail
cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

python3 tests/test_herald96_guards.py
python3 tests/run_herald96_mutations.py

# Smoke, on the seed reserved for it: the null, one commuting relation, one economic
# relation outside commuting and one non-linear interaction all live in the same universe,
# so the four cases are the four supports plus the null scenario.
for SUP in commuting_only similarity_only typed_union all_pairs; do
  python3 hpc/herald96/run_neural_granger.py --task-id 0 \
    --out-dir hpc_results/herald96/smoke --n-zones 80 --n-score 12 \
    --scenarios M1_MULTIRELATIONAL --scales 1.0 --supports "${SUP}" --seeds 9951
done
python3 hpc/herald96/run_neural_granger.py --task-id 0 \
  --out-dir hpc_results/herald96/smoke --n-zones 80 --n-score 12 \
  --scenarios M0_NULL --scales 1.0 --supports typed_union --seeds 9951
