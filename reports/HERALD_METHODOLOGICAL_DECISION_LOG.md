# HERALD — Methodological Decision Log

**Created:** 2026-06-10  
**Rule:** Never delete old entries. Corrections add new entries pointing to superseded ones.  
**Format:** date · phase · question · evidence · alternatives · decision · rationale · limitations · reopen condition · affected files

---

## DEC-001 — 2026-06-03 — Temporal leakage in growth_1y

**Phase:** 4A / 4D  
**Question:** Are Phase 4A/4D WMAPE results valid as scientific baselines?  
**Evidence:** `growth_1y[t] = (y[t] − y[t-1]) / y[t-1]` uses the forecast target `y[t]` directly. The feature is computed at training time and therefore leaks the target into all models that use it.  
**Alternatives considered:** Partial correction keeping some features; full recompute.  
**Decision:** Classify Phase 4A/4D results as LEGACY/LEAKAGE-AFFECTED. All baseline comparisons must use Phase 4E-B (causal recompute) or later.  
**Rationale:** Any model using a leaky feature in its training or evaluation is invalid as a scientific claim of predictive performance. The error is systematic and affects all countries.  
**Limitations:** Historical runs cannot be retroactively fixed; only reran results qualify.  
**Reopen condition:** Cannot be reopened; decisions from this phase must be re-executed under causal protocol.  
**Affected files:** `reports/HERALD_PHASE4E_A2_DEGRADATION_AUDIT.md`; `src/data/ingest_belgium_panel.py`; `src/data/ingest_netherlands_panel.py`; `src/data/ingest_portugal_panel_nuts3.py`

---

## DEC-002 — 2026-06-04 — Causal baseline per country (Phase 4E-B)

**Phase:** 4E-B  
**Question:** What is the correct per-country causal baseline for enterprise-birth forecasting?  
**Evidence:** Feature-policy ablation (180 runs, 12 configs × 10 seeds per country) with `growth_1y[t] = (y[t-1] − y[t-2]) / y[t-2]` (past-only). Best per-country configs identified.  
**Alternatives considered:** Single global config; pooled selection.  
**Decision:** Best per-country configs adopted as canonical baseline. Per-country WMAPE is the primary metric; pooled WMAPE is not admissible as a main result.  
**Rationale:** Countries differ in data availability, region counts and economic dynamics. A single pooled config would hide country-level failures.  
**Limitations:** n=4 countries; seeds are not independent domains; no power for universal generalization claim.  
**Reopen condition:** New countries added to the panel.  
**Affected files:** `reports/HERALD_PHASE4E_B_RESULTS_AUDIT.md`; `hpc/phase4/`

---

## DEC-003 — 2026-06-06 — Semantic target gate FAIL for unified European target

**Phase:** 4J  
**Question:** Can FR / NL / BE / PT targets be treated as semantically equivalent for a unified generalization claim?  
**Evidence:** FR = établissement creations (SIDE/SIRENE), NL = local unit openings (CBS), BE = first VAT registrations (StatBel), PT = enterprise births (INE). Conceptual differences documented in `HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md`.  
**Alternatives considered:** Continue with heterogeneous targets using Path M; build Path H harmonized panel.  
**Decision:** Gate FAIL for unified target. Path M = heterogeneous multitask with explicit per-target framing. Path H = harmonized `enterprise_birth` subpanel (Eurostat `bd_size_r3`, OECD demographic concept).  
**Rationale:** A mean WMAPE over incommensurable targets does not constitute evidence of generalization.  
**Limitations:** Path H currently limited to PT + IT + AT (3 countries); FR/NL/BE remain in Path M only.  
**Reopen condition:** Documentary proof of equivalence for FR or NL target under a declared shared definition.  
**Affected files:** `reports/HERALD_PHASE4J_SEMANTIC_TARGET_AUDIT.md`; `reports/HERALD_PHASE4J_TARGET_EQUIVALENCE_TABLE.md`

---

## DEC-004 — 2026-06-07 — Forecast combination (50/50) not promoted

**Phase:** 4J-A  
**Question:** Does equal-weight `0.5 × persistence + 0.5 × Ridge` qualify as a promoted model?  
**Evidence:** Balanced WMAPE drops from 0.0939 to 0.0871 (−7.3%). But worst-year performance degrades in FR and PT; learned weights from source countries do not transfer safely to target country.  
**Alternatives considered:** Learned combination weights; adaptive weighting.  
**Decision:** Combination result is EXPLORATORY. Not promoted. Persistence remains best-balanced baseline.  
**Rationale:** Tail-risk regression and non-transferable weights disqualify as a safe general model.  
**Limitations:** n=4 country domains; combination not tested on held-out countries.  
**Reopen condition:** New target country with demonstrated safe weight transfer.  
**Affected files:** `reports/HERALD_PHASE4J_A_FORECAST_COMBINATION_AUDIT.md`

---

## DEC-005 — 2026-06-09 — Austria selected as third harmonized country; FR/ES/CZ blocked

**Phase:** 4K / 4M  
**Question:** Which Eurostat `bd_size_r3` country qualifies for the harmonized Path H panel (2008–2020, stable mainland NUTS3)?  
**Evidence:** AT: 35 stable mainland NUTS3, complete 2008–2020, same `V11920 TOTAL` indicator. FR: only 8 codes survive without crosswalk. ES: no region complete for full window. CZ: <20 regions, starts 2010.  
**Alternatives considered:** Shorter window for FR; crosswalk for ES.  
**Decision:** Austria integrated. FR/ES/CZ remain BLOCKED without explicit crosswalk or revised window.  
**Rationale:** Pre-registered gate required complete stable NUTS3 coverage for 2008–2020. No exceptions post-hoc.  
**Limitations:** 3-country panel (PT/IT/AT) still limited for LOCO claims. 3 domains provide weak domain power.  
**Reopen condition:** Documented NUTS crosswalk for FR or ES; or revised window (e.g. 2010–2020) re-preregistered before analysis.  
**Affected files:** `reports/HERALD_PHASE4M_THIRD_COUNTRY_PREFLIGHT.md`; `data/processed/european_panel/at_panel.csv`

---

## DEC-006 — 2026-06-09 — Phase 4N: persistence is best-balanced baseline; no model promoted

**Phase:** 4N  
**Question:** Does the residual Ridge or nested mix model transfer across PT/IT/AT under LOCO?  
**Evidence:** Balanced WMAPE: persistence 0.0874, n3_residual 0.0865, n4_mix 0.0881. n3 gain concentrated in PT only (1/3 countries). IT and AT degrade under n3. Promotion gate requires ≥2/3 countries improve.  
**Alternatives considered:** Promoting n3 on PT-specific basis.  
**Decision:** No model promoted. Persistence is the canonical LOCO baseline. n3 improvement in PT is real but not robust.  
**Rationale:** A balanced baseline claim requires consistent improvement across all domains, not concentration in one.  
**Limitations:** 3 countries; Ridge direct fails catastrophically due to scale mismatch (not a model failure per se, a protocol issue).  
**Reopen condition:** Scale-invariant direct model or ≥4 harmonized countries.  
**Affected files:** `reports/HERALD_PHASE4N_RESULTS_AUDIT.md`; `hpc/phase4/run_phase4n_harmonized_loco.py`

---

## DEC-007 — 2026-06-09 — Phase 4O-C: multi-country Phase 4P not authorized (1/3 gate)

**Phase:** 4O-C  
**Question:** Do residuals show robust spatial autocorrelation across ≥2/3 countries (IT/PT/AT)?  
**Evidence:** IT: PASS (robust relative + causal Moran's I, multiple years, LOO-stable). PT: FAIL (LOO instability in 3–3 of significant years). AT: FAIL (signal only in absolute residuals, likely heteroscedasticity). Pre-specified gate: ≥2/3. Observed: 1/3.  
**Alternatives considered:** Relaxing LOO threshold; accepting AT absolute signal.  
**Decision:** Multi-country Phase 4P NOT authorized. Italy-only linear spatial-lag diagnostic authorized.  
**Rationale:** Pre-specified gate not met. Relaxing post-hoc would be cherry-picking.  
**Limitations:** PT's failure is partly structural (23 NUTS3; 1 region = 4% of panel). AT failure may reflect genuine heteroscedasticity, not absence of spatial structure.  
**Reopen condition:** New evidence: ≥1 additional harmonized country with robust relative residual spatial signal.  
**Affected files:** `reports/HERALD_PHASE4O_B_RESIDUAL_SPATIAL_AUDIT.md`; `hpc/phase4/run_phase4o_c_residual_spatial_diagnostic.py`

---

## DEC-008 — 2026-06-10 — Phase 4P FAIL: queen-contiguity birth lag rejected

**Phase:** 4P  
**Question:** Does adding `W × births[t-1]` (queen-neighbour lag) improve Italy rolling-origin WMAPE?  
**Evidence:** Real graph WMAPE 0.056185 vs persistence 0.054946 (+2.26%) and Ridge 0.056204 (marginal). 18/99 permuted controls tie/beat real graph (p=0.19). Real graph wins only 4/9 years vs persistence. Moran's I does not decrease.  
**Alternatives considered:** Extending to multi-country; using different weight normalization.  
**Decision:** FAIL. Tested feature rejected. Final bounded ablation (Spatial-Durbin) authorized.  
**Rationale:** p=0.19 is not significant; the real graph has no advantage over topology-randomized controls.  
**Limitations:** Only one type of spatial lag (birth count at t-1) tested. Does not prove all graph representations are useless.  
**Reopen condition:** New independent evidence (new country, justified functional/mobility network, new data window).  
**Affected files:** `reports/HERALD_PHASE4P_ITALY_SPATIAL_LAG_AUDIT.md`; `hpc/phase4/run_phase4p_italy_spatial_lag.py`

---

## DEC-009 — 2026-06-10 — Phase 4Q FAIL: Spatial-Durbin block rejected; geographic graph branch closed

**Phase:** 4Q  
**Question:** Does a fixed Spatial-Durbin block (neighbour means of all common covariates) improve Italy forecasts?  
**Evidence:** Real block WMAPE 0.058214 vs persistence 0.054946 (−5.95%) and Ridge 0.056204 (−3.58%). p=0.32 (31/99 controls tie/beat). Relative Moran barely decreases (0.2642 → 0.2602).  
**Alternatives considered:** Feature-selected spatial lags; non-linear spatial model.  
**Decision:** FAIL. Geographic queen-contiguity graph branch CLOSED under current 2008–2020 PT/IT/AT data. No STGNN, no HERALD graph training, no multi-country graph.  
**Rationale:** Both pre-registered geographic ablations (4P + 4Q) failed the gate. Further search without new evidence would be p-hacking.  
**Limitations:** Covers only linear geographic lags. Does not cover: sector-similarity graphs, commuting networks, functional economic area networks, learned sparse graphs.  
**Reopen condition:** New harmonized country; separately justified functional/mobility network; new data window post-2020.  
**Affected files:** `reports/HERALD_PHASE4Q_ITALY_SPATIAL_DURBIN_AUDIT.md`; `hpc/phase4/run_phase4q_italy_spatial_durbin.py`

---

## DEC-010 — 2026-06-10 — New strategic direction: economic dynamic graph (not geographic)

**Phase:** Post-4Q  
**Question:** What is the next scientific direction after geographic graph closure?  
**Evidence:** Geographic contiguity lags (4P/4Q) failed. However: (1) spatial residual autocorrelation in IT is real (4O-C); (2) sector and employment data exist partially; (3) economic complexity and relatedness literature provides principled graph definitions beyond geography.  
**Alternatives considered:** (A) Add a new harmonized country. (B) Develop non-geographic economic dynamic graph. (C) Move to synthetic data experiments. (D) Abandon graph entirely.  
**Decision:** Pursue Bloco 2 (economic dynamic graph) as a separate scientific track, parallel to Bloco 1 (temporal forecasting improvements). Geographic graph branch remains closed; economic graph is a new track requiring G0 conceptual gate before any implementation.  
**Rationale:** The rejection of geographic contiguity lags (which test one specific and arguably weak form of spatial dependence) does not invalidate the economic rationale for sector-territory relational graphs. The two tracks serve different scientific purposes: Bloco 1 = forecasting accuracy; Bloco 2 = economic interpretation and eventual recommendation.  
**Limitations:** Economic dynamic graph requires new data (sector A10, commuting, input-output) and new methodology. Italy lacks NUTS3 sector employment coverage in `bd_size_r3`.  
**Reopen condition:** Not applicable — this is an opening, not a closure.  
**Affected files:** `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` (new); `reports/HERALD_RESEARCH_GANTT.md` (new)

---

## DEC-011 — 2026-06-10 — Gate: no economic graph implementation authorized without G0 contract

**Phase:** Post-4Q / Pre-G1  
**Question:** Under what conditions may implementation of the economic dynamic graph begin?  
**Evidence:** Decision DEC-010. No formal node/edge definition yet. No data inventory. No null model specified.  
**Decision:** Implementation BLOCKED until all 10 G0 gate items are satisfied (see `HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` § Gate).  
**Items required:**
1. Formal node and edge definition with semantic meaning  
2. Data availability confirmed for ≥2 countries  
3. Falsifiable hypothesis  
4. Baseline (persistence or Ridge)  
5. Null model (permuted graph)  
6. Causal temporal protocol (no leakage)  
7. Stability metrics defined  
8. Acceptance criteria pre-registered  
9. Permitted claims listed  
10. Post-experiment audit plan  
**Rationale:** Phase 4P/4Q taught that graph experiments without pre-registered gates lead to ambiguous closure. G0 contract prevents this.  
**Affected files:** `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md`

---

## DEC-012 — 2026-06-10 — Sector A10 nucleus corrected: FR+NL+PT, not PT/IT/AT

**Phase:** Post-4Q / G0 preparation  
**Question:** Which countries provide sector A10 enterprise births at NUTS3 for the dynamic economic graph nucleus?  
**Evidence:** Panel inspection 2026-06-10 — `mask_sector_a10`: FR=0.923, NL=1.000, PT=0.941, BE=0.000, IT=0.000, AT=0.000. `bd_size_r3` for IT/AT uses aggregate NACE `B-S_X_K642`. `bd_hgnace_r_raw.csv` provides FR/NL/PT sector births 2019–2023. Commuting files confirmed for NL, BE, PT.  
**Alternatives considered:** Include IT/AT with aggregate only; wait for new Eurostat sector release.  
**Decision:** Sector graph nucleus = FR + NL + PT. BE = employment-only complement. IT and AT remain in Path H aggregate LOCO but not in sector graph nucleus.  
**Rationale:** Cannot build a sector graph without sector data. Masks are unambiguous.  
**Limitations:** FR/NL/PT graph may not generalize to IT/AT economic structures.  
**Reopen condition:** Eurostat releases NUTS3-level A10 births for IT or AT via `bd_hgnace_r` or equivalent.  
**Affected files:** `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md`; `reports/HERALD_RESEARCH_GANTT.md`; `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md`

---

## DEC-013 — 2026-06-10 — AT and IT A10 claims removed

**Phase:** G0 preparation  
**Question:** Does AT or IT provide complete A10 sector births at NUTS3?  
**Evidence:** Panel inspection: `at_panel.csv` `mask_sector_a10=0.000`, `sector_BE not-null=0.000`; same for `it_panel.csv`. Source is `bd_size_r3` with NACE aggregate `B-S_X_K642`. No territorial sector disaggregation.  
**Decision:** All claims that "AT has complete A10" or "IT has sufficient A10 for G1" are incorrect and removed. AT and IT provide total enterprise births and stock for Path H aggregate only.  
**Rationale:** Panel mask is authoritative. Mask=0 is unambiguous.  
**Reopen condition:** New Eurostat `bd_hgnace_r` extract covers AT or IT at NUTS3 with sector disaggregation.  
**Affected files:** `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md` (corrected); `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_LITERATURE_REVIEW.md`

---

## DEC-014 — 2026-06-10 — Official visualization base: France dashboard

**Phase:** G0 preparation / Bloco 2  
**Question:** Should a new dashboard be created from scratch for the economic graph, or should the existing France dashboard be adapted?  
**Evidence:** `reports/dashboards/herald_france_final_dashboard.html` implements: interactive choropleth map, territory selection, A10 sector breakdown, time series navigation, and rolling forecast visualization. Separate European panel dashboard also exists (`herald_phase4e_europe_dashboard.html`). Recreating map/navigation/sector components from scratch is unnecessary work.  
**Decision:** `herald_france_final_dashboard.html` is the official visual base. No new dashboard from scratch. Incremental adaptations only.  
**Rationale:** Reuse tested components. Avoid parallel dashboard fragmentation. Graph layer added only after G1 is validated (G4 pass).  
**Planned adaptations (deferred to Gantt Phase 4, task 4.4):**
- Country selector: FR, NL, PT, BE
- Year, territory, and sector A10 selectors
- G1 graph layer: nodes, edges, weight, stability, communities, evolution
- Edge type legend: geographic, economic, mobility, learned
- Territory click → sector breakdown + time series + forecast + graph neighbors
- Real geometries with declared granularity
- All labels must distinguish association from causality  
**Forbidden in this task and any task until G1 validated:** modify `herald_france_final_dashboard.html`; generate a new HTML dashboard.  
**Limitations:** Adaptation scope and complexity unknown until G1 graph structure is finalized.  
**Reopen condition:** G1 validated; supervisor confirms dashboard requirements.  
**Affected files:** `reports/HERALD_DYNAMIC_ECONOMIC_GRAPH_ROADMAP.md`; `reports/HERALD_RESEARCH_GANTT.md`; `README.md`
