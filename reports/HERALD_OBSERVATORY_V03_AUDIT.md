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

---

## 11. DEC-036 / v0.3.1 Addendum — Geographic Dashboard + Derived Windows + France ZE Finding + Sector Map

**Decision:** DEC-036
**Date:** 2026-06-12

### 11.1 Problems fixed

| # | Problem | Fix |
|---|---------|-----|
| A1 | Dashboard lacked geographic map | Choropleth (Plotly `go.Choropleth`) added as primary section; 3 country GeoJSONs embedded (FR=280 ZE2020, NL=40 COROP, PT=25 NUTS3); territory click → mini side panel with state + velocity time series |
| A2 | Dashboard depended on CDN Plotly | `plotly.min.js` (4.7 MB) embedded from `plotly/package_data/plotly.min.js`; CDN fallback only if package not installed; manifest records `"plotly_dependency"` field |
| A3 | `ROBUST_WINDOWS` hardcoded in builder | Replaced by `derive_robust_windows(covid_robust_edges.csv)`; FAIL_CLOSED if counts ≠ NL=3/PT=9/FR=0; manifest records derived windows |

### 11.2 France ZE scale finding

Inspection of `herald_observatory_v02_panel.csv` confirms all FR rows have `region_system = "ZE2020"` (280 functional employment zones). Phase 7 used this panel → Phase 7 FR was already computed at ZE functional scale. No separate P7_FR_ZE_SCALE_SENSITIVITY study is needed or warranted. The territorial system badge in the dashboard explicitly labels FR as ZE2020, NL as COROP (equivalent NUTS3), PT as NUTS3.

### 11.3 v0.3.1 patch — Sector map + mainland Portugal

Additional fixes applied after DEC-036 (no new DEC required — no scientific decision changed):

| Change | Detail |
|--------|--------|
| Sector filter on map | A10 sector dropdown ("All" or specific sector); "All" shows territory coloured by sector with largest absolute velocity; sector code shown in hover and side panel |
| Portugal mainland scope | `_build_pt_geojson` filters via `territorial_scope.is_in_scope`; Azores/Madeira excluded from map (PT_200, PT_300) but retained in panel; map badge shows "23 mainland territories" |
| `dominant_sector` field | Added to `territory_summary` records; JS `dominantSector` field in `TERR_IDX` |
| `territory_sector_summary` | New per-territory × sector × year precomputed in `summary.json`; `TERR_SECTOR_IDX` JS index in dashboard |
| `map_scope` in manifest | Records `mapped_territories`, `panel_territories`, `excluded_from_map` |
| KPI label | "Territories total 345" → "Territories mapped 343" |

### 11.4 Updated outputs

| File | Before | After v0.3.1 |
|------|--------|--------------|
| `reports/dashboards/herald_observatory_v03_dashboard.html` | ~902 KB, CDN Plotly, no map | 13,930 KB, Plotly+GeoJSON+sector data embedded |
| `src/data/european_panel/build_observatory_v03.py` | `ROBUST_WINDOWS` constant, no GeoJSON, CDN | `derive_robust_windows()`, 3 GeoJSON builders, sector filter, mainland PT scope |
| `tests/test_observatory_v03.py` | 29 tests | 48 tests |

### 11.5 Tests added (DEC-036 + v0.3.1)

| Category | Tests added |
|----------|-------------|
| ROBUST_WINDOWS not hardcoded (AST check) | 1 |
| `derive_robust_windows` structure + FAIL_CLOSED | 4 |
| Manifest records derived windows + Plotly dependency | 3 |
| Dashboard: choropleth map present, 3 GeoJSONs, system labels | 3 |
| Dashboard: no undeclared external scripts | 1 |
| Dashboard: territory click side panel + year/country filter | 2 |
| FR uses ZE2020, distinct from NUTS3 | 2 |
| `test_dashboard_no_causal_claim` strips `<script>` blocks | (fix, not new) |
| Portugal mainland map (no island panel_ids, "mainland territories" text) | 1 |
| Sector identification per territory (shownSector, `sector=` in hover) | 1 |
| **Total new (DEC-036 + v0.3.1)** | **19** |

Full test suite post-DEC-036: 666 passed, 3 skipped.
Full test suite post-v0.3.1: **48/48 observatory tests pass**.

### 11.5 Map interpretation correction

- The map now has an explicit A10 sector selector. When one sector is selected,
  colour, state and velocity all refer to that sector.
- In `All sectors`, each territory is represented by the sector with the
  largest absolute velocity for the selected year. The sector code is shown in
  the hover and territory detail panel; it is no longer an unexplained
  cross-sector majority state.
- The Portugal map uses the pre-declared `continental_mainland` scope:
  `PT20*` (Azores) and `PT30*` (Madeira) remain in the canonical panel but are
  excluded from the geographic view. The map therefore contains 23 mainland
  NUTS3 territories.
- Sector-to-sector precedence remains a country-level graph. It is not drawn as
  a territory-to-territory flow because Phase 7 did not estimate spatially
  localised sector edges.

---

## 10. Provenance

| Item | Value |
|------|-------|
| Builder | `src/data/european_panel/build_observatory_v03.py` |
| Input panel SHA256 | `a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e` |
| Phase 7 Slurm job | 7455266 |
| Tests (DEC-035) | 649 passed, 3 skipped |
| Tests (DEC-036) | 666 passed, 3 skipped |
| Generated | 2026-06-12 |
| Decisions | DEC-034 (sector precedence), DEC-035 (v0.3 integration), DEC-036 (geographic dashboard + derived windows + France ZE) |
