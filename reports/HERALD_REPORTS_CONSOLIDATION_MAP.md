# HERALD Reports Consolidation Map

**Created:** 2026-06-18 (documentation/curation pass).
**Purpose:** This repository has 200+ `reports/*.md` files. This map says which
canonical synthesis document now represents each cluster of older reports — it does
**not** merge files physically, delete anything, or move folders. Every file named
below still exists exactly where it was; this is a reading guide, not a migration.

**2026-06-18 update:** the five documents in `reports/canonical/` are now the primary
synthesis layer and supersede the single-document pointers used in the first version of
this map (which pointed mostly at `HERALD_PROJECT_TRAJECTORY.md`/`HERALD_ARCHITECTURE_OVERVIEW.md`
directly). Those documents still exist and are still accurate — they are now the
*source material the canonical docs are built from*, not themselves the entry point.

For per-file classification (ACTIVE/historical/closed-branch), see
`reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`. For the narrative version of how these
clusters relate chronologically, see `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`.

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
| Regime/V6/V7 architecture search, dual-graph design docs (pre-P6) | `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` ("Dual graph / regime / V7 architecture search") | Superseded by the final P6/DUAL_GRAPH_S1_FAIL result; kept only for traceability of design rationale. |
| Pre-HERALD ATLAS_IAT reports | Not represented by any current HERALD document — out of scope by definition | `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` ("Out of HERALD scope"). |
| Repository/dashboard cleanup plans (multiple prior passes) | This document + `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` (this 2026-06-18 pass is latest in that lineage) | Earlier cleanup passes are historical record, not superseded instructions to redo. |
| `reports/HERALD_PROJECT_TRAJECTORY.md` (first trajectory doc, superseded as entry point) | `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md` | Still accurate; kept as the detailed narrative source the canonical doc's Phase Map table is built from. |
| `reports/HERALD_ARCHITECTURE_OVERVIEW.md` (first architecture doc, superseded as entry point) | `reports/canonical/HERALD_03_METHODS_AND_ARCHITECTURE.md` | Still accurate; kept as the detailed architecture source. |
| `reports/HERALD_RESEARCH_GANTT.md` (detailed Gantt, superseded as entry point) | `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md` (§4, Mermaid Gantt) | Still the authoritative detailed timeline with per-task status checks; the canonical doc's Gantt is a Mermaid-rendered summary. |

---

## How to use this map

1. If you need a **current number or claim**, go to the "Represented by" column first.
2. If you need to understand **why** a result looks the way it does, follow the
   cluster's listed reports — they are not deleted, just not the entry point.
3. If a cluster isn't listed here, it isn't large enough to need a synthesis pointer —
   check `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` directly.
