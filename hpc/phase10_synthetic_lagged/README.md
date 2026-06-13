# HERALD Phase 10 — HPC Infrastructure

**Decision:** DEC-043  
**Target cluster:** meso  
**Partition:** fast / QOS: fast  
**Conda env:** herald-v5  
**Remote path:** `~/project_recomm_herald_v6_2025_20260430/dataset`

## Array Spec

- Tasks: 0–19 (4 scenarios × 5 seeds = 20 tasks)
- Each task: all 15 models × 3 mask types × 3 mask levels
- Epochs: 500 (HPC), 200 (pilot)
- Time limit: 4h per task
- CPUs: 4 per task, 16G RAM

## Launch Sequence

```bash
# 1. Commit and push all code locally
git push origin main

# 2. Sync to meso (no --delete)
rsync -avz --exclude='*.pyc' --exclude='hpc_results/' --exclude='data/external/' \
    /home/jpdark/Downloads/project_recomm/dataset/ \
    meso:~/project_recomm_herald_v6_2025_20260430/dataset/

# 3. Smoke test on meso (1 task, 50 epochs)
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    conda run -n herald-v5 \
    python -m src.modeles.synthetic.run_phase10_benchmark \
    --smoke --output-dir hpc_results/phase10_synthetic_lagged --verbose"

# 4. Verify smoke output (exit 0, valid JSON, leakage PASS, NaN=0)
ssh meso "python -c \"
import json, sys
with open('~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase10_synthetic_lagged/linear_seed00042.json') as f:
    d = json.load(f)
assert d['leakage_check']['passed'], 'leakage FAIL'
print('JSON valid, leakage PASS')
print('manifest_version:', d['manifest_version'])
\""

# 5. Launch array (only after smoke PASS)
cd ~/project_recomm_herald_v6_2025_20260430/dataset
sbatch hpc/phase10_synthetic_lagged/run_phase10_meso.slurm
```

## Output

Results written to `hpc_results/phase10_synthetic_lagged/` (one JSON per task).
After collection, run gate evaluation:

```bash
python -m src.modeles.synthetic.gates_phase10 \
    hpc_results/phase10_synthetic_lagged/ \
    --out reports/phase10_gate_report.json
```

## Gates

L1 + L2 + L7 must PASS for HPC to be authorized (pre-specified in DEC-043).

## Collect and merge

```bash
# Rsync results back
rsync -avz meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/phase10_synthetic_lagged/ \
    hpc_results/phase10_synthetic_lagged/

# Run gates
python -m src.modeles.synthetic.gates_phase10 hpc_results/phase10_synthetic_lagged/ --pilot
```
