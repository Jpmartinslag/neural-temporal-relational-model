# HERALD Reports Consolidation Map

**Created:** 2026-06-18 (documentation/curation pass).
**Purpose:** This repository had 200+ `reports/*.md` files. This map says which
canonical synthesis document now represents each cluster of older reports. It does
**not** move folders or alter any DEC-*/scientific result.

**2026-06-18 update (git index cleanup):** most individual files named in this map have
since been removed from the git index via `git rm --cached` — they remain on the local
filesystem and in full git history, but are no longer part of the tracked/public tree.
See `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md` for the exact per-file
disposition (kept/removed, category, risk). This map stays at the cluster level; it does
not repeat that file-by-file detail.

For per-file classification, see `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` and the
consolidation audit above. For the narrative version of how these clusters relate
chronologically, see `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`.

---

| Report cluster | Represented by (canonical synthesis) | Notes |
|---|---|---|
| Phase 2/3 France architecture search (all `HERALD_PHASE2*.md`/`HERALD_PHASE3*.md` except 2R/3E) | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` ("France foundation" phase) + `reports/HERALD_PHASE3E_QTENSOR_ARCH_AUDIT.md` + `reports/HERALD_PHASE2R_CONFIRMATORY_AUDIT.md` | The two named audits are the citable result (Q7, PENDING_REAUDIT); the rest is search-process history. |
| Phase 4 harmonization (all `HERALD_PHASE4*.md` except 4M/4N/4O-B/4P/4Q/4J) | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` ("International harmonization" phase) + `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md` (claim table) | 4M/4N/4O-B/4P/4Q/4J themselves remain the citable results; the rest are intermediate plans/sub-steps feeding them. |
| Dynamic Economic Graph G0–G2 (`HERALD_G0*`, `HERALD_G1*`, `HERALD_G2*` except the named PASS audits) | `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` (§2-3) | `HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md` and `HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md`/`HERALD_G2_COVID_SENSITIVITY_AUDIT.md` remain the citable PASS results. |
| Closed graph branches: P6 dual graph, graph-temporal GConvGRU/EvolveGCN-H, geographic/mobility queen-contiguity (Phase 4P/4Q), Phase 5 fixed-L2 corrector, Louvain communities | `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` (§3) + `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md` ("Closed branches" table) | These are findings, not gaps — the decision log entry is the authoritative record; do not reopen without a new DEC-*. |
| DEC-048→DEC-059 neural relation-learning research track | `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` (§4) + `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md` | Still active as a research direction; not wired into any dashboard. Individual DEC reports remain the source of truth for specific numbers (e.g. AUC values). |
| Phase 7 sector precedence + DEC-060→DEC-066 granularity work | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` ("Granularity push" phase) + `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md` | `HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md` is the authoritative source for the NL proxy block — do not cite the superseded draft. |
| Observatory v0.1→v0.5.1 contracts and audits | `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` | v0.5.1 is the current candidate; v0.3/v0.4/v0.4.1 remain valid as the stable scientific baseline the candidate is built on; v0.5 is superseded for dashboard-readiness only. |
| Regime/V6/V7 architecture search, dual-graph design docs (pre-P6) | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` (France foundation phase) + `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md` | Superseded by the final P6/DUAL_GRAPH_S1_FAIL result; removed from git index, recoverable via git history. |
| Pre-HERALD ATLAS_IAT reports | Not represented by any current HERALD document — out of scope by definition | Removed from git index; see `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md`. |
| Repository/dashboard cleanup plans (multiple prior passes) | This document + `reports/canonical/HERALD_CANONICAL_CONSOLIDATION_AUDIT.md` (this 2026-06-18 pass is latest in that lineage) | Earlier cleanup passes are historical record, removed from git index, recoverable via git history. |
| `reports/HERALD_PROJECT_TRAJECTORY.md` (first trajectory doc) | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` | **Removed from git index** (`ALREADY_FULLY_REPRESENTED`) — content fully absorbed into the canonical's Phase Map; recoverable via git history. |
| `reports/HERALD_ARCHITECTURE_OVERVIEW.md` (first architecture doc) | `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` | **Removed from git index** (`ALREADY_FULLY_REPRESENTED`) — architecture diagram and method tables absorbed into the canonical; recoverable via git history. |
| `reports/HERALD_RESEARCH_GANTT.md` (detailed Gantt) | `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` (§4, Mermaid Gantt) | **Removed from git index** (`ALREADY_FULLY_REPRESENTED`) — milestones absorbed into the canonical's Mermaid Gantt; recoverable via git history. |

---

## Second-level canonical maps (2026-06-18 addition)

In addition to the cluster-level mapping above, three second-level documents now exist
in `reports/canonical/` for cross-cutting traceability rather than per-cluster synthesis:

| Need | Canonical |
|---|---|
| Phase/technique/data/decision matrix (one row per phase) | `reports/canonical/HERALD_06_PHASE_TECHNIQUE_MATRIX.md` |
| Narrative scientific reasoning for the article | `reports/canonical/HERALD_07_METHOD_LINEAGE_FOR_ARTICLE.md` |
| Repository folder structure and what not to cite from where | `reports/canonical/HERALD_08_REPOSITORY_TRACEABILITY_MAP.md` |

---

## How to use this map

1. If you need a **current number or claim**, go to the "Represented by" column first.
2. If you need to understand **why** a result looks the way it does, follow the
   cluster's listed reports — they are not deleted, just not the entry point.
3. If a cluster isn't listed here, it isn't large enough to need a synthesis pointer —
   check `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` directly.
