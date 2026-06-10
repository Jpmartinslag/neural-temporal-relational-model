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
**Rationale:** Reuse tested components. Avoid parallel dashboard fragmentation.
Graph layer added only after L1, L2 and L3 are validated under G4; the current
L3 result alone is insufficient.
**Planned adaptations (deferred to Gantt Phase 4, task 4.4):**
- Country selector: FR, NL, PT, BE
- Year, territory, and sector A10 selectors
- G1 graph layer: nodes, edges, weight, stability, communities, evolution
- Edge type legend: geographic, economic, mobility, learned
- Territory click → sector breakdown + time series + forecast + graph neighbors
- Real geometries with declared granularity
- All labels must distinguish association from causality  
**Forbidden in this task and any task until L1/L2/L3 are validated:** modify
`herald_france_final_dashboard.html`; generate a new HTML dashboard.
**Limitations:** Adaptation scope and complexity unknown until G1 graph structure is finalized.  
**Reopen condition:** L1/L2/L3 validated; supervisor confirms dashboard
requirements.

---

## DEC-015 — 2026-06-10 — G0 frozen; clean sector vocabulary excludes agriculture

**Phase:** G0 / Pre-G1
**Question:** Can the observable economic graph preflight begin, and what is its
common sector vocabulary?
**Evidence:** FR, NL and PT unlagged national sector sources are locally
available. The legacy nine-sector predictive builders folded agriculture `A`
into `OQ` for NL/PT, which is not a clean European business-sector contract.
France currently has aggregate quarterly URSSAF employment, not a verified
ZE-by-A10 employment file.
**Decision:** Freeze `reports/HERALD_G0_FORMAL_CONTRACT.md` at 10/10. Build the
analytical graph panel from unlagged sources using
`BE,FZ,GI,JZ,KZ,LZ,MN,OQ,RU`; exclude agriculture rather than folding it into
`OQ`. Preserve legacy predictive files unchanged. Use BE employment as a
separate complementary layer.
**Rationale:** This prevents off-by-one temporal labels and sector-definition
contamination while retaining reproducibility of prior forecasting runs.
**Limitations:** Territorial systems and target concepts still differ. Raw
counts cannot be pooled across countries.
**Reopen condition:** A future harmonized source provides a documented common
territorial and sector definition.
**Affected files:** `reports/HERALD_G0_FORMAL_CONTRACT.md`;
`src/data/european_panel/build_dynamic_sector_preflight.py`.

---

## DEC-016 — 2026-06-10 — G1-L3 territory-structure projection validated

**Phase:** G1 / G4-lite
**Question:** Does the observable sector-structure graph contain stable
territory-specific information beyond structure-preserving nulls?
**Evidence:** FR and NL beat temporal and territory-identity nulls after
BH/FDR (`q=0.005`), pass leave-one-year-out direction checks, contain stable
bootstrap edges, have one connected component per snapshot and no isolated
nodes. PT was removed from the validated set after detecting `KZ=0` in every
territory and year despite an observed mask. Clean validated windows are FR
2012–2025 and NL 2015–2025.
**Decision:** G1-L3 territory-structure similarity PASS for analytical use.
Authorize economic-coherence review and bounded interpretive dynamics. L1
sector-sector, L2 co-growth, L4 mobility and L5 geography remain unvalidated.
Do not authorize GNN
training, causal claims, recommendation claims or dashboard modification yet.
**Rationale:** The tested graph captures persistent country-specific economic
structure beyond temporal and territory-label nulls. Prediction was not part
of this gate.
**Limitations:** Similarity may reflect stable size/composition effects;
territorial systems and target concepts differ; bootstrap edge stability is
project-specific; external economic validation remains pending.
**Reopen condition:** G3-lite dynamics or economic-coherence audit reveals
instability or semantic failure.
**Affected files:** `reports/HERALD_G1_OBSERVABLE_GRAPH_AUDIT.md`;
`data/processed/economic_graph/g1_observable/`.

---

## DEC-017 — 2026-06-10 — G1-L1 RCA sector graph fails common promotion gate

**Phase:** G1 / G4-lite
**Question:** Does RCA-based sector co-specialization provide a reproducible
sector-sector relation in at least two countries?
**Evidence:** NL passes temporal and configuration nulls after BH/FDR
(`q=0.01`) and LOYO. FR has high raw stability (`0.9797`) but the temporal and
configuration nulls are equally or more stable (`q=1.0`), so stable marginal
sector prevalence explains the result. PT is ineligible because `KZ` has zero
mass in every territory/year.
**Decision:** L1 FAIL and is not promoted. Do not tune thresholds or replace
the formula after observing the result. Keep L3 descriptive in FR/NL and move
to the pre-specified L2 causal co-growth test after auditing PT `KZ`.
**Rationale:** High raw stability is insufficient when null models reproduce
it. The failed gate prevents converting persistent composition into a false
claim of economic relatedness.
**Limitations:** Only one observable L1 definition was tested. Failure does not
prove that all sector-relatedness definitions are invalid.
**Affected files:** `reports/HERALD_G1_L1_SECTOR_GRAPH_AUDIT.md`;
`data/processed/economic_graph/g1_l1_sector/`.

---

## DEC-018 — 2026-06-10 — PT sector KZ formally unavailable: INE structural exclusion

**Phase:** G1 preflight
**Question:** Does `sector_KZ` zero mass in Portugal represent an economic zero,
a mapping error, or a structural data absence?
**Evidence:** INE Portugal indicator 0009703 (enterprise births by NUTS3 and CAE
section) never includes section K (Financial and insurance activities) in any
year 2008–2022.  Available sections in all years: A, B, C, D, E, F, G, H, I,
J, L, M, N, P, Q, R, S, TOT.  K is completely absent.  Root cause: INE follows
the Eurostat/OECD enterprise demography convention excluding the financial
sector, which is regulated by Banco de Portugal and not covered in standard firm
demography statistics.  Evidence chain: raw JSON files
`data/external/portugal/raw/ine/0009703_*.json` → `portugal_qtensor_births_cae_nuts3.csv`
(KZ births all=0) → `pt_adapter.py` (KZ passes through as zero) →
`sector_panel_fr_nl_pt.csv` (`mask_sector_supported=0` for PT KZ).
**Decision:** PT KZ is formally unavailable.  `mask_sector_supported=0` for PT
KZ is correct.  PT is excluded from the nine-sector gate (L1, L3).  PT is
eligible for L2 with an eight-sector vocabulary (KZ excluded), explicitly
labeled.  No data correction is needed or authorized; the source definition is
the binding constraint.
**Rationale:** The absence is a verified definitional exclusion, not a missing
file, a mapping error, or an economic zero.  Imputing or re-coding KZ would
introduce unverifiable assumptions.
**Limitations:** If Banco de Portugal ever releases a compatible enterprise-birth
series for section K, the exclusion could be revisited.
**Affected files:** `data/external/portugal/raw/ine/0009703_*.json`;
`data/external/portugal/processed/portugal_qtensor_births_cae_nuts3.csv`;
`src/data/european_panel/adapters/pt_adapter.py`.

---

## DEC-019 — 2026-06-10 — G1-L2 same-sector co-growth graph passes validation

**Phase:** G1
**Question:** Does rolling same-sector cross-territory co-growth produce a
reproducible graph structure in at least two of FR/NL/PT?
**Evidence:** Builder `src/data/european_panel/build_g1_l2_cogrowth.py` with
rolling window w=5, min_periods=4, 199 temporal permutations, 199 territory
permutations, BH FDR q=0.05, LOYO direction test, bootstrap stability at 70%
threshold (seed=42).  Results:

| Country | Sectors | Eval years | Stability | Temporal q | Territory q | LOYO | Stable edges |
|---|---|---|---:|---:|---:|---|---:|
| FR | 9 | 2017–2026 | 0.7824 | 0.0050 | 0.0050 | True | 13 |
| NL | 9 | 2012–2026 | 0.7893 | 0.0050 | 0.0050 | True | 19 |
| PT | 8 | 2013–2025 | 0.7778 | 0.0050 | 0.0050 | True | 22 |

COVID sensitivity (2020 excluded from window observation years; eval_year=2020
retained): all three still pass full gate (temporal q=0.005, territory q=0.005,
LOYO, stable edges > 0).  Classification: COVID_ROBUST (DEC-020).
Stability with exclusion: FR 0.7440, NL 0.7622, PT 0.7379.  3/2 required.
**Decision:** L2 PASS.  The co-growth graph is promoted as an analytically
validated layer. Correlation edges are statistical co-movement associations,
not Granger predictability or structural economic causality. This result does
not authorize GNN training,
forecast combination or recommendation.
**Rationale:** All three countries independently beat both null models after FDR
correction and LOYO direction stability.  The result is COVID-robust.
**Limitations:** Pearson rolling correlation conflates co-movement with shared
trends.  MAUP applies (NUTS3/ZE/COROP boundaries are administrative).  PT
participates with 8 sectors (KZ excluded per DEC-018).
**Affected files:** `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`;
`src/data/european_panel/build_g1_l2_cogrowth.py`;
`data/processed/economic_graph/g1_l2_cogrowth/`.

---

## DEC-020 — 2026-06-10 — COVID sensitivity correction: eval_year exclusion bug fixed

**Phase:** G1 audit / Part A
**Question:** Was the COVID sensitivity analysis in the original L2 builder
correctly excluding only window observation data, or was it also
removing `eval_year=2020` from evaluation?
**Evidence:** Code audit of `build_g1_l2_cogrowth.py` (commit `ebb2979`):
(1) `eval_yrs = [t for t in eval_yrs if t not in exclude_years]` incorrectly
removed `eval_year=2020` from the evaluation set, even though its window covers
`[2015..2019]` which contains no COVID data.
(2) `bootstrap_edge_stability` called `window_matrix` without propagating
`exclude_years`, so bootstrap windows could silently include 2020.
(3) The COVID sensitivity gate omitted the `stable_edge_count > 0` check,
making the COVID gate strictly weaker than the main gate.
**Alternatives considered:** Accept original result as conservative (removing
2020 from eval_years is a stricter test). Rejected: the intent is to exclude
2020 from window DATA, not from the evaluation itself.
**Decision:** (1) Remove the eval_year filter; `eval_year=2020`'s window
covers pre-COVID years and is retained. (2) Propagate `exclude_years` to
`bootstrap_edge_stability`. (3) Apply the full 4-criterion gate (temporal q,
territory q, LOYO, bootstrap stable edges) to the COVID sensitivity run as well.
(4) Report explicit window gaps (list of excluded years per window) in output.
(5) Classify result as `COVID_ROBUST` if the full gate passes with 2020 excluded,
`COVID_SENSITIVE` otherwise.
**Rationale:** Removing eval_year=2020 was unnecessary and discarded a valid
evaluation point. Bootstrap windows were inconsistent with the declared protocol.
Gate asymmetry between main and COVID runs was an undeclared relaxation.
**Limitations:** The corrected result uses a slightly different eval_year set
than the original run; re-run results may differ numerically.
**Reopen condition:** If MIN_PERIODS < 4, some windows excluding 2020 would
have too few observations; review if window length changes.
**Affected files:** `src/data/european_panel/build_g1_l2_cogrowth.py`;
`tests/test_g1_l2_cogrowth.py`; `reports/HERALD_G1_L2_CAUSAL_COGROWTH_AUDIT.md`.

---

## DEC-021 — 2026-06-10 — G1 community detection baseline authorized on validated L2 layer

**Phase:** G1 / task 2.8
**Question:** What community structure does the validated L2 co-growth graph
exhibit, and is it more structured than temporally or territorially permuted nulls?
**Evidence:** L2 PASS (DEC-019) provides a validated co-growth edge set per
(country, eval_year, sector). Louvain algorithm available via NetworkX 3.4.2
(no external dependency required). Positive correlations only (negative
co-growth ≠ community membership). Per-country analysis; no cross-country pooling.
**Decision:** Build Louvain community baseline on a fixed symmetric top-k=5 L2
graph. Metrics: modularity, AMI between consecutive years, edge
appearance/disappearance, community count and size. Null models rebuild L2
from temporally and territorially permuted growth series. Node relabeling is
not a valid modularity null. COVID sensitivity removes observation year 2020
from windows while retaining evaluation year 2020.
**Rationale:** G0 contract item 8 requires community stability metrics. Louvain
is the standard method; NetworkX implementation avoids new dependencies. Results
are analytical observations, not economic claims.
**Limitations:** Louvain is stochastic; one fixed-seed run is applied equally
to observed and null graphs. Community membership is a statistical co-growth
cluster, not an economic production district or industrial cluster. Results
cannot be used as policy input.
**Reopen condition:** If igraph or leidenalg become available, repeat with Leiden
for comparison; results should agree in direction.
**Affected files:** `src/data/european_panel/build_g1_communities.py`;
`tests/test_g1_communities.py`; `reports/HERALD_G1_COMMUNITIES_AUDIT.md`;
`data/processed/economic_graph/g1_communities/`.
**Result (corrected 2026-06-10):** FAIL 0/3 after applying valid nulls, equal
Louvain budget, top-k sparsification and FDR to both modularity and AMI. FR
modularity q=(0.54, 0.42); NL=(1.0, 1.0); PT=(0.587, 0.072). Some AMI tests
are positive, especially PT, but no country passes all four criteria. COVID
sensitivity also fails 0/3. G-11 is NOT_SUPPORTED under this protocol. L2 edge
stability remains supported; only the community claim is rejected.

---

## DEC-022 — 2026-06-10 — Phase 5 HPC architecture drafted; training blocked

**Phase:** Pre-Phase 5
**Question:** What architecture and comparison protocol should the next HPC
battery use for the residual neural corrector experiment?
**Evidence:** Phase 4N established persistence (0.0939) as best LOCO baseline.
L3 and L2 are validated observable graph layers. The geographic spatial branch
(Phase 4P/4Q) is closed (FAIL). The next logical step is testing whether
validated graph layers provide out-of-sample forecast improvement when combined
with a low-capacity residual corrector.
**Decision:** Keep the corrected H0-H5 specification as a draft in
`reports/HERALD_PHASE5_HPC_SPEC.md`. Architecture:
`y_hat = y_hat_baseline + alpha * residual_neural(G)`. Gate: ≥1% WMAPE
improvement vs persistence and Ridge, graph-control p ≤ 0.05, no per-country
regression, both temporal and territory permutation controls. H5 (learned
graph) only if H2 or H4 pass. The failed community hypothesis does not
invalidate the validated L2 edges: community separability and predictive
utility are distinct hypotheses. Training remains blocked only until the
sector-specific L2 pooling implementation is tested locally, exact L2
artifacts are frozen, the supervisor deadline is confirmed and the smoke test
passes. Community labels must not enter the model.
**Rationale:** A draft specification prevents parameter selection after seeing
forecast results while allowing correction of invalid upstream assumptions.
The gate is strict enough to reject a graph that merely matches the null.
**Limitations:** Alpha regularization design is not yet validated; implementation
may require adjustment during smoke test.
**Reopen condition:** If H2/H4 fail the gate, close Phase 5 graph branch and
return to non-graph frugal improvements (Bloco 1).
**Affected files:** `reports/HERALD_PHASE5_HPC_SPEC.md`.

**Update 2026-06-10 — Smoke test v2 (NL, eval_years=[2021,2022,2023], seeds=[42,43,44]):**
Corrected naming: H1/H2 are now "linear" (Ridge). Added H1-neural/H2-neural (sklearn MLP,
hidden=(16,8), 9D per-sector features + 2 AR lags, alpha_scale ∈ [0,1]). PC controls
fixed (inline matrix permutation, not dict-based). 65/65 tests pass.

Results (mean over 3 seeds):

| Hypothesis          | Mean WMAPE |
|---------------------|-----------|
| H0 (persistence)    | 6.96%     |
| H0b (Ridge AR)      | **3.41%** |
| H1-linear           | 5.52%     |
| H2-linear           | 5.56%     |
| PC-temporal-linear  | 5.52%     |
| PC-territory-linear | 5.49%     |
| H1-neural           | 5.80%     |
| H2-neural           | 8.79%     |
| PC-temporal-neural  | 9.81%     |
| PC-territory-neural | 9.33%     |

Neural gate criteria:
- Graph specificity (H2-neural ≠ H1-neural): ✓ PASS (diff=3.0%)
- H2-neural beats PC-temporal-neural: ✓ PASS (gain +1.0%)
- H2-neural beats PC-territory-neural: ✗ FAIL (gain +0.53% < 1% threshold)
- H2-neural no regression >10% vs H0b: ✗ FAIL (H2=8.79% >> H0b*1.1=3.75%)

**Conclusion: HPC_BLOCKED.** Neural corrector regresses substantially vs H0b.
H2-neural (8.79%) is worse than H0 (6.96%). This likely reflects overfitting on
small rolling-origin windows — 9D input with (16,8) MLP on ~360 samples (10yr × 36
valid regions).

What this does NOT mean: L2 co-growth layer is not validated. H2-linear shows graph
propagation changes features meaningfully but capacity is insufficient to exploit them.

Mitigations before reopening: (a) reduce MLP capacity to (8,) or (4,); (b) increase
L2 regularisation (mlp_alpha=0.1); (c) longer eval window with more training data;
(d) consider FR/PT where data ranges differ. Not to be pursued without supervisor
confirmation of scope and deadline.

---

## DEC-023 — 2026-06-10 — Phase 5 graph corrector: NOT_SUPPORTED

**Phase:** Phase 5 ablation v3
**Question:** Do smaller MLP widths and corrected training set construction change
the NOT_SUPPORTED verdict for the graph residual corrector?
**Evidence:**
Root causes fixed before ablation:
1. `message_pass_1hop` returned NaN for all regions when sector had zero edges
   (OQ sector, NL, t=2012-2019). Fix: self-value fallback when no valid neighbours.
   NaN only if x[r] is itself NaN (genuine data absence).
2. `predict_neural_corrector` used `np.isfinite(row).all()` requiring all 11 features
   to be finite; OQ growth data missing for 2011-2016 dropped entire training years.
   Fix: collect all region-years with finite residuals; impute NaN feature columns with
   column-mean from training data (training-only, no leakage). n_train: 39 → 440
   for eval_year=2021.
3. Test semantics updated: zero-edge adj → self-value (not NaN). 65/65 tests pass.

Ablation (NL, eval_years=[2021,2022,2023], 5 seeds, widths (2,)(4,)(8,)(16,8)):

| Hypothesis | (2,) | (4,) | (8,) | (16,8) |
|---|---|---|---|---|
| H0b (Ridge AR baseline) | 3.41% | 3.41% | 3.41% | 3.41% |
| H1-neural (no graph) | 5.67% | 5.22% | 5.14% | 5.30% |
| H2-neural (L2 graph) | 5.87% | 5.64% | 5.53% | 5.57% |
| PC-temporal-neural | 6.25% | 6.08% | 6.34% | 6.26% |
| PC-territory-neural | 6.41% | 6.13% | 5.94% | 6.63% |

Best width=(8,): H2-neural=5.53%, H0b×1.1=3.75%. Gate status:
- H2 ≠ H1 (0.39%): ✓ graph specificity confirmed
- H2 < PC-temporal (6.34%): ✓
- H2 < PC-territory (5.94%): ✓
- H2 < H1-neural: ✗ (H2=5.53% > H1=5.14% — H2 WORSE, graph adds noise)
- H2 ≤ H0b×1.1=3.75%: ✗ (5.53% — 62% regression vs H0b)

Linear correctors also fail: H2-linear=5.56% vs H0b=3.41%.

**Decision: Phase 5 graph corrector branch CLOSED — NOT_SUPPORTED.**
No capacity variant passes all gate criteria. The L2 co-growth graph encodes
statistically significant co-movement signal (beats permuted controls) but this
signal does not improve out-of-sample WMAPE over the AR-Ridge baseline. The residual
corrector architecture fails regardless of whether the graph is linear or neural.

**What this means:**
- L2 graph validation (DEC-019/020, G-10 SUPPORTED) stands. The graph exists and is
  statistically non-trivial.
- The forecasting claim is different: graph-augmented corrector does NOT improve
  territorial forecasting over H0b Ridge for NL 2021-2023.
- H0b (AR-Ridge) remains the best local baseline.

**What this does NOT mean:**
- L2 graph is useless for all purposes (Bloco 2 stands: graph representation,
  evolution tracking, dynamics description — separate from forecast utility).
- Results cannot be extrapolated to FR/PT without running those experiments.

**Reopen condition:** Closed. Phase 5 graph corrector experiment terminated.
Only reopen if: (1) substantially different architecture (e.g. global AR-graph
interaction, not residual correction), OR (2) new harmonized multi-country panel
with longer windows, OR (3) supervisor directive with explicit justification.

**Affected files:** `reports/HERALD_PHASE5_HPC_SPEC.md`, `CODEX_MEMORY.md`,
`src/modeles/phase5/neural_corrector.py`, `src/modeles/phase5/l2_pool.py`.
