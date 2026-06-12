# HERALD HPC Organization Audit

**Date:** 2026-06-12
**Scope:** `hpc/` and `hpc_results/` directory taxonomy, Phase 6 registration, path collision audit
**Decision:** INDEX_FIRST — no existing files moved; Phase 6 directories created

---

## 1. Findings by Severity

### INFO — No breaking changes
- All existing files left in place. Index + registry documents the mapping without moving anything.

### INFO — Phase 6 directories created (new, empty)
- `hpc/phase6_dynamic_dual_graph/{scripts/,configs/,audits/,README.md}`
- `hpc_results/phase6_dynamic_dual_graph/{pilot/,smoke/,full/,logs/}`

### LOW — `hpc/research/` not categorized in prior README
- `hpc/research/` contains exploratory V7/showdown scripts that are not in any scientific track.
- Not moved; flagged as safe to archive eventually.

### LOW — `hpc_results/` naming is flat (not phase-prefixed)
- Legacy runs use per-run timestamps (`herald_phase4e_a_fr_20260531_*`) not phase prefixes.
- Migration BLOCKED by hardcoded globs in `src/visualisation/generate_herald_phase4_dashboard.py`.
- Documented in `hpc/HPC_PATH_MIGRATION_PLAN.md`; deferred.

### LOW — Three hardcoded `DEFAULT_*` paths in src/
- `src/modeles/train_temporal_baselines_v1.py:30` → `hpc_results/final_model_comparison_20260429/temporal_baselines`
- `src/visualisation/plot_herald_v6_2025_dashboard.py:26` → `hpc_results/herald_v6_observed2025_20260430_142920`
- `src/visualisation/generate_herald_geo2025_dashboard.py:19` → `hpc_results/herald_semi_total_253_geo2025`
- Not moved; paths are still valid. Document as blocked in migration plan.

### LOW — Phase 5 has `__init__.py` (Python package)
- `hpc/phase5/__init__.py` makes the directory a Python package importable by `run_phase5_job.py`.
- Moving phase5 would break the import. Documented; NOT_SUPPORTED so no action needed.

---

## 2. Taxonomy Adopted

```text
CANONICAL MAPPING (target ← current)
─────────────────────────────────────────────────────────────────────────────────
hpc/phase3_data_features/           ← hpc/regime/ + hpc/validation/    [deferred]
hpc/phase4_forecasting/
  geographic_graph/                 ← hpc/phase4/                       [deferred]
  harmonized_loco/                  ← hpc/phase4/ (phase4n/4o subset)   [deferred]
hpc/phase5_fixed_graph_correction/  ← hpc/phase5/                       [deferred]
hpc/phase6_dynamic_dual_graph/      ← NEW — CREATED 2026-06-12          [active]
  scripts/
  configs/
  audits/
─────────────────────────────────────────────────────────────────────────────────
hpc_results/phase3_data_features/   ← hpc_results/herald_regime_*       [deferred]
hpc_results/phase4_forecasting/
  geographic_graph/                 ← hpc_results/herald_phase4*        [deferred]
  harmonized_loco/                  ← hpc_results/herald_phase4n_*/4o_* [deferred]
hpc_results/phase5_fixed_graph_correction/ ← no local results           [N/A]
hpc_results/phase6_dynamic_dual_graph/     ← NEW — CREATED 2026-06-12  [active]
  pilot/ smoke/ full/ logs/
```

All "deferred" items are BLOCKED by hardcoded path references (see §5).
Phase 6 is the only category where the canonical structure is live.

---

## 3. Phase Inventory Summary

| ID | Phase | Dir(s) | Status | Notes |
|----|-------|--------|--------|-------|
| P2P3_REGIME_FRANCE | France Regime Phase 2+3 | `hpc/regime/` | frozen | Q7_effectifs_lag1 selected (Phase 3E) |
| P2P3_SEMIV2_VALIDATION | Semi V2 Validation | `hpc/validation/` | frozen | Dashboard stable |
| P_AUDIT_EXANTE | Cross-phase Audit | `hpc/audit/` | frozen | Strict ex-ante + leak stress |
| P_FORECAST_2026_2027 | Prospective Forecast | `hpc/forecast/` | frozen | 2026/2027 France |
| P4_GEO_GRAPH | Geographic Graph Phase 4 | `hpc/phase4/` | frozen/FAIL | 4A-D leaky; 4E+ causal; 4P/4Q FAIL |
| P4_HARMONIZED_LOCO | Harmonized LOCO | `hpc/phase4/` (subset) | frozen | IT PASS; PT/AT FAIL; 4P NOT authorized |
| P5_FIXED_GRAPH_CORRECTOR | Fixed L2 Corrector | `hpc/phase5/` | NOT_SUPPORTED | NL ablation FAIL; H0b remains best |
| P_RESEARCH_EXPLORATORY | V7/Showdown | `hpc/research/` | exploratory | Not in main track |
| **P6_DDEG_S1** | **Dynamic Dual Graph** | **`hpc/phase6_dynamic_dual_graph/`** | **ACTIVE** | HPC not yet launched |

**Phase 4P (geographic spatial-lag, Italy):** FAIL — p=.19, wins 4/9 years vs persistence.
**Phase 4Q (geographic spatial-Durbin, Italy):** FAIL — p=.32, −5.95% vs persistence.
**Geographic queen-contiguity branch CLOSED** (2026-06-10).

**Phase 5 (L2 fixed-graph neural corrector):** NOT_SUPPORTED — H2-neural WMAPE 5.53% vs H0b 3.41%;
fails regression gate (>H0b×1.10=3.75%); H2 WORSE than H1-neural; DEC-023.

**Phase 6 pilot (5 folds × 11 controls × 2 seeds = 110 runs):**
Gate preliminary: DUAL_GRAPH_S1_FAIL — 6/7 criteria fail; only c6_no_fold_regression passes.
`data/processed/dual_graph_pilot_all_folds/gate_result.json`.
Full study (5×11×5=275 jobs): NOT YET LAUNCHED.

---

## 4. Files Created / Modified

| Action | Path |
|--------|------|
| CREATED | `hpc/HPC_PHASE_INDEX.md` |
| CREATED | `hpc/HPC_PATH_MIGRATION_PLAN.md` |
| CREATED | `hpc/hpc_phase_registry.json` |
| CREATED | `hpc/phase6_dynamic_dual_graph/README.md` |
| CREATED | `hpc/phase6_dynamic_dual_graph/scripts/` (empty dir) |
| CREATED | `hpc/phase6_dynamic_dual_graph/configs/` (empty dir) |
| CREATED | `hpc/phase6_dynamic_dual_graph/audits/` (empty dir) |
| CREATED | `hpc_results/phase6_dynamic_dual_graph/pilot/` (empty dir) |
| CREATED | `hpc_results/phase6_dynamic_dual_graph/smoke/` (empty dir) |
| CREATED | `hpc_results/phase6_dynamic_dual_graph/full/` (empty dir) |
| CREATED | `hpc_results/phase6_dynamic_dual_graph/logs/` (empty dir) |
| MODIFIED | `hpc_results/README.md` — Phase 6 section added |
| MODIFIED | `CODEX_MEMORY.md` — Phase 6 active state, HPC taxonomy |
| CREATED | `reports/HERALD_HPC_ORGANIZATION_AUDIT.md` (this file) |

No existing file was deleted, renamed, or moved.

---

## 5. Hardcoded Paths Found

All paths listed are BLOCKED from migration. Full details in `hpc/HPC_PATH_MIGRATION_PLAN.md`.

```
src/modeles/train_temporal_baselines_v1.py:30
  → DEFAULT_OUT = ROOT / "hpc_results/final_model_comparison_20260429/temporal_baselines"

src/visualisation/plot_herald_v6_2025_dashboard.py:26
  → DEFAULT_HPC = ROOT / "hpc_results/herald_v6_observed2025_20260430_142920"

src/visualisation/generate_herald_geo2025_dashboard.py:19
  → BASE = os.path.join(ROOT,"hpc_results","herald_semi_total_253_geo2025")

src/visualisation/generate_herald_phase4_dashboard.py:43,62,81
  → "hpc_glob": "hpc_results/herald_phase4c_{nl,be,pt}_*"

src/visualisation/generate_herald_phase4_dashboard.py:1145,1311
  → "hpc/phase4/submit_herald_phase4_{ck}.sh"

hpc/regime/submit_herald_regime_discovery.sh:25,29,32,40,50
  → calls hpc/regime/{run_herald_regime_array.sbatch, audit_herald_regime_plan.py, ...}

hpc/regime/submit_herald_phase*.sh
  → source hpc/regime/submit_herald_phase_template.sh

hpc/phase5/run_phase5_job.py (BASE-relative)
  → src/modeles/phase5/

src/modeles/train_dual_graph_experiment.py:64
  → TENSOR_DIR = BASE / "data/processed/dual_graph_tensors"

src/modeles/train_dual_graph_experiment.py:66
  → DEFAULT_OUT = BASE / "data/processed/dual_graph_s1"
```

---

## 6. What Was Effectively Moved or Created

Nothing was moved. The following were created:

- `hpc/phase6_dynamic_dual_graph/` directory tree (scripts, configs, audits, README)
- `hpc_results/phase6_dynamic_dual_graph/` directory tree (pilot, smoke, full, logs)
- `hpc/HPC_PHASE_INDEX.md` — navigation index
- `hpc/HPC_PATH_MIGRATION_PLAN.md` — migration rules and blocked items
- `hpc/hpc_phase_registry.json` — machine-readable phase registry
- `reports/HERALD_HPC_ORGANIZATION_AUDIT.md` — this file

---

## 7. Validations

```
python3 -m json.tool hpc/hpc_phase_registry.json >/dev/null  → VALID
git diff --check                                               → CLEAN
rg -n "hpc/phase4|hpc_results/herald_phase|phase5|dual_graph" README.md CODEX_MEMORY.md → verified; no orphaned references
```

No script was deleted. No output was duplicated. No import was broken. No Slurm command was executed.
Phase 6 is clearly separated from all prior phases. Future HPC paths for smoke, pilot, full, and logs
are defined. Migration plan documents what can and cannot be moved later.

---

## 8. Next Exact Step for P6_DDEG_S1

Create the HPC array job scripts in `hpc/phase6_dynamic_dual_graph/scripts/`:

1. `run_dual_graph_array.sbatch` — Slurm array header, env setup, calls task runner
2. `run_dual_graph_task.py` — single-job runner: decode SLURM_ARRAY_TASK_ID → (fold, control, seed); call trainer; write atomic JSON to `hpc_results/dual_graph_s1/raw/`
3. `submit_dual_graph_full.sh` — pre-flight checks + `sbatch` call
4. `audit_dual_graph_hpc_results.py` — post-run aggregation and gate application

Followed by:
- Local gauntlet (py_compile, pytest, bash -n)
- SSH remote probe (Python versions, torch import)
- Targeted rsync (src/modeles/dual_graph_models.py, train_dual_graph_experiment.py, hpc/phase6_dynamic_dual_graph/, data/processed/dual_graph_tensors/)
- Remote py_compile
- Remote smoke (FR/2021, C5_dual, seed=42, 5 epochs)
- Remote Slurm smoke (--array=0-0)
- Array submit (--array=0-274%20)
- Commit and push HPC scripts (NOT results)

---

## 9. Files Proposed for Commit

```
hpc/HPC_PHASE_INDEX.md
hpc/HPC_PATH_MIGRATION_PLAN.md
hpc/hpc_phase_registry.json
hpc/phase6_dynamic_dual_graph/README.md
hpc_results/README.md
reports/HERALD_HPC_ORGANIZATION_AUDIT.md
CODEX_MEMORY.md
```

Excluded: empty directories (Git does not track them; add `.gitkeep` if needed).
