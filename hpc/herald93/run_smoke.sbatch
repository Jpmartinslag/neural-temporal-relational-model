#!/bin/bash
#SBATCH --job-name=h93-smoke
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=hpc_results/herald93/logs/smoke-%j.out
#SBATCH --error=hpc_results/herald93/logs/smoke-%j.err
set -euo pipefail

cd "${REPO_ROOT:?set REPO_ROOT to the repository root}"
module load conda/23.3.1
source activate herald-v5
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8

python3 -c 'import sys,numpy,torch; print(sys.version.split()[0],"numpy",numpy.__version__,"torch",torch.__version__)'

echo "=== guards ==="
python3 tests/test_herald93_guards.py

echo "=== mutants ==="
python3 tests/run_herald93_mutations.py

echo "=== smoke: four methods, S0 and S1, one non-final seed, 280 zones ==="
rm -rf hpc_results/herald93/smoke_a hpc_results/herald93/smoke_b
for TASK in $(seq 0 9); do
  python3 hpc/herald93/run_model_benchmark.py --task-id "$TASK" \
    --out-dir hpc_results/herald93/smoke_a --n-zones 280 --n-score 6 --epochs 2 \
    --seeds 9301 --widths 64
done

echo "=== determinism: the same smoke a second time ==="
for TASK in $(seq 0 9); do
  python3 hpc/herald93/run_model_benchmark.py --task-id "$TASK" \
    --out-dir hpc_results/herald93/smoke_b --n-zones 280 --n-score 6 --epochs 2 \
    --seeds 9301 --widths 64
done

python3 - <<'PY'
import json, pathlib, sys
a = sorted(pathlib.Path("hpc_results/herald93/smoke_a").glob("bench_*.json"))
b = sorted(pathlib.Path("hpc_results/herald93/smoke_b").glob("bench_*.json"))
assert len(a) == len(b) == 10, f"expected ten runs, found {len(a)} and {len(b)}"
bad = []
for left, right in zip(a, b):
    x, y = json.loads(left.read_text()), json.loads(right.read_text())
    for key in ("mae", "wmape", "skill_vs_persistence"):
        if abs(x["forecast"][key] - y["forecast"][key]) > 1e-9:
            bad.append(f"{left.name}:{key} {x['forecast'][key]} vs {y['forecast'][key]}")
    if x["relational"] and abs(x["relational"]["edge_f1"] - y["relational"]["edge_f1"]) > 1e-9:
        bad.append(f"{left.name}:edge_f1")
    grads = x.get("gradients", {})
    if x["method"] == "herald":
        for name in ("scorer", "relational_head", "fusion", "node_head"):
            assert grads.get(name, 0) > 0, f"{name} received no gradient"
        coverage = grads.get("coverage", [1.0] * len(grads["per_signal"]))
        # A signal that publishes nothing inside the probe window contributes nothing, by
        # design. Only the signals that *are* covered must show gradient.
        dead = [i for i, (gradient, seen) in enumerate(zip(grads["per_signal"], coverage))
                if seen > 0 and gradient <= 0]
        assert not dead, f"signal encoders {dead} are dead despite coverage {coverage}"
    if x["method"] != "persistence" and x["scenario"] == "S0_NULL":
        assert x["forecast"]["mae"] < 1.0, f"{x['method']} exploded on S0"
print("determinism failures:", bad or "none")
sys.exit(1 if bad else 0)
PY

echo "=== arms are distinct ==="
python3 - <<'PY'
import json, pathlib
runs = {}
for path in pathlib.Path("hpc_results/herald93/smoke_a").glob("bench_*.json"):
    r = json.loads(path.read_text())
    runs[(r["method"], r["scenario"])] = r
for scenario in ("S0_NULL", "S1_SHARED"):
    f1 = {m: runs[(m, scenario)]["relational"].get("edge_f1")
          for m in ("sparse_var", "mtgnn", "nri", "herald") if (m, scenario) in runs}
    mae = {m: runs[(m, scenario)]["forecast"]["mae"]
           for m in ("persistence", "sparse_var", "mtgnn", "nri", "herald")
           if (m, scenario) in runs}
    print(scenario, "edge_f1", {k: round(v, 4) for k, v in f1.items()})
    print(scenario, "mae     ", {k: round(v, 5) for k, v in mae.items()})
    values = [round(v, 6) for v in mae.values()]
    assert len(set(values)) > 1, f"{scenario}: every arm produced the same forecast"
PY

touch hpc_results/herald93/SMOKE_PASSED_${SLURM_JOB_ID}
echo "smoke passed"
