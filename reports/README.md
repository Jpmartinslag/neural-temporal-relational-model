# HERALD Reports

This directory is now intentionally small at the top level.

The old phase-by-phase reports were consolidated into five canonical synthesis
documents under `reports/canonical/`. Historical reports are still recoverable from
git history (every one of the 210 removed files was individually re-read and verified
against the canonicals — see `canonical/HERALD_DEEP_REPORT_AUDIT.md`), but they are no
longer the public entry point.

**Do not start with:** `hpc_results/` (raw HPC outputs), raw data under
`data/external/*/raw/`, or any dashboard HTML other than the current candidate. These
require cross-referencing the decision log before any number is trusted.

## Read First

1. `canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`
2. `canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`
3. `canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md`
4. `canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
5. `canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`

## Second-level canonical maps

Built on top of the five above, for cross-cutting traceability:

6. `canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md` — one row per phase/block (data,
   granularity, technique, validation, result, DEC-*, status, citability).
7. `canonical/HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md` — the scientific reasoning in
   narrative form, for the article.
8. `canonical/HERALD_08_REPOSITORY_TRACEABILITY_MAP.md` — what each folder is and what
   not to cite from it.
9. `canonical/HERALD_09_DATA_ASSET_MAP.md` — every data path classified (canonical,
   valid-processed, raw-regenerable, historical, blocked-for-training).
10. `canonical/HERALD_10_CODE_PATH_MAP.md` — every `src/` module classified (active,
    historical, closed branch, research-track).
11. `canonical/HERALD_11_HPC_AND_RESULTS_MAP.md` — every HPC job/result classified
    with its DEC trace.
12. `canonical/HERALD_12_FINAL_PHASE_MAP.md` — the single end-to-end phase table.

`canonical/HERALD_13_ORGANIZATION_BACKLOG.md` is an organizational chore list (not a
scientific document) — uncommitted worktree state and future data/code/HPC decisions.
`01`-`12` are the science/structure base; `13` is housekeeping against that base.

## Control Documents

- `HERALD_CURRENT_STATE.md` — current component status and next step.
- `HERALD_METHODOLOGICAL_DECISION_LOG.md` — immutable DEC-* decision trail.
- `HERALD_ACTIVE_DOCUMENT_INDEX.md` — classification of current, historical, and closed evidence.
- `HERALD_REPORTS_CONSOLIDATION_MAP.md` — where each old report cluster is represented.
- `HERALD_PROJECT_CHARTER.md` — permitted and forbidden claims.
- `HERALD_NAMING_CONVENTIONS.md` — canonical labels and status vocabulary.
- `herald_artifact_registry.json` — artifact provenance and allowed use.

## Dashboards

Current dashboard candidate:

- `dashboards/herald_observatory_v051_narrative_dashboard.html`

Stable scientific baseline/dashboard lineage is documented in the canonical roadmap.

## Policy

Do not add new root-level phase reports. New scientific work needs a DEC-* entry and
should either update a canonical report or create a clearly scoped artifact referenced
from the active document index.
