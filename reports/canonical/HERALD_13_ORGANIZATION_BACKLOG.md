# HERALD 13 — Organization Backlog

**Created:** 2026-06-18 (post-consolidation organizational backlog).
**Status:** This is a **backlog of organizational debt**, not a scientific document.
Nothing here is a result, claim, or DEC. It records what still needs a human decision
or a future pass — `reports/canonical/01-12` remain the science/structure base; this
document tracks open chores against that base.
**Method:** identified via `git status --short` (untracked/modified worktree state) and
the structural maps in canonicals #9/#10/#11. Nothing was moved, renamed, deleted, or
`git rm`'d to produce this list.

---

## 1. Worktree — uncommitted/untracked changes not addressed by this pass

These are pre-existing in the working tree, untouched by any of the recent
documentation passes. They need their own review before being committed or discarded.

| Path/pattern | Type | Risk | Recommended future action | Needs human decision? |
|---|---|---|---|---|
| `src/data/european_panel/` (modified: `adapters/it_adapter.py`, `build_enterprise_birth_subpanel.py`), `src/data/ingest_italy_panel.py` | CODE | MEDIUM | Review diff, decide if it's a fix to commit or in-progress work | Yes |
| `src/modeles/train_herald_regime_experiment.py`, `train_herald_semi_v2.py`, `train_herald_v6.py`, `train_herald_v7.py` (modified) | CODE | LOW (historical/superseded models) | Confirm these are inert edits (e.g. comment/lint) before committing; these scripts are HISTORICAL_EXPERIMENT per canonical #10 | Yes |
| `src/data/ingest_eurostat_enterprise_birth_panel.py`, `src/modeles/herald_fold_controls.py`, `src/modeles/run_ardeco_ridge_fr.py` (untracked, new) | CODE | MEDIUM | Determine if these are finished work to add, or scratch files | Yes |
| `scripts/` (untracked dir) | CODE | LOW | Inventory contents, classify (utility vs scratch) | Yes |
| `tests/__init__.py`, `tests/test_ardeco_fr_extension.py`, `test_ardeco_ridge_fr.py`, `test_build_fr_nuts3_sector_panel.py`, `test_dual_graph_targets.py`, `test_dual_graph_tensors.py`, `test_eurostat_jsonstat.py`, `test_g1_l1_sector_graph.py`, `test_g1_observable_graph.py`, `test_phase4o_spatial.py`, `test_phase4p_italy_spatial_lag.py`, `test_phase4q_italy_spatial_durbin.py` (untracked) | CODE | MEDIUM | Run and confirm green before committing; some target CLOSED branches (dual_graph, 4P/4Q) — committing tests for closed branches is fine for traceability but should be a deliberate choice | Yes |
| `data/external/austria/`, `data/external/eurostat_business_demography/`, `data/external/nuts3_2021_eurostat.geojson` (untracked) | DATA | LOW | Likely regenerable ingestion outputs; confirm against `.gitignore` intent (should these be tracked or ignored?) | Yes |
| `data/processed/european_panel/` (untracked new files), `data/processed/economic_graph/`, `data/processed/phase4g/` | DATA | LOW-MEDIUM | Cross-check against canonical #9; some may already be superseded outputs that should be gitignored rather than committed | Yes |
| `data/processed/dual_graph_pilot_all_folds/`, `dual_graph_preflight/`, `dual_graph_tensors/`, `graph_temporal_s1/`, `graph_temporal_v2/` (untracked) | DATA | LOW (CLOSED branches per canonical #9 §4) | These belong to closed branches (P6, graph-temporal) — confirm they should stay gitignored, not accidentally committed | Yes |
| `data/processed/herald_observatory_v02/`, `v03/`, `v04/` (untracked) | DATA | LOW | Historical Observatory milestones; confirm intentionally excluded from git (regenerable) | Yes |
| `data/processed/real_dec059_results/`, `real_weak_label_results/`, `sector_precedence_results/`, `synthetic_benchmark/` (untracked) | DATA | LOW | Research-track/Phase 7 outputs; cross-check against `herald_artifact_registry.json` for intended tracked-vs-ignored status | Yes |
| `hpc/phase4/`, `hpc/phase7_sector_precedence/` (modified/untracked scripts) | HPC | MEDIUM | Confirm whether these are new authorized scripts or leftover scratch work | Yes |
| `hpc_results/dual_graph_s1/`, `phase10_synthetic_lagged/`, `phase7_pt_municipal/`, and ~30 `herald_phase4*`/`smoke_phase4*` job folders (untracked) | HPC | LOW | Per canonical #11, these are mostly historical/superseded or closed-branch job outputs; confirm `.gitignore` is correctly excluding the large files within them | No (already classified in #11) |
| `reports/dashboards/herald_observatory_v051_narrative_dashboard.html`, `herald_observatory_v05_narrative_dashboard.html` (modified) | DASHBOARD | **explicitly out of scope for this pass** | Do not touch until the modular map-first redesign begins | Yes, when that work starts |
| `reports/bibliography/HERALD_REFERENCES_MASTER.md` (modified) | DOC | LOW | Review diff (likely a reference addition), commit separately when ready | Yes |

## 2. Data — folders needing a future keep/archive/gitignore/consolidate decision

| Path | Decision needed |
|---|---|
| `data/processed/ardeco_extension/`, `france_relation_audit/`, `municipal_granularity_audit/`, `granular_phase7_preflight/` | Archive (closed/superseded preflight) vs keep for traceability — currently kept, no action forced |
| `data/processed/phase4/`, `phase4d/`, `phase4e/`, `phase4g/`, `phase5/` | Consolidate into a single `phase4_historical/` umbrella, or leave as-is — cosmetic only, not urgent |
| `data/interim/atlas_iat/` | Out-of-scope (pre-HERALD); candidate for archiving outside the active `data/` tree in a future pass |
| `data/processed/herald_observatory_v01/`...`v04/` (pre-granular) | Could be pruned to keep only the small manifest/summary files once confirmed unused by any active builder |
| `data/raw/` (28 GB) | Mostly gitignored already; periodic check that nothing large is accidentally tracked |

## 3. Code — modules needing future review

| Path/group | Status guess (canonical #10) | Review needed |
|---|---|---|
| `src/modeles/synthetic/phase16_decoupled/` and siblings (phase11-15) | Research-track, PARTIAL | Decide if this line of work continues (new DEC) or is formally paused |
| `src/modeles/real_world/` | Research-track, PARTIAL | Same as above — owns the DEC-056/058/059 weak-label line |
| Pre-Q7 `train_herald_v3.py`...`v7.py`, `train_herald_semi_v1/v2.py`, `train_herald_regime_experiment.py` | HISTORICAL_EXPERIMENT | Confirm none of these are silently imported by anything still active (a quick `grep -r "import train_herald_v"` would settle this in a future pass) |
| `src/data/european_panel/build_dual_graph_tensors.py`, `audit_dual_graph_targets.py`, `src/modeles/dual_graph_models.py`, `train_dual_graph_experiment.py` | CLOSED_BRANCH (DEC-029) | No action — correctly closed, just flagged here as a reminder not to casually reuse |
| `src/data/european_panel/build_graph_temporal_*.py`, `src/modeles/graph_temporal_*.py` | CLOSED_BRANCH (DEC-031) | Same as above |

## 4. HPC — scripts/results needing classification before reuse

| Path/group | Needed before reuse |
|---|---|
| `hpc/phase4/` (mixed active/historical per canonical #11) | Per-script DEC-tag review — some 4N/4E-B scripts are reusable baselines, others (4P/4Q) are CLOSED |
| `hpc/phase6_dynamic_dual_graph/`, `hpc/phase5/` | CLOSED branches — no new HPC submission without a new DEC (Charter §8) |
| `hpc_results/imported_from_vm_20260501`, `final_model_comparison_20260429` | Provenance not independently re-verified (flagged in canonical #11 §5) — verify before citing anything from these |
| `hpc_results/smoke_*` (all smoke-test folders) | Liveness checks only — never cite as a scientific result regardless of folder age |

## 5. Dashboard — explicitly deferred

The next visual work item is the **modular, map-first dashboard redesign** (signalled
direction, not started — see canonical #5). **No dashboard, HTML, CSS, JS, or builder
file was touched in this pass or should be touched until that work explicitly begins.**
When it does, canonicals #5, #9 (data), #10 (code), and #11 (HPC) already provide the
map of what's safe to build on.

---

## How to use this backlog

- Each row is a chore, not a finding — none of these block current scientific claims.
- "Needs human decision? Yes" means: do not act on this row without explicit
  authorization, even though the action itself (e.g. `git add`, `.gitignore` edit) is
  low-risk in isolation.
- This document should be updated (not replaced) as items are resolved — mark resolved
  rows rather than deleting them, consistent with the project's "never silently erase
  history" convention used throughout the decision log and naming conventions.

## Cross-reference

- Data structure: `reports/canonical/HERALD_09_DATA_ASSET_MAP.md`
- Code structure: `reports/canonical/HERALD_10_CODE_PATH_MAP.md`
- HPC structure: `reports/canonical/HERALD_11_HPC_AND_RESULTS_MAP.md`
- Phase-level status: `reports/canonical/HERALD_12_FINAL_PHASE_MAP.md`
