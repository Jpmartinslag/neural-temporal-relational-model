# Phase 9 — Synthetic Generalisation Benchmark (DEC-040)

## Purpose

Controlled synthetic benchmark to provide falsifiable evidence that HERALD graph-aware
imputation outperforms statistical baselines when recovering missing economic panel labels
with known ground truth.

Governed by a pre-specified, fail-closed contract (`reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md`).
**Do not adjust gate thresholds after observing results.**

---

## Task structure

- **Total tasks:** 20 (4 scenarios × 5 seeds)
- **Per task:** 12 models × 9 mask combos (3 types × 3 levels) = 108 evaluations
- **Array range:** `--array=0-19`
- **Scenarios:** `linear`, `nonlinear_heavy`, `mixed_default`, `generalization`
- **Seeds:** 42, 123, 456, 789, 1337
- **Mask types:** mcar, mar, block
- **Mask levels:** 10%, 30%, 50%

---

## Quick start

### Local pilot (mandatory before HPC submission)

```bash
python src/modeles/synthetic/run_full_benchmark.py \
  --local-pilot \
  --output-dir data/processed/synthetic_benchmark/pilot \
  --n-epochs 200
```

### Dry run (verify manifest, do not run)

```bash
python src/modeles/synthetic/run_full_benchmark.py --dry-run
```

### Single task (local test)

```bash
python src/modeles/synthetic/run_full_benchmark.py \
  --task-id 0 \
  --output-dir data/processed/synthetic_benchmark/test_task \
  --n-epochs 100
```

### Full benchmark (HPC — requires `--confirm-full-run`)

```bash
python src/modeles/synthetic/run_full_benchmark.py \
  --confirm-full-run \
  --output-dir data/processed/synthetic_benchmark/full \
  --n-epochs 500
```

---

## HPC submission (Slurm)

**Prerequisites (mandatory, in order):**

1. `run pilot locally — all 6 tasks PASS, no NaN, leakage=True`
2. `run all 86 tests — all PASS`
3. `rsync repo to cluster`
4. `smoke check on cluster: --task-id 0 --n-epochs 50`
5. `sbatch run_phase9.slurm`

**Commands:**

```bash
# 1. Sync to cluster
rsync -avz --exclude='data/external' --exclude='data/raw' \
  /home/jpdark/Downloads/project_recomm/dataset/ \
  CLUSTER_USER@CLUSTER_HOST:~/project_recomm/dataset/

# 2. Cluster smoke
ssh CLUSTER_USER@CLUSTER_HOST
cd ~/project_recomm/dataset
python src/modeles/synthetic/run_full_benchmark.py \
  --task-id 0 --n-epochs 50 \
  --output-dir data/processed/synthetic_benchmark/cluster_smoke

# 3. Submit (only after smoke PASS)
sbatch hpc/phase9_synthetic_generalization/run_phase9.slurm
```

---

## Output

Each task writes one JSON to `--output-dir`:

```
linear_seed00042.json
linear_seed00123.json
...
generalization_seed01337.json
```

**JSON structure:**
```json
{
  "scenario": "linear",
  "seed": 42,
  "config_hash": "...",
  "leakage_check": {"passed": true},
  "baselines": {
    "mcar_10": {
      "mean": {"mae": 0.25, "rmse": 0.31, ...},
      "herald_graph": {"mae": 0.21, "edge_auc": 0.65, ...},
      ...
    }
  }
}
```

---

## Post-run evaluation

```bash
# Evaluate gates on all 20 results
python -c "
import json, glob, sys
sys.path.insert(0, '.')
from src.modeles.synthetic.gates import evaluate_gates

results = []
for f in sorted(glob.glob('data/processed/synthetic_benchmark/full/*.json')):
    d = json.load(open(f))
    for mask_combo, bl in d['baselines'].items():
        if isinstance(bl, dict) and 'herald_graph' in bl:
            results.append({
                'seed': d['seed'],
                'scenario': d['scenario'],
                'mask_type': bl.get('mask_type', mask_combo.split('_')[0]),
                'leakage_check': d.get('leakage_check', {'passed': True}),
                'baselines': bl,
            })
for scenario in ['mixed_default', 'linear', 'nonlinear_heavy', 'generalization']:
    subset = [r for r in results if r['scenario'] == scenario]
    if subset:
        verdict = evaluate_gates(subset, scenario=scenario)
        print(f'=== {scenario} ===')
        print(verdict.summary())
"
```

---

## Estimated runtime

| Unit | Time |
|------|------|
| 1 task (1 scenario × 1 seed, 500 epochs) | ~8–12 min CPU |
| 20 tasks sequential | ~3–4 h CPU |
| 20 tasks parallel (20 cores) | ~12–15 min wall |

**Memory:** < 2 GB RAM per task (30T × 9S × 20Y panels)

---

## Files

| File | Description |
|------|-------------|
| `run_phase9.slurm` | Slurm array job script |
| `src/modeles/synthetic/run_full_benchmark.py` | Main runner |
| `src/modeles/synthetic/gates.py` | Fail-closed gate evaluation |
| `reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md` | Sealed contract |

---

## Safety rules

- **Do not submit the full array without explicit authorisation.**
- **Do not adjust gate thresholds after observing any results.**
- **Do not use force push.**
- Atomic writes: each task writes `.tmp` then renames → safe against partial-write corruption.
- Resume: re-running an already-completed task is a no-op (valid JSON detected).
