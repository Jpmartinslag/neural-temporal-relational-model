# HERALD Current State
**Updated:** 2026-06-18 (traceability re-audit — final decision corrected to
`OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`; see DEC-068 in
`HERALD_METHODOLOGICAL_DECISION_LOG.md`. v0.5.1 is the current best-draft
dashboard, not a finally-accepted one: 103/103 structural tests pass but it
has never been visually validated — no Playwright/screenshot, only DOM/JS
string assertions — and the product owner's own next-step direction was to
redesign the dashboard modularly starting with the map.)
**Previously updated 2026-06-17** (OBSERVATORY_V051_NARRATIVE_READY — corrects
OBSERVATORY_V05_NARRATIVE_READY below, which the product owner rejected as a
polished MVP, not a complete-method presentation: English UI, architecture
explanation at the bottom of the page, PT prediction gap left open, no
geographic heatmap, sector graph not wired to the map, generic KPI cards,
technical vocabulary leaking outside the collapsible section. v0.5.1 fixes
every point: French UI throughout; a "Méthode HERALD" architecture diagram
(6 stages + 4 components: statistical baseline / relational-candidate layer
/ validation / output) opens the page before the map; PT municipal
prediction integrated via causal persistence/Ridge AR(1) on the observed PT
municipal panel (no proxy, no HPC — see
`reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` §6, now CLOSED); a real
"Bassins économiques" geographic-intensity heatmap mode; the sector relation
graph now filters the map on click (`applyGraphFilterToMap`); a French
"Résumé d'évidence" replaces the generic KPI cards; beta/q_fdr/bss and the
one permitted causality-prohibition sentence confined to two collapsible
"Détails méthodologiques" blocks; an explicit "Couche relationnelle" section
stating no neural candidate-relation dataset exists in this repository
today. New files only — v0.4/v0.4.1/v0.5 dashboards/builders/tests untouched
and still pass (192/192). New dashboard:
`reports/dashboards/herald_observatory_v051_narrative_dashboard.html` (18.2
MB). 103/103 new tests pass
(`tests/test_observatory_v051_narrative_dashboard.py`). Full record:
`reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md`.)
**Previously updated 2026-06-17 (OBSERVATORY_V05_NARRATIVE_READY [CORRECTED
to OBSERVATORY_V05_PARTIAL by the v0.5.1 entry above; scientific/statistical
DEC-0xx conclusions are unaffected, only this dashboard-readiness claim is
corrected] — new layperson-friendly
dashboard `reports/dashboards/herald_observatory_v05_narrative_dashboard.html` (14.8 MB)
built as a presentation layer on top of v0.4's already-validated granular exports; v0.4
dashboard untouched. Map is now the heatmap (colour-by-year/sector directly on the
choropleth, no separate chart) with a play/pause timeline; sector graph is dynamic and
spatial with a plain-language sentence per relation and a persistent faint-vs-active
window mode; prediction layer ("above/below expected") wired for FR+NL from the existing
v0.3 Ridge/persistence forecast export (same ZE2020/COROP grain as v0.4 granular) — PT
excluded at municipal grain because its only existing forecast is NUTS3-scale (gap
documented, no fabrication, no HPC needed to close: see
`reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md`). PT/KZ structural absence now shown
as "Sector not available for Portugal" (never NaN), KZ disabled in the sector selector
for PT. NL gemeente proxy re-verified absent from the embedded relation graph; 121
blocked proxy edges isolated in a technical-only panel. No causal language, no ML jargon
in the main UI body (test-verified). New exports under
`data/processed/herald_observatory_v05_narrative/`. 65/65 new tests pass
(`tests/test_observatory_v05_narrative_dashboard.py`); all 127 prior v0.4/v0.4.1 tests
unaffected. Playwright unavailable — validated structurally (JSON parse, DOM id/handler
cross-reference) instead of screenshots.)
**Previously updated 2026-06-17 (OBSERVATORY_V041_VISUAL_READY — PT continental municipality geometry obtained (278/278, DGT/CAOP via geoapi.pt, name-crosswalked, 1.18 MB simplified) and now renders as a real choropleth in `reports/dashboards/herald_observatory_v04_granular_dashboard.html` (10.0 MB). Sector→sector graph is now dynamic: timeline slider + play/pause + 3 modes (current/cumulative/recurring) + recurring/sign-change/exclusive markers + per-window edge history + relation×window heatmap. Map↔graph linking added (country sync, sector highlight, edge-click territory context). NL gemeente proxy re-verified absent from the relation graph; 121 blocked edges still isolated. 241/241 tests pass (41 new `test_observatory_v041_visual_upgrade.py` + 200 prior). OBSERVATORY_V04_DASHBOARD_READY (previous milestone) and GRANULAR_OBSERVATORY_V04_DATA_READY both superseded by this visual upgrade. DEC-066 COMPLETE — FINE_GRAIN_THRESHOLD_POLICY_READY. DEC-064: PT_MUNICIPAL_PHASE7_COMPLETE, 2 COVID-robust pairs. DEC-063: GRANULAR_FR_PT_NL_PREFLIGHT_READY.)
**Source of truth:** `HERALD_PROJECT_CHARTER.md`, `HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-068), `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`.

---

## Overall Completion (re-audited 2026-06-18, consolidation/freeze)

This table replaces the 2026-06-12-era estimate below it, which predates
DEC-060→DEC-068 (France signal audit, PT municipal granularity, NL gemeente
proxy block, fine-grain threshold policy, Observatory v0.4.1/v0.5/v0.5.1).
Percentages are planning estimates derived from what is actually READY vs
PARTIAL vs BLOCKED in the decision log — not an empirical metric.

| Layer | Completion | Ready | Partial | Blocked/Missing |
|-------|-----------|-------|---------|------------------|
| **Data** | **85%** | FR ZE2020, PT Municipal (278), NL COROP (40) all observed; PT/IT/AT harmonized Path H panel; European 27-country preflight (DEC-038) | NL gemeente proxy panel built but evidentially weak (DEC-063/065) | NL gemeente births at municipal grain (CBS open data structurally blocked — DEC-062); BE/other EU countries not ingested at sector×territory grain |
| **Forecast/Prediction** | **75%** | Persistence/Ridge causal baseline validated PT/IT/AT LOCO (DEC-006); PT municipal forecast closed via direct AR(1)/Ridge re-run, no proxy, no HPC (DEC-068) | France HERALD Q7 (WMAPE 0.0204) — PENDING_REAUDIT, not a headline claim until causal pipeline audit completes | Conformal/uncertainty intervals still exploratory; no promoted interval method |
| **Economic states** | **65%** | Deterministic observed states exported for aggregate PT/IT/AT and sector FR/NL/PT (Observatory v0.1.1→v0.4); PT/KZ structural absence correctly labelled, never bare NaN | — | No validated forecast-derived state (states are descriptive-only, not predicted ahead) |
| **Sector→sector relations** | **80%** | SECTOR_PRECEDENCE_PROTOTYPE_READY: 20 observed edges (FR=9, NL COROP=8, PT Municipal=3); fine-grain threshold policy ready (DEC-066: ROBUST_ORIGINAL/FINE_GRAIN_SUPPORTED/EXPLORATORY_FINE_GRAIN tiers) | France has only 1 promoted label (RU→MN, COVID-sensitive) — audited root cause is small effect sizes at ZE2020 scale (DEC-060), not a methodology gap | NL gemeente proxy at finer grain BLOCKED for relation labels (DEC-065) — structural validity defect in the stock-share proxy method |
| **Graph/neural layer** | **20%** | SharedRelationEncoder demonstrated on synthetic data (in-sample AUC=0.960, unseen-pair AUC=0.690 — DEC-055); useful as a research direction | Real-data validation PARTIAL (DEC-056/058/059): sign transfer weak (0.438-0.667 depending on variant), no robust cross-country replication, COVID/window sensitivity unresolved | Geographic/mobility graph as forecast input CLOSED (4P/4Q FAIL); P6 dual dynamic graph CLOSED (DUAL_GRAPH_S1_FAIL); graph-temporal GConvGRU/EvolveGCN-H CLOSED (S1_FR_FAIL). **No neural candidate-relation dataset exists in the repository for real data today** (explicitly stated in v0.5.1 dashboard) |
| **Visualization (Observatory)** | **90%** | v0.4.1 stable/historical (FR/NL COROP/PT Municipal real choropleth, dynamic relation graph, 241/241 tests); v0.5.1 `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN` — **committed to git** as the current best-draft candidate (French, architecture-first, FR+NL+PT prediction, real geographic heatmap, graph-to-map wiring, 103/103 structural tests) | No Playwright/screenshot visual validation in this environment (structural JS/DOM validation only) — committed as a candidate, NOT a finally-accepted dashboard | Modular, map-first next iteration signalled by product owner — not started |
| **Recommendation** | **0%** | — | Intelligence layer structure exists from earlier work (`HERALD_INTELLIGENCE_LAYER_SPEC.md`), reusable as structure only | Requires Bloco 1 + Bloco 2 complete per Charter; explicitly NOT STARTED; no weights/claims validated; rankings would be hypotheses only |
| **European product (multi-country)** | **~45%** | FR/PT/NL sector-level integrated; PT/IT/AT harmonized for LOCO; 27-country sector coverage preflight done (DEC-038: FI eligible, 9 countries eligible-with-download) | NL gemeente sub-national disaggregation built but blocked for relations; BE remains semantically heterogeneous (vat_first_registration target) | No validated cross-country pooled relation claim; no validated single harmonized European target beyond Path H (PT/IT/AT, enterprise_birth demographic concept only) |
| **Writing/article** | **5%** | Decision log, charter, evidence matrix, and bibliography (25 master refs) exist as raw material | Gantt re-drafted in this consolidation (`reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`) | No outline, no draft sections, no venue selected; report/article writing has not started in any form beyond methodological documentation |

**What's needed before the thesis/article can be written:** (1) Observatory
v0.4.1/v0.5/v0.5.1 committed and visually validated; (2) PT municipal
prediction extended/validated further if time permits (already closed as a
data-engineering task, DEC-068); (3) decision on whether to attempt the
modular map-first dashboard before or after writing starts; (4) figures/
tables generated from the frozen results (not yet done — no figure-export
pass has happened since Phase 8); (5) an explicit methods/results/discussion
outline — none exists yet.

---

## Overall Completion (legacy estimate, 2026-06-12 — superseded by the table above)

| Layer | Completion | Notes |
|-------|-----------|-------|
| Data | **87%** | PT/IT/AT harmonized; FR/NL/BE complete; European preflight DEC-038 complete; FI eligible, ES/IT/DE eligible with download |
| Quantitative forecasting | **75%** | Ridge+persistence validated; conformal intervals exploratory |
| Territorial graph (G1-L2) | **75%** | FR/NL/PT PASS; community detection NOT_SUPPORTED |
| Aggregate dynamics (G2) | **75%** | FR robust; NL/PT COVID-sensitive |
| Economic states | **60%** | Deterministic observed states exported for aggregate PT/IT/AT and sector FR/NL/PT |
| Sector→sector graph | **90%** | SECTOR_PRECEDENCE_PROTOTYPE_READY: 12 COVID-robust edges (NL=3, PT=9); integrated in Observatory v0.3 (DEC-034/035) |
| Explanation | **30%** | Descriptive co-growth associations; no attention/associative explanation validated |
| Dashboard | **85%** | Observatory v0.3: choropleth map + sector graph + economic states + territory heatmaps + Phase 8 territorial contribution layer (Section 6, toggle, divergent scale); 14,095 KB self-contained (DEC-036/037) |
| Recommendation | **35%** | Intelligence layer structure exists; weights/claims not validated |
| Territorial movement attribution | **55%** | Phase 8 DESCRIPTIVE_ONLY: 91 HIGH + 78 MODERATE + 8 LOW DESCRIPTIVE territories localised per ROBUST relation; integrated in dashboard; no causal claim (DEC-037 + addendum) |
| **Integrated prototype** | **~82%** | Sector→sector layer validated; territorial attribution descriptive layer added; explanation and recommendation remain |
| **European product** | **~40%** | Multi-country sector observations integrated; influence and recommendation layers remain |

---

## State by Component

### Bloco 1 — Temporal Forecasting

| Country | Best model | WMAPE | Status |
|---------|-----------|-------|--------|
| France | HERALD Q7 | 0.0204 (2021–2025) | PENDING_REAUDIT — potential pre-causal growth feature dependency; not headline-ready |
| PT/IT/AT balanced | Persistence | ~0.0874 | VALIDATED |
| NL | Persistence | LOCO result | VALIDATED |
| BE | Persistence (Phase 4E-B b3) | 0.1488 | VALIDATED |
| Cross-country combination | 50/50 persistence+Ridge | 0.0871 | EXPLORATORY, not promoted |

**Last valid decision:** DEC-006 (Phase 4N persistence baseline); DEC-010 (Phase 4P spatial lag FAIL); DEC-011 (Phase 4Q Spatial Durbin FAIL).
**Blocker:** Conformal intervals are exploratory; no promoted interval method.
**Next step (historical — superseded by the 2026-06-18 re-audit at the top of this
file):** Observatory v0.3 complete (DEC-035). Immediate next step: extend sector
panel to AT/BE; refine explanation layer; report writing. **Current next step (see
top of file):** modularize the dashboard starting with the map; PT municipal
prediction extension; report/article writing has not started.

### Bloco 2 — Dynamic Economic Graph

#### G1-L2 Co-growth (territorial)
- **Status:** PASS for FR/NL/PT (DEC-019, DEC-020).
- **Scope:** Dense weight field within each sector; statistical co-movement association.
- **Forbidden:** Individual edge claims; causal interpretation; Louvain communities.
- **Artefact:** `data/processed/economic_graph/g1_l2_cogrowth/`

#### G2 Aggregate Dynamics (territorial co-growth temporal evolution)
- **Status:** G-14 SUPPORTED (descriptive); G-13 PARTIALLY_SUPPORTED (aggregate coherence FR-robust only).
- **Scope:** FR aggregate temporal signal robust. NL/PT COVID-sensitive.
- **Forbidden:** Individual edge stability; cross-country pooling; causal attribution.
- **Artefact:** `data/processed/economic_graph/g2_preflight/`

#### G1-L3 Territory-structure projection
- **Status:** PASS for FR/NL (DEC-016). PT excluded (KZ definitional exclusion, DEC-018).

#### G1-L1 RCA co-specialization
- **Status:** NOT_SUPPORTED (NL pass, FR fail — DEC-017).

#### Phase 5 fixed-L2 corrector
- **Status:** NOT_SUPPORTED (DEC-023). Closed.

#### P6_DDEG_S1 Dynamic dual graph
- **Status:** DUAL_GRAPH_S1_FAIL (DEC-029). All 7 gate criteria fail. Closed.
- **Sector edge labels:** INVALID_FOR_INTERPRETATION (wrong mapping in CSV, see Charter §6).
- **Index-based metrics** (MAE, Jaccard) remain numerically valid.
- **Artefact:** `data/processed/dual_graph_s1/` (frozen, historical only).

#### Graph-temporal tensors (schema 2.0 / A1 contract)
- **Status:** S1_FR_FAIL (DEC-031). GConvGRU and EvolveGCN-H both fail all 5 frozen gate criteria. Mean WMAPE: Ridge 0.06486, GConvGRU 0.06492, EvolveGCN-H 0.06497. Both models indistinguishable from temporal and territory permutation nulls (p=1.0 for GConvGRU). Leakage/seed-stability checks pass.
- **Branch status:** Graph-temporal prediction branch CLOSED. No HPC authorized. Non-graph frugal improvements (Bloco 1) and descriptive graph (Bloco 2) remain valid. Observatory v0.1 proceeds without graph-temporal correction.
- **Artefacts:** `data/processed/graph_temporal_v2/` (schema 2.0 tensors, ACTIVE); `data/processed/graph_temporal_s1/` (S1 results, FROZEN/FAIL, DEC-031)

### Bloco 3 — Economic Recommendation
- **Status:** NOT STARTED. Requires Bloco 1 + Bloco 2 complete.
- **Intelligence layer structure** exists from earlier work. Weights not validated. Rankings are hypotheses.

---

## Data Assets

| Panel | Path | Status | Rows |
|-------|------|--------|------|
| FR NUTS3 sector panel | `data/processed/economic_graph/sector_panel_fr_nuts3.csv` | ACTIVE | — |
| FR/NL/PT sector panel | `data/processed/economic_graph/sector_panel_fr_nl_pt.csv` | ACTIVE | 45 945 |
| Observatory aggregate v0.1.1 | `data/processed/herald_observatory_v01/` | ACTIVE/REGENERABLE | 1 963 |
| Observatory sector v0.2 | `data/processed/herald_observatory_v02/` | ACTIVE/REGENERABLE | 45 945 |
| PT/IT/AT harmonized LOCO | `data/processed/european_panel/enterprise_birth_pt_it_at_mainland_panel.csv` | ACTIVE | 1 963 |
| PT/IT panel (pre-AT) | `data/processed/european_panel/enterprise_birth_pt_it_panel.csv` | SUPERSEDED by AT panel | — |
| G1-L2 co-growth artefacts | `data/processed/economic_graph/g1_l2_cogrowth/` | ACTIVE (analytical) | — |
| G2 preflight artefacts | `data/processed/economic_graph/g2_preflight/` | ACTIVE (analytical) | — |
| Graph-temporal v2 tensors | `data/processed/graph_temporal_v2/` | ACTIVE (A1 blocked) | — |
| Dual graph S1 artefacts | `data/processed/dual_graph_s1/` | FROZEN/FAIL historical | — |

---

## Blocked Items

| Item | Blocker | Reopen condition |
|------|---------|-----------------|
| HPC new submission | S1_FR_FAIL (DEC-031) — graph-temporal branch closed | New information hypothesis + new DEC-* required |
| Sector→sector graph | Full 999-permutation/500-bootstrap run pending | Execute DEC-033 contract, then audit before visualization |
| Recommendation layer | Bloco 1 + Bloco 2 complete | — |
| New GNN architecture | Integrated prototype complete | New hypothesis + new data |
| Conformal intervals | Method selection | Choose between conformal or bootstrap |
| Phase 9 HPC full run | Smoke PASS (DEC-039) — full benchmark script not yet written | Implement run_full_benchmark.py, review, authorise |

---

## Phase 9 — Synthetic Benchmark (DEC-039)

**Status:** SMOKE PASS (2026-06-13). Architecture validated.

- Generator: 10T × 5S × 12Y synthetic economic panel with ground truth relations, crises, structural breaks, MCAR/MAR/block missing patterns
- Baselines B1–B8 implemented and tested
- Temporal features: strictly causal (no future leakage, verified)
- Smoke: 2 seeds, MCAR 20%, 100 epochs → 1.7s, no NaN, leakage PASS
- G1/G3 gates NOT yet evaluable at smoke scale (require full HPC run, not yet authorised)

**Next:** Implement `run_full_benchmark.py`; authorise HPC after review.

---

## DEC-066 — Fine-Grain Threshold Calibration (2026-06-16)

**Status:** `FINE_GRAIN_THRESHOLD_POLICY_READY`. 10/10 gates PASS. 43/43 tests PASS.

- **Original threshold 0.10 (ROBUST_ORIGINAL):** unchanged — pre-registered DEC-034/DEC-064.
- **Supplementary threshold 0.09 (FINE_GRAIN_SUPPORTED):** adopted. Requires bss≥0.80 PLUS one of: (a) COVID-robust; (b) ≥2 consecutive windows same sign; (c) cross-country replication.
- **EXPLORATORY_FINE_GRAIN (0.07-0.09, bss≥0.90):** documented, NOT a training label.
- Ecological scale effect confirmed: PT NUTS3 max|β|=0.362 → NL COROP 0.285 → FR/PT_MUNI ≈0.10-0.13.
- NL proxy (DEC-065) may now proceed under this policy. KZ→FZ FR cannot transfer to PT labels.

**Label counts:** FR=1 ROBUST + 3 FINE_GRAIN + 5 EXPLORATORY; NL=8 ROBUST; PT_NUTS3=16 ROBUST; PT_MUNI=2 ROBUST + 1 EXPLORATORY.

**Policy:** `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json`

**Next:** DEC-065 (NL gemeente proxy, now authorised); DEC-067 (FR/PT label export).

---

## Observatory v0.4.1 Visual Upgrade — PT Map + Dynamic Graph (2026-06-17)

**Status:** `OBSERVATORY_V041_VISUAL_READY`. 41/41 new tests PASS (241/241 total).

- **PT geometry (Part A):** previously missing. Obtained via geoapi.pt
  (redistributes DGT/CAOP municipal boundaries; GeoJSON properties
  Dicofre/Concelho/Distrito match CAOP schema). 278/278 continental
  municipalities matched to the panel's 7-digit geocods by normalised name
  (no code-to-code assumption — the two ID schemes are unrelated). 0 unmatched
  panel names; 30 unmatched geoapi names = exactly the Açores+Madeira set
  (confirms correct exclusion). Simplified 0.001° for embedding: 29.7 MB → 1.18 MB.
  Builder: `src/data/european_panel/build_pt_municipality_geometry.py`. Output:
  `data/processed/geometries/pt_municipalities_continental.geojson` +
  `_manifest.json` (status=COMPLETE_278_278).
- **PT map (Part B):** dashboard now renders PT as a real choropleth (was
  table fallback). Fallback logic preserved: if geometry/manifest status is
  ever missing, PT silently reverts to the table view rather than fabricating
  a map.
- **Dynamic graph (Part C):** timeline slider over the 6 windows present in
  `granular_relation_edges.csv` (2009-2014…2020-2025), play/pause animation,
  3 modes (current window / cumulative until window / recurring edges only),
  🔁/⚠/⭐ markers for recurring/sign-changing/exclusive-to-one-window edges,
  per-window edge history table in the detail panel, and a relation×window
  mini heatmap (β sign/intensity).
- **Map↔graph linking (Part D):** selecting a country on the map filters the
  graph; selecting a sector highlights its incoming/outgoing edges (dims the
  rest); clicking a graph edge shows an aggregate territory-state distribution
  for that country/region_system/window — explicitly labelled as context, not
  an edge-specific territorial attribution.
- **Methodological protection (Part E), re-verified:** `GEMEENTE_PROXY` still
  absent from `RELATION_EDGES` (20 edges, unchanged); 121 `BLOCKED_EDGES`
  still isolated in their own panel, `allowed_for_training_label=false`;
  DEC-066 label classes unchanged; no forbidden causal language.
- **Tests:** `tests/test_observatory_v041_visual_upgrade.py` (41/41 PASS).
- **Visual validation:** Playwright/headless browser still unavailable in
  this environment — validated via HTML/JS structural checks and embedded-data
  assertions (same approach as the v0.4 milestone). Manual validation
  recommended: open the dashboard, switch the map source to Portugal and
  confirm a real choropleth renders, drag the timeline slider/press Play and
  confirm the graph and heatmap update, click an edge and confirm the
  per-window table and territory-state context appear.
- **Dashboard:** `reports/dashboards/herald_observatory_v04_granular_dashboard.html`
  (10.0 MB). v0.3 dashboard untouched.
- **Raw geometry cache** (`data/external/portugal/geometry/raw/`, 181 MB) is
  gitignored — regenerable via the builder script, not committed.

**Next:** none required for this task; future work could add an analogous
NL gemeente choropleth (still context-only, never relation-graph) if gemeente
geometry becomes available, or extend the dynamic graph to FR/PT NUTS3 scale
comparisons.

---

## Observatory v0.4 Granular Dashboard (2026-06-17)

**Status:** `OBSERVATORY_V04_DASHBOARD_READY`. 41/41 dashboard tests PASS (200/200 total across DEC-065/066/Observatory-policy/dashboard suites).

- **File:** `reports/dashboards/herald_observatory_v04_granular_dashboard.html` (9.0 MB, Plotly embedded locally — works fully offline, no CDN).
- **Map (Layer 1):** FR ZE2020 + NL COROP render as a real choropleth (geometry from `data/external/ze2020_geometry.geojson` and NUTS3 via the NL_COROP_TO_NUTS3 crosswalk, reused from v0.3). PT Municipality and NL gemeente proxy have no embedded municipal/gemeente geometry — they render as a sortable, colour-coded table (state heatmap), an explicit fallback rather than a fabricated map. NL gemeente rows always carry a `proxy/context — not valid for relation labels` badge.
- **Relation graph (Layer 2):** circular sector layout built ONLY from `granular_relation_edges.csv` (20 edges: FR=9, NL COROP=8, PT Municipal=3). Styled by `label_class` (solid/dashed/dotted) and `sign` (colour), width by |β|. NL gemeente proxy is structurally absent — verified by parsing the embedded `RELATION_EDGES` JS blob in tests.
- **Blocked panel (Layer 3):** all 121 NL gemeente proxy edges in a dedicated "Blocked proxy artifacts" table, `allowed_for_training_label=false`, `reason=stock_share_induced_artifact`, never rendered as graph edges.
- **Evidence/export (Layer 4-5):** KPI counts, manifest checksums, DEC references, CSV/manifest download links, embedded manifest modal.
- **Builder:** `src/data/european_panel/build_observatory_v04_dashboard.py` — fail-closed asserts at build time (GEMEENTE_PROXY never in relation edges; blocked edges always non-trainable).
- **Tests:** `tests/test_observatory_v04_dashboard.py` (41/41 PASS) — existence/well-formedness, dataset references, hard-rule isolation, UI elements, language rules, builder determinism/checksums.
- **Visual validation:** Playwright/headless browser not available in this environment; validated via HTML structural checks and embedded-data assertions instead of screenshot. Manual validation: open the file directly in a browser and confirm map/graph/tables render (see report for checklist).
- v0.3 dashboard (`herald_observatory_v03_dashboard.html`) untouched.

**Next:** dashboard is ready for manual visual confirmation in a browser; no further action required unless visual review surfaces issues.

---

## DEC-065 — NL Gemeente Proxy Phase 7 (2026-06-17)

**Status:** `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` (manual override). 71/71 tests PASS. HPC job 7475756 (252/252 complete).

- **Automated gate-count verdict would have been `SUPPORTED`** (121 promoted, 97 nominally COVID-robust, 7/8 COROP pairs preserved) — but this is overridden.
- **Critical structural finding:** DEC-063 proxy method (`estimated_births_gemeente = corop_births × stock_share`) injects cross-sector-correlated noise unrelated to births precedence. Decomposition: `share_velocity` coefficient (13.0) ~10x larger than `corop_velocity` coefficient (1.33), R²=0.635. `share_velocity` cross-sector correlation 0.34-0.82 (general local stock co-movement, e.g. gentrification — not births dynamics).
- This explains the implausible 15x jump in promoted edges (8 COROP observed → 121 gemeente proxy), opposite of the ecological-fragmentation pattern (finer units → fewer effects) confirmed in DEC-064/066.
- **None of the 121 promoted/97 COVID-robust gemeente edges may be used as DEC-066 training labels under any tier.**
- NL COROP (8 promoted, 3 COVID-robust, observed) remains the valid NL baseline.

**Artefacts:** `data/processed/phase7_nl_gemeente_proxy/results/` (all_edges.csv, decision.json, structural_validity_diagnostic.json), `nl_corop_vs_gemeente_proxy_comparison.csv`, `nl_gemeente_proxy_label_summary.json`

**Full audit:** `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md`

**Consolidation (2026-06-17):** All 121 gemeente proxy edges explicitly marked
`INVALID_FOR_TRAINING_LABELS` (label_class=`BLOCKED_PROXY_ARTIFACT`,
`allowed_for_training_label=false`). Artifact registry adds explicit
`NL_GEMEENTE_PROXY_PHASE7_BLOCKED` (status=`BLOCKED`,
relation_label_status=`INVALID_FOR_RELATION_LABELS`) and `NL_COROP_PHASE7`
(status=`VALID_OBSERVED`) entries. New policy document
a policy (now summarized in `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`) defines observed vs proxy evidence
boundaries, label classes (`ROBUST_ORIGINAL`/`FINE_GRAIN_SUPPORTED`/
`EXPLORATORY_FINE_GRAIN`/`BLOCKED_PROXY_ARTIFACT`/`INSUFFICIENT_EVIDENCE`), and
language rules. Observatory v0.4 granular contract
(`reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md`, 4 layers) + clean exports
in `data/processed/herald_observatory_v04_granular/`:
- `granular_territory_state_panel.csv` (142,650 rows: FR ZE2020 + PT Municipal +
  NL COROP observed + NL gemeente proxy tagged `allowed_use=territory_state_context_only`)
- `granular_relation_edges.csv` (20 rows: FR=9, NL COROP=8, PT Municipal=3 — NL
  gemeente proxy structurally excluded)
- `blocked_proxy_edges.csv` (121 rows, `BLOCKED_PROXY_ARTIFACT`)
- `manifest.json` (checksums, DEC references, hard rules)

159/159 tests pass (71 DEC-065 + 45 `test_observatory_v04_granular_evidence_policy.py`
+ 43 DEC-066). **Decision: `GRANULAR_OBSERVATORY_V04_DATA_READY`** — data layer
complete and tested; dashboard build is a separate, larger task not yet authorised.

**Next:** DEC-065b (proposed) — re-specify gemeente regression with COROP-clustered SEs or COROP×year FE before re-testing. DEC-068 (cross-country granular training) must exclude NL gemeente proxy edges, limit NL contribution to COROP scale. DEC-067 (FR/PT label export, unaffected by this finding) remains open. Observatory v0.4 dashboard build requires separate authorisation.

---

## Phase 7: DEC-064 — PT Municipal Phase 7 (2026-06-16)

**Status:** `PT_MUNICIPAL_PHASE7_COMPLETE`. 10/10 gates PASS. Job 7472757 (208/208 complete).

- **2 COVID-robust promoted pairs** — both in window 2015-2020 only:
  - GI→OQ: β=+0.130, q_fdr=0.028, bss=1.00, n=1668 (COVID-robust: β_wo2020=+0.108)
  - MN→JZ: β=−0.104, q_fdr=0.037, bss=1.00, n=999 (COVID-robust: β_wo2020=−0.125)
- Both pairs are **period-specific** (2015-2020); no other window produces promotions.
- Ecological fragmentation: NUTS3 max|β|=0.362 vs municipal max|β|=0.130 (smaller units, smaller effects).
- NUTS3 baseline: 0 promoted in all 14 windows. Municipal 278 territories provides 11× statistical power.
- DEC-065 DRAFT preparado: `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_DRAFT.md`.

**Artefacts:** `data/processed/phase7_pt_municipal/results/` (all_edges.csv, latest.csv, covid_robust_edges.csv)

**Next:** DEC-065 (NL gemeente proxy — now authorised, policy DEC-066 in place); DEC-067 (FR/PT label export with fine-grain policy).

---

## Phase 4: DEC-063 — Granular FR/PT/NL Evidence Model (2026-06-16)

**Status:** COMPLETE. Decision: `GRANULAR_FR_PT_NL_PREFLIGHT_READY` — 10/10 gates PASS, 66/66 tests PASS.

- **FR ZE2020 (280 units):** observed_births, SIDRE establishment_creation. READY.
- **PT Municipal (278 units):** observed_births, INE enterprise_birth. KZ structural_absent. READY_WITH_LIMITATION.
- **NL COROP (40 units):** observed_births, CBS 83631NED. KZ present. READY.
- **NL Gemeente proxy (355 units):** proxy_disaggregated_by_stock_share. 73% proxy_computed. Reaggregation exact (max_abs=0.0).
- CBS API 10k-row limit resolved: year-loop strategy (19 calls × 9,177 rows).
- Contract: `reports/HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md` — evaluation must report observed-only and proxy-excluded sensitivity separately.

**Next:** HPC authorisation for full run (208 tasks); or await local medium run (~6h). DEC-065 draft prepared (awaiting DEC-064 completion).

---

## Phase 13 — DEC-048 Failure Cause Diagnostic (DEC-048)

**Status:** PILOT_COMPLETE (2026-06-15). Decision: TRAINING_BUDGET_TOO_SMALL.

- OFAT design: 4 axes (D/M/L/S) + functional scenario test + gradient diagnostics + masked pretraining
- 6/10 gates PASS. 21 tests PASS. Runtime: 79s.
- C2 PASS: Oracle beats ffill by 27% in functional scenario (ratio=0.732) — architecture NOT inadequate
- Attention gradient 400x smaller than MLP under NLL — flat gradient landscape for graph learning
- GRAPH_MASKED_MULTITASK pretraining +1.1% MAE benefit vs NO_PRETRAINING (25 datasets, 50 epochs)
- S3 (structural_break_year=8) causes catastrophic degradation (ratio=1.45)
- Package: `src/modeles/synthetic/phase13_diagnostic/`
- Report: `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md`

**Next:** DEC-049 — Full-scale pretraining (n_epochs=150, 50 D2 datasets, GRAPH_MASKED_MULTITASK), then rerun DEC-047 few-shot strategies.

---

## Reference Documents

- Direction and claims: `reports/HERALD_PROJECT_CHARTER.md`
- All decisions: `reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (DEC-001→DEC-068)
- Claims classification: `reports/canonical/HERALD_04_RESULTS_EVIDENCE_AND_CLOSED_BRANCHES.md`
- Gantt: `reports/canonical/HERALD_05_OBSERVATORY_DASHBOARD_AND_ARTICLE_ROADMAP.md`
- HPC registry: `hpc/hpc_phase_registry.json`
- Artefact manifest: `reports/herald_artifact_registry.json`
- Active document index: `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`
