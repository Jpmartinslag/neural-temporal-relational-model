#!/bin/bash
#SBATCH --job-name=h94-valid
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=hpc_results/herald94/logs/valid-%j.out
#SBATCH --error=hpc_results/herald94/logs/valid-%j.err
set -euo pipefail

cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1

python3 -c "import sys, numpy; print('python', sys.version.split()[0], 'numpy', numpy.__version__); import numpy.__config__ as c; c.show()"

# Guards first: a failing guard must stop the array before any science runs.
python3 tests/test_herald94_guards.py
python3 tests/run_herald94_mutations.py

# The smoke: two seeds reserved for it, never used for a result, all six scenarios,
# a reduced epoch budget. It proves the mechanics, not the science.
for SCEN in N0_NULL N1_LINEAR N2_NONLINEAR N3_REGIME N4_INTERACTION N5_REDUNDANT; do
  python3 hpc/herald94/run_layer1.py --task-id 0 \
    --out-dir hpc_results/herald94/smoke \
    --n-zones 280 --n-score 12 --epochs 300 \
    --scenarios "${SCEN}" --seeds 9601
done

# Repeated once, to prove the fit is reproducible. HERALD 93 lost a grid to a summation
# order that was not fixed, and the only reason it was caught was a repeat like this one.
python3 hpc/herald94/run_layer1.py --task-id 0 \
  --out-dir hpc_results/herald94/smoke_repeat \
  --n-zones 280 --n-score 12 --epochs 300 \
  --scenarios N1_LINEAR --seeds 9601
python3 - <<'PY'
import json, pathlib, sys
first = json.loads(pathlib.Path("hpc_results/herald94/smoke/layer1_N1_LINEAR_9601.json").read_text())
again = json.loads(pathlib.Path("hpc_results/herald94/smoke_repeat/layer1_N1_LINEAR_9601.json").read_text())
for arm in first["arms"]:
    a = first["arms"][arm]["out_of_sample"]["mse"]
    b = again["arms"][arm]["out_of_sample"]["mse"]
    if a != b:
        sys.exit(f"{arm} was not reproducible: {a} vs {b}")
print("two identical runs agreed exactly on every arm")
PY
