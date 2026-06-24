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
`canonical/HERALD_14_WORKTREE_DECISION_AUDIT.md` is the decision layer on top of it:
per-group commit/gitignore/keep-local/requires-new-DEC/human-review calls. `01`-`12` are
the science/structure base; `13`-`14` are housekeeping against that base.

13. `canonical/HERALD_15_FR_ZE2020_DATA_TREATMENT_PIPELINE.md` — France ZE2020 data layer
    (raw ingestion through `fr_ze2020_model_ready_panel.csv`), separate from training.
14. `canonical/HERALD_16_MODEL_TRAINING_BLOCK_AUDIT.md` — its training-side counterpart:
    every training script classified current/legacy/experimental/closed, and the minimal
    current FR ZE2020 baseline path. Also housekeeping, not a new scientific result.
15. `canonical/HERALD_17_FR_ZE2020_RELATIONAL_LAYER_PLAN.md` — audit and plan for a
    future ZE2020/sector relational layer: artifact inventory, what's usable now vs.
    needs provenance, the scientific hypothesis, and a staged MVP. Planning only — no
    graph/neural model implemented, no claim made.
16. `canonical/HERALD_18_FR_ZE2020_TRAINING_PLAN.md` — audits the 4 current FR ZE2020
    training scripts, defines the local training architecture (Task A: ZE-level
    forecast; Task B: sector graph), and specifies (but does not run) the HPC-ready
    hypotheses and checklist for the next HPC step. No HPC job launched, no headline
    claim.
17. `canonical/HERALD_19_FR_ZE2020_HPC_SPEC.md` — executable HPC spec for the FR
    ZE2020 training block (5 seeds x the 4 scripts), pre-registered gates G1-G5,
    and the `hpc/france_ze2020/` infrastructure. `SPEC_READY`, not launched — `sbatch`
    requires an explicit `--confirm-submit` flag.

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
