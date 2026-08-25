#!/bin/bash
#SBATCH --job-name=h95-valid
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=hpc_results/herald95/logs/valid-%j.out
#SBATCH --error=hpc_results/herald95/logs/valid-%j.err
set -euo pipefail
cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

python3 tests/test_herald95_guards.py
python3 tests/run_herald95_mutations.py
python3 tests/test_herald94_guards.py

# Smoke: the two extreme scales plus the reference, one scenario with a mechanism and the
# flat control, on a seed reserved for the smoke. Reduced epoch budget: it proves the
# mechanics, not the science.
for SCEN in N0_NULL N4_INTERACTION; do
  for SCALE in 0.0 1.0 4.0; do
    python3 hpc/herald95/run_ladder.py --task-id 0 \
      --out-dir hpc_results/herald95/smoke \
      --n-zones 280 --n-score 12 --epochs 300 \
      --scenarios "${SCEN}" --scales "${SCALE}" --seeds 9891
  done
done
