#!/bin/bash
#SBATCH --job-name=h91-tournament-v2
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
# Slurm opens these before the shell runs, so the directory must already exist.
#SBATCH --output=hpc_results/herald91/slurm-%j.out
#SBATCH --error=hpc_results/herald91/slurm-%j.err
set -euo pipefail

cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5

export PYTHONHASHSEED=0
export OMP_NUM_THREADS=4

echo "=== environment ==="
python3 -c 'import sys, numpy; print(sys.version.split()[0], "numpy", numpy.__version__)'

# Guards and mutants run again inside the job. `set -e` aborts before any tournament
# arithmetic if the corrected mechanism has drifted on this machine.
echo "=== guards ==="
python3 tests/test_herald91_inference_guards.py
echo "=== mutants ==="
python3 tests/run_herald91_inference_mutations.py
echo "=== integration guards ==="
python3 tests/test_herald91_integration_guards.py
echo "=== integration mutants ==="
python3 tests/run_herald91_integration_mutations.py

# Exploratory probe only: forty placebo draws, floor 1/41. DEC-132 did not authorise a
# confirmatory run, so `--confirmatory` is deliberately absent.
echo "=== corrected tournament v2 ==="
python3 hpc/herald91/run_tournament_v2.py \
  --out hpc_results/herald91/corrected_tournament_v2_meso_${SLURM_JOB_ID}.json \
  --placebo-draws 40

echo "=== done ==="
