# HPC Phase Index — HERALD

**Last updated:** 2026-06-12
**Registry:** `hpc/hpc_phase_registry.json`

This index maps scientific phases to their HPC scripts and result directories.
Do not move anything without consulting `HPC_PATH_MIGRATION_PLAN.md`.

---

## Active Phase

| ID | Phase | Status | Scripts | Results |
|----|-------|--------|---------|---------|
| **P7_SECTOR_PRECEDENCE** | Phase 7 — Sector Precedence Distributed Study | **READY_FOR_HPC** | `hpc/phase7_sector_precedence/` | `hpc_results/phase7_sector_precedence/` |

710 tasks (FR=198, NL=288, PT=224). Panel: `herald_observatory_v02`, 45,945 rows.
Predictive precedence (associative), not structural causality. Pre-registered gates frozen (DEC-033).
Submit: `sbatch hpc/phase7_sector_precedence/scripts/run_sector_precedence_array.sbatch`

---

## Frozen / Completed Phases

| ID | Phase | Status | Scripts | Key result |
|----|-------|--------|---------|------------|
| P6_DDEG_S1 | Phase 6 — Dynamic Dual Economic Graph | **frozen/FAIL** | `hpc/phase6_dynamic_dual_graph/` | `hpc_results/dual_graph_s1/raw/` |
| P2P3_REGIME_FRANCE | Phase 2+3 — Regime France | frozen | `hpc/regime/` | `hpc_results/herald_regime_phase3e_*` |
| P2P3_SEMIV2_VALIDATION | Phase 2+3 — Semi V2 Validation | frozen | `hpc/validation/` | `hpc_results/herald_semi_total_253_geo2025` |
| P_AUDIT_EXANTE | Cross-phase Audit | frozen | `hpc/audit/` | `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` |
| P_FORECAST_2026_2027 | Prospective Forecast 2026-2027 | frozen | `hpc/forecast/` | `hpc_results/herald_v6_observed2025_*` |
| P4_GEO_GRAPH | Phase 4 — Geographic Graph | **frozen/FAIL** | `hpc/phase4/` | `hpc_results/herald_phase4p_*` / `herald_phase4q_*` |
| P4_HARMONIZED_LOCO | Phase 4N/4O-C — Harmonized LOCO | frozen | `hpc/phase4/` (run_phase4n_*) | `hpc_results/herald_phase4n_a_local_r1` |
| P5_FIXED_GRAPH_CORRECTOR | Phase 5 — Fixed L2 Corrector | **NOT_SUPPORTED** | `hpc/phase5/` | *(no local results)* |
| P_RESEARCH_EXPLORATORY | Research V7/Showdown | exploratory | `hpc/research/` | *(not persisted)* |

---

## Phase 4 Sub-phase Notes

Phase 4A–D are **leaky** (`growth_1y[t]` used `target[t]`). Scientific baseline starts at Phase 4E-A.
Phase 4P (Italy spatial-lag) and Phase 4Q (Italy Spatial-Durbin) both FAIL. Geographic graph CLOSED.

---

## HPC Infrastructure

| Directory | Purpose |
|-----------|---------|
| `hpc/tools/` | rsync, env setup scripts |
| `hpc/archive/legacy_runs/` | V3-V6 historical scripts (read-only) |

SSH alias: `meso` (resolves via `~/.ssh/config`, not committed here — see `hpc/france_ze2020/README.md`)
Remote base: `~/project_recomm_herald_v6_2025_20260430/dataset` (relative to the remote account's own home)
Slurm constraint: `#SBATCH --constraint=mpi`

---

## Phase 6 Directory Layout

```text
hpc/phase6_dynamic_dual_graph/
├── scripts/          # Slurm array job, task runner, submit wrapper
├── configs/          # frozen hyperparameter configs for HPC run
└── audits/           # local audit scripts for HPC results

hpc_results/phase6_dynamic_dual_graph/
├── pilot/            # reduced-budget pilot outputs (5 folds × 11 controls × 2 seeds)
├── smoke/            # remote smoke test outputs
├── full/             # full array outputs (5 folds × 11 controls × 5 seeds = 275 jobs)
└── logs/             # Slurm .out / .err files
```

Note: the local pilot ran in `data/processed/dual_graph_pilot_all_folds/` (not `hpc_results/`).
HPC outputs should write to `hpc_results/phase6_dynamic_dual_graph/full/` or a flat
`hpc_results/dual_graph_s1/raw/` structure as specified by the job script.
