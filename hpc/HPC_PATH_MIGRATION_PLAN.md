# HPC Path Migration Plan — HERALD

**Date:** 2026-06-12
**Status:** Index-first (no files moved yet)

This document records what can and cannot be moved, and the rationale for each decision.
Moving anything listed as BLOCKED requires resolving the listed dependency first.

---

## Canonical Target Taxonomy

```text
hpc/
  phase3_data_features/        ← maps to current: hpc/regime/ (partial)
  phase4_forecasting/
    geographic_graph/          ← maps to current: hpc/phase4/
    harmonized_loco/           ← maps to current: hpc/phase4/ (phase4n/4o-c subset)
  phase5_fixed_graph_correction/ ← maps to current: hpc/phase5/
  phase6_dynamic_dual_graph/   ← NEW (created 2026-06-12)
    scripts/
    configs/
    audits/

hpc_results/
  phase3_data_features/        ← maps to current: hpc_results/herald_regime_*
  phase4_forecasting/
    geographic_graph/          ← maps to current: hpc_results/herald_phase4*
    harmonized_loco/           ← maps to current: hpc_results/herald_phase4n_*/herald_phase4o_*
  phase5_fixed_graph_correction/ ← no results to move
  phase6_dynamic_dual_graph/   ← NEW (created 2026-06-12)
    pilot/
    smoke/
    full/
    logs/
```

---

## Items: MUST NOT MOVE (blocking dependencies)

| Current path | Reason blocked |
|---|---|
| `hpc/phase4/` (entire directory) | Referenced by `README.md` (lines 441-471), `CODEX_MEMORY.md` (lines 69-72, 276), and `src/visualisation/generate_herald_phase4_dashboard.py` (hardcoded `hpc/phase4/submit_herald_phase4_{ck}.sh` strings). All scripts use `BASE = Path(__file__).resolve().parents[2]` for src/ imports — moving breaks nothing in Python, but the `.sh` launchers call each other by relative path. |
| `hpc/regime/` (entire directory) | Scripts call each other by relative path (`source hpc/regime/submit_herald_phase_template.sh`, `bash hpc/regime/...`). `hpc/regime/submit_herald_regime_discovery.sh` calls multiple sub-scripts. Moving would break all shell-level composition. |
| `hpc/audit/` | Scripts call each other by relative path (`source`). Audit results referenced in reports. |
| `hpc/validation/` | Results referenced externally; shell scripts call each other. |
| `hpc/phase5/` | `hpc/phase5/__init__.py` present (Python package). `run_phase5_job.py` imports `src/modeles/phase5/`. Results document the NOT_SUPPORTED decision (DEC-023). |
| `hpc_results/herald_v6_observed2025_20260430_142920` | Hardcoded as `DEFAULT_HPC` in `src/visualisation/plot_herald_v6_2025_dashboard.py:30`. |
| `hpc_results/herald_semi_total_253_geo2025` | Hardcoded in `src/visualisation/generate_herald_geo2025_dashboard.py:19`. |
| `hpc_results/final_model_comparison_20260429` | Hardcoded as `DEFAULT_OUT` in `src/modeles/train_temporal_baselines_v1.py:30`. |
| `data/processed/dual_graph_tensors/` | Path hardcoded as `TENSOR_DIR` in `train_dual_graph_experiment.py:64`. Cannot move without editing the trainer. |
| `data/processed/dual_graph_pilot_all_folds/` | Gate result JSON and leakage audit frozen at this path; referenced in trainer audit report. |
| `src/modeles/train_dual_graph_experiment.py` | Imported by `run_dual_graph_pilot.py`, `run_dual_graph_smoke.py`, and 44 tests. Module-level; cannot be moved to `hpc/` without breaking all imports. |

---

## Items: SAFE TO MOVE (no external dependencies found)

| Current path | Target path | Condition |
|---|---|---|
| `hpc/research/` | `hpc/archive/research/` | No src/ imports found; no hardcoded result paths. Verify with `rg -n "hpc/research" src/ tests/ reports/ README.md CODEX_MEMORY.md` first. |
| `hpc/archive/legacy_runs/` | Already archived; rename not needed | Safe to leave as-is. |

---

## Items: CONDITIONAL (safe after fixing dependency)

| Current path | Target path | Condition to satisfy |
|---|---|---|
| `hpc/regime/` | `hpc/phase3_data_features/` | Only after all shell scripts updated to use new relative paths and `CODEX_MEMORY.md`/`README.md` paths updated. High effort, low benefit. Not recommended until Phase 2+3 track is fully archived. |
| `hpc/phase4/` | `hpc/phase4_forecasting/geographic_graph/` | Only after README.md, CODEX_MEMORY.md, and generate_herald_phase4_dashboard.py updated. High effort. Not recommended. |
| `hpc_results/herald_phase4*` | `hpc_results/phase4_forecasting/geographic_graph/` | Only after `generate_herald_phase4_dashboard.py` glob patterns updated and tested. |

---

## Items: ALREADY IN CORRECT LOCATION

| Path | Notes |
|---|---|
| `hpc/phase6_dynamic_dual_graph/` | Created 2026-06-12; canonical target location. |
| `hpc_results/phase6_dynamic_dual_graph/` | Created 2026-06-12; canonical target location. |
| `hpc/tools/` | Infrastructure; no phase mapping needed. |

---

## Recommendation

**Do not rename existing directories now.** The benefit of strict canonical naming is outweighed by
the risk of breaking references across README, CODEX_MEMORY, visualisation scripts, and shell
composition. The index (`HPC_PHASE_INDEX.md`) and registry (`hpc_phase_registry.json`) provide the
semantic mapping without moving any file.

**When to actually move:** Only if a phase enters a new active HPC run that requires the canonical
path, and all dependents have been updated and tested. Always verify with:

```bash
rg -n "<path_being_moved>" src/ tests/ reports/ README.md CODEX_MEMORY.md hpc/ --include="*.py" --include="*.sh" --include="*.md"
```

---

## Hardcoded Path Inventory (full list found by `rg`)

```
src/modeles/train_temporal_baselines_v1.py:30  → hpc_results/final_model_comparison_20260429/temporal_baselines
src/visualisation/plot_herald_v6_2025_dashboard.py:26 → hpc_results/herald_v6_observed2025_20260430_142920
src/visualisation/generate_herald_geo2025_dashboard.py:19 → hpc_results/herald_semi_total_253_geo2025
src/visualisation/generate_herald_phase4_dashboard.py:43,62,81 → hpc_results/herald_phase4c_{nl,be,pt}_*
src/visualisation/generate_herald_phase4_dashboard.py:1145,1311 → hpc/phase4/submit_herald_phase4_{ck}.sh
hpc/regime/submit_herald_regime_discovery.sh → hpc/regime/{audit,aggregate,run}*.py (relative calls)
hpc/regime/submit_herald_phase*.sh → hpc/regime/submit_herald_phase_template.sh (source)
hpc/phase4/phase4*_configs.sh → called by sbatch scripts via relative path
hpc/phase5/run_phase5_job.py → src/modeles/phase5/ (BASE-relative)
train_dual_graph_experiment.py:64 → data/processed/dual_graph_tensors
train_dual_graph_experiment.py:66 → data/processed/dual_graph_s1 (DEFAULT_OUT)
```
