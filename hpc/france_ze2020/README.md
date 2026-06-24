# France ZE2020 — HPC Infrastructure

**Status:** SPEC_READY, **NOT LAUNCHED**. Full spec: `reports/canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md`.
Local training-block plan and audit: `reports/canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md`.

**Target cluster:** `meso` (`ssh meso`, alias resolves via `~/.ssh/config`, `ProxyJump mesoext`).
**Conda env:** `herald-v5` (`~/.conda/envs/herald-v5/bin/python` -- sklearn/pandas/numpy
only, no torch needed for this track).
**Remote path:** `~/project_recomm_herald_v6_2025_20260430/dataset` (rsync-synced,
**not** a git checkout on the remote).

## What this runs

5 seeds (`42, 43, 44, 45, 46`) x the 4 existing FR ZE2020 training scripts
(`train_fr_ze2020_baselines.py`, `train_fr_ze2020_relational_baselines.py`,
`train_fr_ze2020_neural_relational_mlp.py`, `train_fr_ze2020_sector_graph_prototype.py`)
-- no new model. Persistence/Ridge are deterministic (seed-independent); only the two
sklearn `MLPRegressor`-based scripts vary by seed. Purpose: test whether the smoke
result (no relational/neural model beat its baseline with a single seed) holds, and
collect `feature_signals`/`relation_signals` across seeds to assess stability (H3).

## Files

| File | Purpose |
|---|---|
| `run_fr_ze2020_hpc_task.sh` | One seed's work: runs the 4 scripts via their own CLIs, writes to `seed_<N>/` |
| `run_fr_ze2020_hpc_array.sbatch` | Slurm array `0-4`, maps array index to seed, calls the task script |
| `submit_fr_ze2020_hpc.sh` | Prepares + validates the submission; only calls `sbatch` with `--confirm-submit` |
| `smoke_test_fr_ze2020_hpc.sh` | 1 seed, 20 epochs, 2 eval years -- runs directly (no `sbatch`), must pass first |
| `audit_fr_ze2020_hpc_results.py` | Post-collection: computes gates G1-G5 (descriptive only, no auto-promotion) |

## Sequence

```bash
# 1. Sync local -> meso (no --delete, never touches hpc_results/ or data/external/)
rsync -avz --exclude='*.pyc' --exclude='hpc_results/' --exclude='data/external/' \
    /home/jpdark/Downloads/project_recomm/dataset/ \
    meso:~/project_recomm_herald_v6_2025_20260430/dataset/

# 2. Smoke test on meso (no sbatch, plain python, ~seconds)
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/smoke_test_fr_ze2020_hpc.sh"

# 3. Dry-run the submit (prints the sbatch command, does not submit)
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh"

# 4. Real submit -- ONLY with explicit human confirmation
ssh meso "cd ~/project_recomm_herald_v6_2025_20260430/dataset && \
    bash hpc/france_ze2020/submit_fr_ze2020_hpc.sh --confirm-submit"

# 5. Monitor
ssh meso "squeue -u \$USER"

# 6. Collect (replace <RUN_ID> with the timestamp submit_fr_ze2020_hpc.sh printed)
rsync -avz \
    meso:~/project_recomm_herald_v6_2025_20260430/dataset/hpc_results/fr_ze2020_hpc_<RUN_ID>/ \
    hpc_results/fr_ze2020_hpc_<RUN_ID>/

# 7. Audit (descriptive gates G1-G5, human decides what to do with them)
python3 hpc/france_ze2020/audit_fr_ze2020_hpc_results.py \
    hpc_results/fr_ze2020_hpc_<RUN_ID>/ --out reports/metrics/fr_ze2020_hpc_<RUN_ID>_gate_report.json
```

## Budget

5 tasks x ~2-3 min each (sector-graph build dominates), `--cpus-per-task=4`,
`--mem=8G`, `--time=00:30:00`, partition/QOS `fast`/`fast`. No GPU, no torch.
Estimated total: <15 min of cluster time.

## Rules (per HERALD_19 section 9)

- No causal claim. `relation_signals`/`feature_signals` are observed association,
  never an effect.
- No automatic recommendation. No `recommendation` column anywhere in this pipeline
  (enforced by gate G5 and by each script's own tests).
- No final performance claim. Even a G3 PASS (candidate beats baseline in >=3/5
  seeds) authorizes discussing next steps, not a conclusion that the model "works."
- Never reads `dynamic_stgnn_feature_panel*` or `graph_adjacency_core_v0.csv`/
  `graph_adjacency_mobility_v0.csv` (re-checked at runtime by `run_fr_ze2020_hpc_task.sh`,
  in addition to each script's own test suite).
- Output writes are confined to `hpc_results/fr_ze2020_hpc_<RUN_ID>/` -- never the
  dashboard, never `data/external/`, never Italy/Austria, never the legacy
  `train_herald_v6/v7/semi_v2/regime_experiment` scripts.
