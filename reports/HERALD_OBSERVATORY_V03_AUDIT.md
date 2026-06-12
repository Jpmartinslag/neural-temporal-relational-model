# HERALD Observatory v0.3 — Integration Audit

**Status:** COMPLETE  
**Date:** 2026-06-12  
**Decision:** DEC-035  
**Depends on:** DEC-034 (SECTOR_PRECEDENCE_PROTOTYPE_READY), DEC-032 (Observatory v0.2 contract)

---

## 1. Objective

Integrate the validated Phase 7 sector precedence results (DEC-034) into Observatory v0.3, extending the v0.2 panel with a sector→sector relations layer and updated dashboard. The observatory schema is unchanged (same 45,945 rows, same columns); only `sector_graph_available` values are updated and new output files are added.

---

## 2. Inputs Verified

| Input | Path | Status |
|-------|------|--------|
| Observatory v0.2 panel | `data/processed/herald_observatory_v02/herald_observatory_v02_panel.csv` | SHA256 verified: `a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e` |
| Phase 7 promoted edges (main) | `data/processed/sector_precedence_results/latest.csv` | 25 rows (FR=1, NL=8, PT=16) |
| COVID-robust edges | `data/processed/sector_precedence_results/covid_robust_edges.csv` | 12 rows (NL=3, PT=9) |
| Phase 7 decision | `data/processed/sector_precedence_results/decision.json` | verdict: SECTOR_PRECEDENCE_PROTOTYPE_READY |
| Phase 7 audit | `data/processed/sector_precedence_results/audit/audit_report.json` | PASS |

---

## 3. Outputs Generated

| File | Rows/Size | Notes |
|------|-----------|-------|
| `data/processed/herald_observatory_v03/herald_observatory_v03_panel.csv` | 45,945 rows | Same schema as v0.2; `sector_graph_available` updated |
| `data/processed/herald_observatory_v03/herald_observatory_v03_sector_relations.json` | 25 edges | ROBUST=12, MAIN_ONLY_EXPLORATORY=13 |
| `data/processed/herald_observatory_v03/herald_observatory_v03_manifest.json` | — | SHA256 of panel, input checksums, verdict, provenance note |
| `data/processed/herald_observatory_v03/herald_observatory_v03_summary.json` | 433 state rows, 5105 territory rows | Pre-aggregated for dashboard rendering |
| `reports/dashboards/herald_observatory_v03_dashboard.html` | ~902KB | Self-contained HTML; Plotly 2.27.0 CDN |

---

## 4. Edge Classification

### ROBUST edges (12 — default visible in dashboard)

COVID-robust = promoted in main AND without_2020, same sign.

| Country | Window | Source → Target | β_main | Sign |
|---------|--------|-----------------|--------|------|
| NL | 2014–2019 | FZ → GI | +0.195 | positive |
| NL | 2014–2019 | FZ → RU | +0.170 | positive |
| NL | 2014–2019 | JZ → FZ | −0.230 | negative |
| PT | 2014–2019 | BE → MN | −0.281 | negative |
| PT | 2014–2019 | MN → JZ | −0.311 | negative |
| PT | 2014–2019 | OQ → JZ | −0.328 | negative |
| PT | 2015–2020 | GI → BE | +0.362 | positive |
| PT | 2015–2020 | MN → JZ | −0.289 | negative |
| PT | 2015–2020 | MN → OQ | −0.287 | negative |
| PT | 2015–2020 | OQ → JZ | −0.267 | negative |
| PT | 2017–2022 | BE → MN | −0.228 | negative |
| PT | 2017–2022 | GI → JZ | −0.220 | negative |

### MAIN_ONLY_EXPLORATORY edges (13 — hidden by default, user opt-in)

Promoted in main scenario only; not confirmed without_2020. Includes FR's single promoted edge (RU→MN, 2020-2025).

---

## 5. sector_graph_available Update Logic

`sector_graph_available = 1` iff `structural_mask = 1` AND country has COVID-robust edges AND `observation_year` falls within at least one robust window for that country.

| Country | Robust windows | sector_graph_available |
|---------|----------------|------------------------|
| NL | 2014–2019 | 1 for NL rows with structural_mask=1 and year ∈ [2014, 2019] |
| PT | 2014–2019, 2015–2020, 2017–2022 | 1 for PT rows with structural_mask=1 and year ∈ [2014, 2022] |
| FR | — | 0 always |

---

## 6. Dashboard Features

- **Sector Precedence Graph:** Circular layout, 9 nodes, directed arrows. Country filter. Toggle to show/hide MAIN_ONLY_EXPLORATORY. Click → side panel with all edge fields and non-causal interpretation.
- **Economic State Timeline:** Plotly heatmap sector × year, six economic states (growth/acceleration/deceleration/stagnation/decline/recovery).
- **Territory State Distribution:** Stacked bar, country + sector filter.
- **Territory Dynamics:** Velocity heatmap territory × year.
- **Provenance section:** Manifest metadata, DEC-034/035 references.

---

## 7. Tests

File: `tests/test_observatory_v03.py` — 29 tests (21 builder + 8 dashboard).

| Category | Tests | Result |
|----------|-------|--------|
| Schema (columns, row count) | 2 | PASS |
| Determinism + checksums | 2 | PASS |
| A10 sector codes | 1 | PASS |
| Exactly 12 ROBUST relations | 1 | PASS |
| NL=3/PT=9/FR=0 split | 1 | PASS |
| No self-edges, no duplicates | 2 | PASS |
| 25 total main edges | 1 | PASS |
| Economic states valid | 1 | PASS |
| sector_graph_available logic | 2 | PASS |
| No causal language | 1 | PASS |
| Manifest provenance + checksums | 3 | PASS |
| Sector relations JSON schema | 1 | PASS |
| Sign correctness | 1 | PASS |
| FR 0 ROBUST | 1 | PASS |
| Manifest verdict | 1 | PASS |
| Summary JSON | 1 | PASS |
| Dashboard file + HTML validity | 2 | PASS |
| Dashboard Plotly + edge embeds | 2 | PASS |
| Dashboard sections | 1 | PASS |
| Dashboard no causal language | 1 | PASS |
| Dashboard provenance + filter | 2 | PASS |
| **Total** | **29** | **29 PASS** |

Full suite: 649 passed, 3 skipped (2026-06-12).

---

## 8. Scientific Integrity Checks

| Check | Result |
|-------|--------|
| No structural causality language | PASS — provenance note uses approved disclaimer only |
| No gate threshold alteration post-observation | PASS — DEC-033 gates immutable; not modified |
| ROBUST defined by COVID robustness only | PASS — classification matches covid_robust_edges.csv exactly |
| MAIN_ONLY_EXPLORATORY edges hidden by default | PASS — dashboard requires user toggle |
| v0.2 SHA256 verified | PASS — `a6f8a5b2...c742e` confirmed |
| FR contributes 0 ROBUST | PASS — test_nl_3_pt_9_fr_0_robust passes |
| Duplicate/self-edge checks | PASS — 0 self-edges, 0 duplicates |

---

## 9. Files Committed

| File | Type | Notes |
|------|------|-------|
| `src/data/european_panel/build_observatory_v03.py` | Builder script | Creates panel + relations + dashboard |
| `tests/test_observatory_v03.py` | Test suite | 29 tests |
| `reports/dashboards/herald_observatory_v03_dashboard.html` | Dashboard | Self-contained HTML |
| `reports/HERALD_OBSERVATORY_V03_AUDIT.md` | This document | |
| Documentation updates | Various `.md` + `.json` | CURRENT_STATE, CODEX_MEMORY, DECISION_LOG, EVIDENCE_MATRIX, GANTT, ACTIVE_DOC_INDEX, artifact registry, README |

Observatory data outputs (`data/processed/herald_observatory_v03/`) are **not** committed — regenerable from builder script.

---

## 10. Provenance

| Item | Value |
|------|-------|
| Builder | `src/data/european_panel/build_observatory_v03.py` |
| Input panel SHA256 | `a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e` |
| Phase 7 Slurm job | 7455266 |
| Tests | 649 passed, 3 skipped |
| Generated | 2026-06-12 |
| Decisions | DEC-034 (sector precedence), DEC-035 (v0.3 integration) |
