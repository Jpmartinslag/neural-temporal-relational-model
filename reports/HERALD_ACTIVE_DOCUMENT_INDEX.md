# HERALD Active Document Index

**Updated:** 2026-06-18 (canonical consolidation, phase 2 — git index cleanup).
**Rule:** Documents not listed here as tracked should be assumed represented inside the
5 canonical documents and/or available via `git log`/`git show`, not lost.

---

## What changed in this pass

This index used to carry a full per-file table for 150+ `reports/*.md` files. That table
is now **superseded by `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`**,
which classifies every one of those files individually (category, which canonical
document represents it, action taken, reason, risk) and is more precise than this index
ever was. `reports/canonical/HERALD_DEEP_REPORT_AUDIT.md` goes one step further: every
one of those 210 files was opened and read in full (via `git show`) and checked for
quantitative numbers, gates, and caveats not yet in any canonical — 7 gaps were found
and closed. Most of those files have been removed from the git index via
`git rm --cached` — they remain on the local filesystem and in full git history; only
the public/tracked tree is smaller. **If a file is not listed in the "Currently
tracked" table below, treat it as: represented in the canonical docs; available in git
history — not deleted, not lost.**

**Where not to start:** `hpc_results/` (raw job outputs, mostly closed/superseded
branches), raw `data/external/*/raw/` ingestion caches, and historical dashboard HTML
files under `reports/dashboards/` other than the current candidate
(`herald_observatory_v051_narrative_dashboard.html`, see
`reports/HERALD_CURRENT_STATE.md`'s Visualization row) are none of them an entry
point — they require cross-referencing the decision log/artifact registry before any
number from them is trusted.

---

## Category legend

| Category | Meaning |
|---|---|
| `CANONICAL_READ_FIRST` | Read these before anything else; they define scope, state, and rules. |
| `CURRENT_SCIENTIFIC_EVIDENCE` | Results currently citable as evidence. |
| `SOURCE_AUDITS` | Explains where a current result came from — not the headline claim itself. |
| `HISTORICAL_BUT_IMPORTANT` | Superseded for citation but explains the path to current state. |
| `SUPERSEDED_OR_CLOSED_BRANCH` | Tested and rejected under a pre-registered gate; Charter §8 governs reopening. |
| `GENERATED_DASHBOARD_OR_EXPORT` | Build output, regenerable from a builder script. |
| `DO_NOT_START_HERE` | Real artefacts but not an entry point. |

**Start with `reports/canonical/` (12 documents, in numbered order: the 5 entry-point
canonicals + 7 second-level traceability maps — `HERALD_06_PHASE_TECHNIQUE_MATRIX.md`,
`HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md`, `HERALD_08_REPOSITORY_TRACEABILITY_MAP.md`,
`HERALD_09_DATA_ASSET_MAP.md`, `HERALD_10_CODE_PATH_MAP.md`,
`HERALD_11_HPC_AND_RESULTS_MAP.md`, `HERALD_12_FINAL_PHASE_MAP.md`, plus the
`HERALD_CANONICAL_CONSOLIDATION_AUDIT.md` and `HERALD_DEEP_REPORT_AUDIT.md` audit
trail).** All 12 numbered documents are `CANONICAL_READ_FIRST`.

---

## Currently tracked `reports/` files (top level, outside `canonical/`, `dashboards/`, `bibliography/`)

The root of `reports/` now holds exactly 8 files — the canonical control documents —
plus the 3 kept folders.

| Document | Category | Purpose |
|---|---|---|
| `reports/README.md` | `CANONICAL_READ_FIRST` | Directory entry note, points to `canonical/` |
| `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` | `CANONICAL_READ_FIRST` | This file |
| `reports/HERALD_CURRENT_STATE.md` | `CANONICAL_READ_FIRST` | State per component, blockers, next step |
| `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` | `CANONICAL_READ_FIRST` | All decisions DEC-001→DEC-068 — authoritative, never represented_by anything |
| `reports/HERALD_PROJECT_CHARTER.md` | `CANONICAL_READ_FIRST` | Official direction, scope, permitted/forbidden claims — authoritative |
| `reports/HERALD_NAMING_CONVENTIONS.md` | `CANONICAL_READ_FIRST` | Canonical label/status vocabulary, documented naming inconsistencies |
| `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md` | `CANONICAL_READ_FIRST` | Which canonical doc represents which report cluster |
| `reports/herald_artifact_registry.json` | `CANONICAL_READ_FIRST` | Artefact manifest with status and claims |

Plus `reports/canonical/` (14 files: the 5 entry-point canonicals, the 7 second-level
traceability maps (06-12), and the 2 audit docs — consolidation + deep verification),
`reports/dashboards/` (current and historical dashboard HTML + builders), and
`reports/bibliography/` (references) — all unconditionally kept per policy.

**Everything else previously listed in this index** (Phase 2/3 France search, Phase 4
sub-steps, G1/G2 audits, closed graph branches, DEC-038→066 reports, the evidence matrix,
the literature review, Observatory v0.1→v0.5.1 contracts, dual-graph/regime/V7 history,
ATLAS_IAT, repository cleanup plans, etc. — including 14 files kept tracked through the
first consolidation pass and removed in a 2026-06-18 follow-up root cleanup once their
content was confirmed absorbed) **has been removed from the git index** and is fully
accounted for, file by file, in `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`
(see its "Final root reports cleanup" section for the second-pass files specifically).

---

## Special notes carried over (still relevant, kept short)

- **P6 sector label status:** `data/processed/dual_graph_s1/learned_sector_edges.csv`
  uses sector names that do not match the tensor `sector_id`s used elsewhere. Status:
  `INVALID_FOR_INTERPRETATION` (Charter §6). Index-based gate metrics (Jaccard, density,
  MAE) remain valid. The gate decision (`DUAL_GRAPH_S1_FAIL`) is unaffected.
- **France WMAPE 0.0204 (Q7):** `PENDING_REAUDIT`. Do not cite as a headline claim until
  the causal-feature audit of the Phase 3E/2R pipeline (`growth_1y/2y`, `effectifs_lag1`)
  is complete. See canonical #1 and #4.
- **File naming policy:** active documents live at `reports/HERALD_*.md` or
  `reports/canonical/HERALD_0*.md`. Do not create new root-level phase reports — new
  scientific work needs a DEC-* entry and should update a canonical document instead.

---

## Cross-reference

- Canonical entry point: `reports/canonical/HERALD_0{1..5}_*.md`
- Full per-file consolidation audit: `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`
- Cluster-level mapping: `reports/HERALD_REPORTS_CONSOLIDATION_MAP.md`
- Decision history: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md`
