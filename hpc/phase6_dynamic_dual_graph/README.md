# Phase 6 — Dynamic Dual Economic Graph (P6_DDEG_S1)

**Status:** FROZEN/FAIL — full study COMPLETE; gate DUAL_GRAPH_S1_FAIL (all 7 criteria fail)
**Experiment ID:** P6_DDEG_S1
**Scope:** France NUTS3 · 101 regions · 9 A10 sectors · eval years 2021–2025

## Experiment Description

Two-graph representation learning experiment.

- **Territory graph:** observed causal dynamic (per-sector NUTS3 co-growth adjacency, input tensor)
- **Sector graph:** learned sparse symmetric (sparsity + temporal-stability regularized)

Targets: sector log-growth · regime · recovery · emergence
Claims: association and early-warning only. NOT a forecast improvement claim.
Gate: fail-closed, §9 of `reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md`.

## Key Files (outside this directory)

| File | Role |
|------|------|
| `src/modeles/train_dual_graph_experiment.py` | Frozen trainer (commit `9521264`) |
| `src/modeles/dual_graph_models.py` | Frozen model (≤10,000 params) |
| `data/processed/dual_graph_tensors/` | Frozen tensors (5 folds, FR 2021–2025) |
| `data/processed/dual_graph_pilot_all_folds/` | Pilot results — gate DUAL_GRAPH_S1_FAIL |
| `reports/HERALD_DUAL_GRAPH_EXPERIMENT_CONTRACT.md` | Frozen contract |
| `reports/HERALD_DUAL_GRAPH_TRAINER_AUDIT.md` | Trainer audit — READY |

## Full Study Result (5 folds × 11 controls × 5 seeds = 275 runs)

**Slurm job:** 7453691 — 275/275 COMPLETED, 0 FAILED
**Date completed:** 2026-06-12

```json
{
  "decision": "DUAL_GRAPH_S1_FAIL",
  "c1_mae_improve": false,
  "c2_macro_f1_margin": false,
  "c3_recovery_aucpr_folds": false,
  "c4_graph_beats_nulls_folds": false,
  "c5_seed_jaccard": false,
  "c6_no_fold_regression": false,
  "c7_holds_without_2021": false
}
```

All 7 criteria fail. C5_dual MAE 0.1424 vs C1_ridge 0.1242 (+14.6%) and C2_no_graph 0.1329 (+7.2%).
Seed Jaccard 0.3353 (threshold 0.50). Worst fold (2023): +17.4% vs C2.

Predictive dual-graph branch CLOSED per contract §9. Do NOT relaunch without documented
operational failure in protocol or data integrity (not in model performance).

## Stable Sector Edges (Descriptive Only — NOT Predictively Validated)

| Sector pair | Stability | Notes |
|-------------|-----------|-------|
| C ↔ KZ | 0.80 | 20/25 fold×seed runs |
| FZ ↔ HZ | 0.76 | 19/25 fold×seed runs |
| HZ ↔ KZ | 0.76 | 19/25 fold×seed runs |
| AZ ↔ DE | 0.72 | 18/25 fold×seed runs |
| AZ ↔ GI | 0.72 | 18/25 fold×seed runs |

These are optimization artifacts from a FAILED gate. No causal or recommendation claims permitted.

## Pilot Result (5 folds × 11 controls × 2 seeds = 110 runs) — superseded

The pilot (2 seeds) had c6_no_fold_regression=true. The full study (5 seeds) has c6=false.
The 2023 fold failure (+17.4% vs C2) was masked by seed variance in the pilot.
Full study is confirmatory; pilot result is superseded.

## HPC Output Layout

```text
hpc_results/phase6_dynamic_dual_graph/
├── smoke/     ← remote smoke test (before array submit)
├── full/      ← array output: one JSON per (fold, control, seed)
└── logs/      ← Slurm .out / .err files
```

Or, if using the flat structure from the array job:
```text
hpc_results/dual_graph_s1/raw/{control}__fr{fold}__seed{seed}.json
```

## Controls (11 total, 5 seeds × 5 folds = 275 jobs)

C0_persistence · C1_ridge · C2_no_graph · C3_territory_only · C4_sector_only
C5_dual · C6_territory_temporal_perm · C7_territory_graph_perm
C8_sector_identity_perm · C9_no_ardeco · C10_ardeco_temporal_perm

## Frozen Hyperparameters

hidden_dim=8 · lr=1e-3 · weight_decay=1e-4 · max_epochs=200 · patience=20
ridge_alpha=10.0 · topk_sector=3 · seeds [42–46]

## Slurm Resources (initial estimate)

`--array=0-274%20 --cpus-per-task=1 --mem=4G --time=00:30:00 --constraint=mpi`
Adjust only after smoke confirms runtime and memory.
