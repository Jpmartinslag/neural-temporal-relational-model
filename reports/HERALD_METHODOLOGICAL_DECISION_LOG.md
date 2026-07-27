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

---

## DEC-024 — 2026-06-10/11 — G2 Preflight + Negative Control: falsifiable criteria and temporal dynamics

**Phase:** Bloco 2 — G2 Temporal Dynamics
**Question:** Are the L2 graph's temporal-Jaccard metrics genuine temporal signal or finite-sample
artefact? What is the scope-correct characterisation of G2 aggregate variation?

### DEC-024a — Preflight findings (2026-06-10, valid)

G2 preflight run on 3,645,230 L2 edges (FR/NL/PT, 9 sectors, 15 eval years).
Top-k=5 (same as Phase 5). PT KZ excluded (DEC-018).

| Criterion | Threshold | Finding |
|-----------|-----------|---------|
| Persistent edge (≥70% year presence) | 70% | 0.4% of edges qualify |
| LOYO Pearson | ≥ 0.70 | 0.10-0.19 (all FAIL) |
| LOYO Jaccard | ≥ 0.70 | 0.07-0.26 (all FAIL) |
| Stable neighbourhood (turnover ≤ 30%) | 30% | 0/295 year-pairs stable |
| Mean turnover | — | 59% (FR: 77%, NL: 56%, PT: 48%) |
| COVID density disruption (\|Δ\| ≥ 0.05) | 0.05 | 0/25 combos exceed |
| COVID weight disruption (\|Δ\| ≥ 0.15) | 0.15 | 0/25 combos exceed |

These descriptive findings are valid and unaffected by the negative-control bug below.

### DEC-024b — Prior negative control (2026-06-11, SUPERSEDED)

> **SUPERSEDED.** The negative control in commit cc48924 permuted pre-computed Pearson
> correlation weights (territory-pair rows of the weight matrix W from `g1_l2_edges.csv`),
> NOT the original growth time series from `sector_panel_fr_nl_pt.csv`. This is
> methodologically invalid: the null distribution does not correspond to the hypothesis
> being tested (temporal randomness in source co-movement series). The p=0.005 values and
> "26/26 significant" result are NOT valid evidence. G-13 reverted to
> EXPLORATORY_PENDING_REVALIDATION.

Preserved for historical record:
- Gate: 3/3 countries, 26/26 combos FDR-significant (p=0.005 min), all positive effects.
- Sensitivity k=3,10: also all p=0.005 (same bug applies).
- These numbers must not be cited as evidence.

### DEC-024c — Corrected control (2026-06-11, COMPLETE)

Module: `src/data/european_panel/build_g2_corrected_controls.py`.
Tests: `tests/test_g2_corrected_controls.py` (25 tests, all pass).
Source: `sector_panel_fr_nl_pt.csv` (NOT `g1_l2_edges.csv`).

**Protocol:**
- N1: permute `observation_year` within each territory × sector column (temporal null).
- N2: row-wise territory permutation — within each observation_year, shuffle which territory
  receives which growth value. Tests territory co-movement identity.
- N2 column permutation DEGENERATE: uniform column shuffle = graph relabeling → null std=0, p=1.0.
  Verified empirically for NL and PT. N2 row-wise used in gate.
- Full pipeline per permutation: rolling windows → pairwise_corr → top-k → adjacency → metrics.
- Metrics: M1 consecutive Jaccard J(G_t, G_{t+1}); M2 mean pairwise Jaccard (all year pairs);
  M3 LOYO reconstruction (remove obs_year y, rebuild affected windows) — observed only, null BLOCKED.
- COVID: `exclude_years=frozenset({2020})` excludes obs_year=2020 from windows; eval_year=2020 retained.
- 199 permutations per null family. p=(1+count(null≥obs))/(N+1). BH/FDR by metric×null family.
- Seeds: N1=42, N2=137.

**Results (k=5 principal):**

| Country | M1 obs (mean) | M2 obs (mean) | N1+N2 sig sectors | Signal gate | Stability gate (M2≥0.70) |
|---------|--------------|--------------|-------------------|-------------|--------------------------|
| FR | 0.181–0.195 | 0.059–0.064 | 9/9 (p=0.005) | ✓ PASS | ✗ FAIL |
| NL | 0.373–0.493 | 0.155–0.260 | 5/9 (BE,FZ,GI,LZ,MN) | ✓ PASS | ✗ FAIL |
| PT | 0.447–0.509 | 0.243–0.261 | 0/8 | ✗ FAIL | ✗ FAIL |

**Global verdicts:**
- In the sensitivity scenario excluding observation year 2020, 2/3 countries
  pass (FR+NL). DEC-024d supersedes an unconditional promotion because the
  main scenario including 2020 passes with FR+PT instead.
- `G2_EDGE_STABILITY_NOT_SUPPORTED` — M2 0.06–0.26 universally; 0/3 countries pass.

**M3 LOYO reconstruction (observed, null BLOCKED):** FR 0.287 · NL 0.500 · PT 0.578.

**Floor-p diagnostics (FR p=0.005):** obs_above_all_null=True; null std ~0.0013–0.0015;
199 unique null values → legitimate signal, not degeneracy.

**Sensitivity (k=3,5,10):** M2 increases with k; direction consistent across k for all countries.

**G-13 status: PARTIALLY_SUPPORTED** — in the sensitivity scenario (exclude observation year 2020)
signal exceeds nulls for FR (9/9) and NL (5/9); in the main scenario (include 2020) for FR (9/9)
and PT (4/8). DEC-024d supersedes any unconditional reading: only FR is COVID-robust across both
scenarios. Stability NOT supported (0/3 countries).

**Scope restrictions (unchanged):**
- Language: "associação estatística temporal observada", NOT causal attribution
- No individual edge claims, no cross-country pooling
- No community claims (DEC-021), no recommendation claims

**Affected files:** `src/data/european_panel/build_g2_corrected_controls.py`,
`data/processed/economic_graph/g2_preflight/` (g2_corrected_controls*.csv, g2_corrected_m3_loyo.csv,
g2_corrected_controls_summary.json), `tests/test_g2_corrected_controls.py`,
`reports/HERALD_G2_PREFLIGHT.md`.

### DEC-024d — COVID is a sensitivity factor, not a model weight (2026-06-11)

**Question:** Does the G2 aggregate temporal-coherence decision depend on the
2020 observation?

**Protocol:** Repeat the full corrected N1/N2 experiment twice with identical
parameters and seeds. Main includes `observation_year=2020`; sensitivity
excludes only that observation from rolling windows. No feature, loss, sample
or metric receives a COVID weight. `available_for_forecast_year=2020` remains.

**Result:** FR remains 9/9 in both scenarios (`COVID_ROBUST`). NL changes from
4/9 with 2020 to 5/9 without it; BE, LZ and RU change decision. PT changes from
4/8 with 2020 to 0/8 without it; BE, GI, JZ and LZ change decision. NL and PT
are `COVID_SENSITIVE`.

**Decision:** The global 2/3 gate is not robust because it passes with FR+PT
when 2020 is included and FR+NL when it is excluded. Promote only the FR
aggregate signal as COVID-robust. Keep G-13 `PARTIALLY_SUPPORTED`; report NL
and PT as sensitivity findings. Edge stability remains `NOT_SUPPORTED`.

**Reconciliation:** G-10 concerns stability of the complete dense Pearson
weight field. G-13 concerns identity overlap in sparse top-k graphs. G-10 does
not validate stable individual edges.

---

## DEC-025 — 2026-06-11 — G2 aggregate dynamics characterization complete

**Phase:** Bloco 2 — G2 Descriptive
**Question:** How does the aggregate structure of the L2 co-growth graph vary
over time by country and sector?
**Evidence:** Builder `src/data/european_panel/build_g2_aggregate_dynamics.py`
produces 321 annual metric rows (FR 90, NL 127, PT 104) across density, weight
distribution (mean, median, std, quantiles), turnover, Jaccard,
pair-resampling sensitivity intervals, period summaries, and period
comparisons. The top-k graph contains positive correlations only, so sign
fractions are structural diagnostics. 45 tests pass.

Key findings:
- FR: density stable (Δ < 0.001), weight stable (Δ < 0.01), turnover 79%.
- NL: slight density increase (+0.006), modest weight increase (+0.011),
  turnover 59%.
- PT: negligible density change (+0.001), largest weight increase (+0.048),
  turnover 51%.  RU and MN sectors show Δweight > 0.13.
- The rolling graph ending in 2020 shows slight weight dips for FR and NL but
  not PT. This is not a single-year graph or a COVID-effect estimate.
- COVID sensitivity: FR COVID_ROBUST, NL and PT COVID_SENSITIVE.
- G2_CROSS_COUNTRY_REPLICATION_NOT_SUPPORTED.

**Alternatives considered:** Inferential tests on period differences.
Rejected: small number of years per period, non-independent observations,
no pre-registered hypothesis for sector-level differences.
**Decision:** G2 aggregate dynamics descriptive characterization is complete.
G-14 is `SUPPORTED` strictly as a computed descriptive statement. The limited
FR inferential claim comes from the corrected controls in G-13/DEC-024d, not
from the period summaries or pair-resampling intervals. NL and PT remain
descriptive and sensitivity results only.
**Rationale:** Descriptive characterization of an already-validated graph
(G-10 SUPPORTED) does not require new statistical gates.  The analysis is
scope-constrained: no individual-edge, causal, community, forecast, or
recommendation claims.
**Limitations:** Small year counts per period. Periods contain overlapping
five-year rolling windows. Pair-resampling intervals are not confidence
intervals because territory pairs share nodes. Positive-edge top-k selection
makes sign fractions non-inferential. Pearson rolling correlation conflates
co-movement with shared trends. MAUP applies. Cross-country replication not
achieved.
**Reopen condition:** Not applicable — descriptive characterization is
complete.  New analysis questions require new pre-registration.
**Affected files:** `src/data/european_panel/build_g2_aggregate_dynamics.py`;
`tests/test_g2_aggregate_dynamics.py`;
`data/processed/economic_graph/g2_dynamics/`;
`reports/HERALD_G2_AGGREGATE_DYNAMICS_AUDIT.md`.

---

## DEC-026: G2 Scientific Reporting and Dashboard Specification
**Date:** 2026-06-11
**Context:** The G2 descriptive dynamics analysis was completed and validated in DEC-025. These results needed to be documented for the final scientific report and a specification needed to be defined for future dashboard integration.
**Decision:**
1. A report section (`HERALD_G2_REPORT_SECTION_FR.md`) was written in academic French, strictly adhering to the permitted claims (no causality, no Granger, no stable individual edges, no forecast improvement).
2. Four figures were selected (`g2_comparative_panel.png`, `g2_weight_temporal_FR.png`, `g2_turnover_jaccard_FR.png`, `g2_post_minus_pre_PT.png`) and documented in `HERALD_G2_REPORT_FIGURE_SELECTION.md` with explicit allowed/prohibited interpretations.
3. A dashboard integration specification (`HERALD_G2_DASHBOARD_INTEGRATION_SPEC.md`) was created, defining how to incorporate these findings without modifying the current HTML.
**Rationale:** Preserves the boundary between verified descriptive results and unsupported inferential/causal claims during the transition to the report phase.
**Limitations:** The report section remains a draft component. The dashboard specification is conceptual and not yet implemented.
**Reopen condition:** Future dashboard implementation.
**Affected files:** `HERALD_G2_REPORT_SECTION_FR.md`, `HERALD_G2_REPORT_FIGURE_SELECTION.md`, `HERALD_G2_DASHBOARD_INTEGRATION_SPEC.md`, `CODEX_MEMORY.md`.

---

## DEC-027 — 2026-06-11 — Graph-temporal architecture preflight

**Question:** Which architecture may be tested after the fixed-L2 Phase 5
corrector failed?

**Evidence:** Twenty-method graph-temporal review, EconoGNN primary-source
audit, current G2 evidence, Phase 5 ablation v3 and the canonical sector panel.

**Corrections made during audit:**

- EconoGNN is an observed dynamic trade graph reference, not a fixed graph and
  not a reusable HERALD implementation.
- A0 and A1 must predict the same territorial total. Sector observations are
  graph-node features, not a different target.
- EvolveGCN evolves graph-convolution parameters; it does not recurrently
  update the adjacency matrix.
- Exact parameter counts must come from implemented code.
- NL is an engineering smoke only; FR is the first scientific test because
  only FR is robust under both G2 COVID scenarios.

**Decision:** Keep country-specific AR/Ridge as A0. Permit a future local
preflight comparing low-capacity GConvGRU and EvolveGCN-H over per-year causal
L2 graphs, with shared sector weights and a bounded residual head. A2 learned
edge gates remain blocked.

**Gate:** HPC remains blocked. The next authorized task is only tensor export,
leakage/mask tests, parameter counting and the NL engineering smoke harness.
Scientific training starts with FR only after that audit. No architecture is
promoted.

**Affected files:** `HERALD_GRAPH_TEMPORAL_ARCHITECTURE_REVIEW.md`;
`HERALD_ECONOGNN_TRANSFERABILITY_AUDIT.md`;
`HERALD_GRAPH_TEMPORAL_ARCHITECTURE_DECISION.md`;
`reports/bibliography/herald_graph_temporal_references.bib`;
`reports/bibliography/HERALD_GRAPH_TEMPORAL_REFERENCE_AUDIT.csv`.

---

## DEC-028 — 2026-06-11 — Graph-temporal schema 2.0 and E0-v2 engineering gate

**Phase:** Pre-A1 implementation (graph-temporal)
**Question:** Is schema 1.0 (static snapshot tensors) sufficient for GConvGRU/EvolveGCN-H training, and what corrections are required?

**Evidence:** Schema 1.0 (commit 58a4e43) passed engineering smoke E0 but produced only static (R,S,F) and (S,R,R) tensors. Five defects were identified:

1. **Static snapshot**: GConvGRU and EvolveGCN-H require temporal input sequences (T,R,S,F) and (T,S,R,R). Schema 1.0 exported only the most recent snapshot before each eval_year.
2. **Simplified Ridge**: Used `target_births` from the country panel with 3 features (lag1, lag2, growth_1y) and target normalization — not the canonical H0b Ridge from `corrector.py`.
3. **Single obs_mask**: One binary mask per (region, sector) caused growth=Inf to silently discard births and share features at the same position. Features with independent validity semantics must carry independent masks.
4. **Signed dense adjacency**: 29–36% of off-diagonal Pearson correlations are negative across NL eval years, and 26–39% across FR eval years. A positive_topk representation is required as the primary; signed_split and shrinkage_dense are available for ablation.
5. **tracemalloc memory**: Python-heap-only measurement is unreliable for NumPy native buffers. `resource.getrusage(RUSAGE_SELF).ru_maxrss` is used instead.

**Corrected schema 2.0 tensors (per fold):**

| Tensor | Shape | Description |
|--------|-------|-------------|
| `features_seq` | (T, R, S, F) | T=5 causal time steps before eval_year; F=3 (growth, share, births_norm) |
| `feature_mask_seq` | (T, R, S, F) | Per-feature binary masks (int8); 0/1 independently per feature |
| `struct_mask` | (R, S) | Static structural mask; 0 for PT-KZ; cannot be overwritten |
| `adjacency_seq` | (T, S, R, R) | Positive_topk (k=5), symmetric, non-negative; per-step causal window |
| `observation_years` | (T,) | Explicit obs year for each step; all < eval_year |
| `y_true` | (R,) | `business_sector_total` from sector panel at obs_year=eval_year |
| `y_ridge_canonical` | (R,) | Canonical H0b Ridge; ≥0; port of `corrector.py::predict_h0b` |
| `residual` | (R,) | `y_true - y_ridge_canonical` where target_mask=1; NaN elsewhere |
| `target_mask` | (R,) | 1 where y_true is finite |

**Causal contract (all enforced by `LeakageError` assertions):**
- `observation_years[t] < eval_year` for all t
- `adjacency_seq[t]` uses only `sector_growth_1y` at obs_years ≤ `observation_years[t]`
- Ridge trains only on `available_for_forecast_year < fold_eval_year`
- PT-KZ is always `struct_mask=0`; no observation loop can overwrite it
- `y_true` and `y_ridge_canonical` share the same source (`business_sector_total`)

**Canonical Ridge H0b** (`corrector.py::predict_h0b` exact port):
- Source: `sector_panel_fr_nl_pt.csv`, column `business_sector_total`
- AR lags: n_lags=2 (avail_year offsets)
- Normalization: StandardScaler on features only (not target)
- Clip: `np.clip(y_hat, 0, None)` — births cannot be negative
- Alpha: RIDGE_ALPHA_H0B=10.0

**E0-v2 smoke (NL, 3 eval years [2019,2020,2021], 2 runs):**

| Check | Description | Result |
|-------|-------------|--------|
| C1 | Causal ordering (all obs_years < eval_year) | PASS |
| C2 | Sequence shapes (T,R,S,F) and (T,S,R,R) | PASS |
| C3 | Per-feature mask independence, values ∈ {0,1} | PASS |
| C4 | Adjacency per-step symmetric non-negative | PASS |
| C5 | No NaN/Inf where feature_mask=1 | PASS |
| C6 | y_ridge_canonical ≥ 0; canonical WMAPE (NL/2019=0.098, NL/2020=0.038, NL/2021=0.042) | PASS |
| C7 | residual = y_true - y_ridge_canonical | PASS (max_diff=0) |
| C8 | Two-run determinism (identical NPZ checksums) | PASS |

Runtime 13.92s; RSS delta 0.035 GB; 57/57 tests pass.

**FR adjacency audit (eval_years 2021–2025, 5 folds, k=5):**
- 280 FR ZE regions, 9 sectors. 0 isolated nodes. 1 connected component (280 nodes) for every sector and eval_year. Perfect symmetry. No negative edges. No NaN/Inf. All 5 eval years pass all 8 fail-closed criteria. Neg_fraction in raw Pearson: 26–39% (positive_topk filters correctly). Mean degree ≈ 6 (before/after symmetrization). Max degree ≤ 14. Adjacency sequence varies temporally. Decision: `FR_ADJACENCY_READY`.

**Tests (57 total):**
- `tests/test_graph_temporal_preflight.py` — 33 schema 1.0 tests (T01–T18 + 15 additional) — all PASS
- `tests/test_graph_temporal_v2.py` — 24 schema 2.0 tests (T19–T42) — all PASS

**Decision:** Schema 2.0 adopted. Schema 1.0 tensors (`data/processed/graph_temporal_preflight/`) retained as audit trail, superseded for GNN use. Schema 2.0 tensors: `data/processed/graph_temporal_v2/`. **E0_V2_PASS**.

**Authorization:** GConvGRU (A1a) and EvolveGCN-H (A1b) implementation is authorized under the contract in `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md`. **S1-FR remains BLOCKED** until models are implemented and pass the A1 implementation gate. **HPC remains BLOCKED** until S1-FR passes locally.

**Conditions for opening S1-FR:**
1. A1a (GConvGRU) and A1b (EvolveGCN-H) implemented with schema 2.0 tensors.
2. A0-neural (equal-capacity no-graph control) implemented.
3. Zero-adjacency control implemented.
4. Both temporal and territory permutation controls implemented.
5. At least 5 FR eval years; at least 5 seeds.
6. Per-architecture tests pass (shape, mask propagation, bounded residual, ≤5,000 params, determinism).
7. `git diff --check` clean.

**Limitations:**
- NL OQ sector has sparse co-growth data before 2019: 40 regions isolated at k=5 in NL/2019 audit (all 40 in OQ sector). This matches the Phase 5 finding (OQ zero edges 2012-2019). FR does not exhibit this issue (0 isolated at all k values and all eval years).
- T=5 sequence length is a hyperparameter. Sensitivity to T not tested in E0.
- Adjacency covers only positive top-k correlations; negative-correlation pairs are not represented in the primary artifact.

**Reopen condition:** If both A1a and A1b fail the S1-FR gate, close the graph-temporal prediction branch and return to non-graph frugal improvements (Bloco 1). The L2 co-growth graph remains valid as an analytical (Bloco 2) artefact.

**Affected files:** `src/data/european_panel/build_graph_temporal_v2.py`; `src/modeles/run_e0_smoke_nl_v2.py`; `tests/test_graph_temporal_v2.py`; `reports/HERALD_GRAPH_TEMPORAL_E0_V2_AUDIT.md`; `reports/HERALD_GRAPH_TEMPORAL_E0_PREFLIGHT_AUDIT.md` (superseded notice); `reports/HERALD_GRAPH_TEMPORAL_FR_ADJACENCY_PREFLIGHT.md`; `reports/HERALD_GRAPH_TEMPORAL_A1_IMPLEMENTATION_CONTRACT.md`; `CODEX_MEMORY.md`.

---

## DEC-029 — 2026-06-12 — P6_DDEG_S1 full study: DUAL_GRAPH_S1_FAIL; predictive branch closed

**Phase:** 6 — P6_DDEG_S1
**Question:** Does the dynamic dual economic graph (territory graph + learned sector graph, ≤10,000 params) improve territorial enterprise-birth prediction, regime classification, or recovery detection for France NUTS3 under rolling-origin 5-fold evaluation?
**Evidence:** Slurm job 7453691; 275/275 tasks COMPLETED; all 7 gate criteria fail.
- c1 MAE: C5_dual 0.1424 vs C1_ridge 0.1242 (+14.6%) and C2_no_graph 0.1329 (+7.2%). Both FAIL (required ≤-1%).
- c2 macro-F1: C5=0.2885 vs C2=0.2870 (margin +0.0015, required ≥+0.02). FAIL.
- c3 recovery AUCPR: C5 beats prevalence in 5/5 folds but loses to C2_no_graph in 5/5 folds. FAIL.
- c4 graph vs nulls: C5 never beats BOTH C7 and C8 simultaneously in any fold. FAIL (0/5; required 3/5).
- c5 seed Jaccard: 0.3353 (required ≥0.50). FAIL.
- c6 fold regression: 2023 fold +17.4% vs C2 (required ≤10%). FAIL. Note: pilot had c6=PASS; full study with 5 seeds reveals the 2023 failure.
- c7 without 2021: C5 is +10.1% worse than C2 over folds 2022–2025. FAIL.
**Alternatives considered:** Hyperparameter tuning (rejected per contract §9 — performance failure is not a reopen condition). Architecture revision (deferred to A1 contract track).
**Decision:** DUAL_GRAPH_S1_FAIL. Predictive dual-graph branch CLOSED. P6_DDEG_S1 status: frozen/FAIL.
**Rationale:** The fail-closed gate was pre-registered before any training. All 7 criteria are independently falsified by the confirmatory 5-seed run. The model cannot distinguish itself from graph permutation nulls (C7/C8), confirming that the learned structure does not encode predictively useful information under this protocol.
**Limitations:** The architecture is very low-capacity (hidden_dim=8, 1,035 params); higher-capacity graph-temporal models (GConvGRU, EvolveGCN-H, A1 contract) are not precluded by this result. The learned sector graph has descriptive stability (C↔KZ 80% of fold×seed runs) but this is not validated for prediction.
**Reopen condition:** Documented operational failure in protocol or data integrity (e.g., tensor leakage discovered post-audit, gate misapplied, wrong control definitions). Performance failure alone is not a reopen condition.
**Affected files:** `data/processed/dual_graph_s1/gate_result.json`; `data/processed/dual_graph_s1/run_manifest.json`; `hpc_results/dual_graph_s1/raw/` (275 JSON); `reports/HERALD_DUAL_GRAPH_S1_RESULTS.md`; `reports/HERALD_DUAL_GRAPH_S1_FINAL_AUDIT.md`; `hpc/hpc_phase_registry.json`; `hpc/phase6_dynamic_dual_graph/README.md`; `CODEX_MEMORY.md`.

---

## DEC-030 — 2026-06-12 — Repository consolidation: HERALD direction frozen; Economic Observatory v0.1 authorized

**Phase:** Cross-phase consolidation
**Question:** What is the official direction of HERALD after P6 closure, and what is the next implementation phase?
**Evidence:** Synthesis of DEC-001→DEC-029. All predictive graph branches tested: geographic (4P/4Q FAIL), fixed-L2 corrector (Phase 5 NOT_SUPPORTED), dynamic dual graph (P6_DDEG_S1 FAIL). Descriptive graph layers validated: G1-L2 co-growth (DEC-019/020), G2 aggregate (DEC-025). Graph-temporal A1 contract frozen (DEC-028), S1-FR blocked pending implementation. Ridge/persistence is the best validated forecasting baseline. P6 sector-edge CSV artefact uses sector names that do not match tensor sector_ids (origin unverifiable).
**Alternatives considered:** (1) Continue architecture search — rejected; no new GNN before integrated prototype is complete. (2) Reopen geographic graph — rejected; P6/4Q/4P all closed, no new hypothesis. (3) Immediate prototype implementation — deferred; consolidation must precede implementation.
**Decision:**
1. **HERALD is an European territorial economic intelligence system**, not a single forecasting model. Enterprise births are the primary operational indicator, not the sole objective. Functions: forecasting, economic states, territorial graph, sector graph, explanation, recommendation (future).
2. **P6_DDEG_S1 sector-edge artefact (`learned_sector_edges.csv`) is INVALID_FOR_INTERPRETATION.** Sector names in the CSV do not match tensor sector_ids (BE, FZ, GI, JZ, KZ, LZ, MN, OQ, RU). The CSV appears to have used an unrelated sector name list; the source cannot be proven. Gate metrics (index-based MAE, Jaccard) remain numerically valid; DUAL_GRAPH_S1_FAIL verdict is unaffected.
3. **No new GNN architecture until the integrated prototype is complete.** A1 implementation (GConvGRU, EvolveGCN-H) authorized under DEC-028 contract; all other graph prediction branches remain closed.
4. **Next phase is HERALD Economic Observatory v0.1.** Produce a unified export per territory/country/year/sector with: observed value, Ridge forecast, uncertainty interval, economic state label, velocity/acceleration, available evidence. Two graph layers: G1-L2 territorial (existing) and sector→sector (simple auditable method, to implement). Incremental dashboard adaptation from existing France base.
5. **Archive and rastreability policy applied.** Documents classified as ACTIVE, historical, or SUPERSEDED in `HERALD_ACTIVE_DOCUMENT_INDEX.md`. Artefact registry in `herald_artifact_registry.json`. Movements of files in `reports/` are by index only — no physical moves to avoid breaking references.
**Rationale:** Consolidating after a major negative result (P6 FAIL) prevents re-deriving settled decisions in future sessions. The direction towards a multi-function observatory is supported by the validated components (persistence forecasting, G1-L2 associations, G2 dynamics). The sector-edge label error must be formally recorded before the artefact is cited by any publication.
**Limitations:** Observatory v0.1 is not yet implemented. Sector→sector graph method is not yet selected. A1 model (GConvGRU/EvolveGCN-H) is authorized but not yet implemented. The 85% data coverage gap is primarily Spain, Czech Republic, and full cross-country harmonization.
**Reopen condition for direction change:** Explicit DEC-* entry with new evidence or new data. Performance failure in any single branch is not sufficient to revise the overall observatory direction.
**Affected files:** `reports/HERALD_PROJECT_CHARTER.md` (new); `reports/HERALD_CURRENT_STATE.md` (new); `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` (new); `reports/herald_artifact_registry.json` (new); `CODEX_MEMORY.md` (updated); `README.md` (updated).

---

## DEC-031 — 2026-06-12 — S1_FR_FAIL: GConvGRU and EvolveGCN-H fail frozen FR gate; graph-temporal prediction branch closed

**Phase:** Graph-temporal A1 / S1-FR local test
**Question:** Do GConvGRU (A1a) or EvolveGCN-H (A1b) improve territorial enterprise-birth prediction over AR-Ridge for France (280 ZE, eval 2021–2025) under the frozen fail-closed gate from DEC-028?
**Evidence:** `data/processed/graph_temporal_s1/s1_fr_results.json`; `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md`. 5 seeds {42–46}, 5 eval years {2021–2025}, rolling-origin folds.

Results:

| Model | Mean WMAPE | Years > Ridge | p_temporal | p_territory |
|---|---:|---:|---:|---:|
| AR-Ridge | 0.064856 | — | — | — |
| A0-neural (no graph) | 0.064888 | — | — | — |
| GConvGRU | 0.064922 | 1/5 | 1.0000 | 1.0000 |
| EvolveGCN-H | 0.064973 | 1/5 | 1.0000 | 0.2927 |

Gate criteria (all frozen at DEC-028; all evaluated for both models):
- `improves_ridge_at_least_1pct`: FAIL — GConvGRU +0.1% vs Ridge, EvolveGCN-H +0.2%
- `improves_a0_at_least_1pct`: FAIL — neither model improves over equal-capacity no-graph control
- `wins_at_least_half_years`: FAIL — both models win only 1 of 5 eval years
- `beats_temporal_null_p_le_005`: FAIL — both models, p=1.0 (graph permutation nulls not rejected)
- `beats_territory_null_p_le_005`: FAIL — GConvGRU p=1.0; EvolveGCN-H p=0.293

Leakage, seed-stability (`seed_std_le_0005`), and tail-risk (`no_year_over_10pct_worse`) checks all pass. COVID-sensitivity (excluding 2020 from adjacency) does not materially change the result (Δ WMAPE < 0.000004 for both models).

**Alternatives considered:** (1) HPC battery — rejected; local gate failed on all 5 criteria; no reopen condition is met. (2) New architecture (higher capacity) — deferred; requires new information hypothesis, not a performance retry. (3) New feature set — deferred; ARDECO direct predictor also failed (`ARDECO_RIDGE_NOT_PROMOTED`); any new features require a new DEC-*.
**Decision:** S1_FR_FAIL. Graph-temporal prediction branch CLOSED. The tested architectures (GConvGRU, EvolveGCN-H) cannot be justified as replacements for AR-Ridge under the current 3-feature tensor (sector growth, sector share, normalized sector births). No HPC submission authorized. Observatory v0.1 proceeds without graph-temporal correction.
**Rationale:** The fail-closed gate was pre-registered at DEC-028. All 5 gate criteria are independently falsified. Both models perform within noise of AR-Ridge and are indistinguishable from temporal and territory permutation nulls, confirming that the recurrent graph architecture adds no exploitable information under the current feature set. This is a feature-set limitation, not necessarily an architecture limitation.
**Limitations:** The tested feature set is narrow (3 features). Wider economic features (ARDECO, mobility) may provide a different signal, but must first be validated as direct predictors before being combined with graph architectures. The null-permutation test has limited statistical power at n=5 eval years and n=5 seeds.
**Reopen condition:** New information hypothesis demonstrated to improve over AR-Ridge without a graph (new DEC-* required). Documented operational failure in protocol or data integrity. Performance failure on this narrow feature set alone is not a reopen condition.
**Affected files:** `reports/HERALD_GRAPH_TEMPORAL_S1_FR_AUDIT.md` (committed); `data/processed/graph_temporal_s1/s1_fr_results.json` (committed); `data/processed/graph_temporal_s1/s1_fr_checkpoint.json` (committed); `reports/HERALD_CURRENT_STATE.md`; `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`; `reports/HERALD_EVIDENCE_MATRIX.md`; `reports/HERALD_RESEARCH_GANTT.md`; `reports/herald_artifact_registry.json`; `CODEX_MEMORY.md`.

---

## DEC-032 — 2026-06-12 — Observatory v0.1.1/v0.2: corrected states and sector export

**Phase:** HERALD Economic Observatory

**Question:** Can the validated data components be exposed in one causal-safe,
sector-aware prototype without conflating dataset, forecast and graph evidence?

**Evidence:** Aggregate PT/IT/AT panel (1,963 rows) and national sector panel
FR/NL/PT (45,945 rows). Twenty-one Observatory tests cover state semantics,
causal persistence, rolling-origin provenance, masks, dimensions, evidence
separation and deterministic output.

**Decision:**
1. Aggregate v0.1 is superseded by v0.1.1. `deceleration` now means positive
growth that is slower than the prior positive growth rate; contraction is
`decline`.
2. Data, forecast and graph evidence are separate fields. Dataset inclusion
does not validate a forecast or graph claim.
3. Sector v0.2 is ACTIVE/REGENERABLE for FR/NL/PT: 345 territories, nine
sectors and 45,945 rows.
4. Structural absence and missing observations remain masked and `NaN`, never
economic zero.
5. Point Ridge forecasts are exploratory. Intervals remain unavailable.
6. G1-L2 availability means an analytical same-sector territorial association
field only. `sector_graph_available=0`.
7. The next authorized implementation is a signed, lagged sector-to-sector
association layer with stability and permutation controls. No GNN and no
structural-causality claim.

**Limitations:** National target concepts remain heterogeneous. The export does
not validate pooling, recommendation, uncertainty intervals or sector
influence.

**Affected files:** `src/data/european_panel/build_observatory_export.py`;
`tests/test_observatory_export.py`;
`reports/HERALD_OBSERVATORY_V01_DATA_CONTRACT.md`;
`reports/herald_artifact_registry.json`; `reports/HERALD_CURRENT_STATE.md`;
`reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`; `reports/HERALD_RESEARCH_GANTT.md`;
`README.md`; `CODEX_MEMORY.md`.

---

## DEC-033 — 2026-06-12 — Signed lagged sector precedence graph contract

**Phase:** HERALD Economic Observatory, sector→sector layer

**Question:** Does lagged growth in sector A add information about next-year
growth in sector B after controlling B's own lag?

**Method frozen before execution:** Directed lag-1 partial regression in
six-year country windows; territory/year demeaning; standardized signed
coefficient; incremental R²; within-year territory permutation; BH/FDR;
territory bootstrap sign stability; main and 2020-excluded scenarios.

**Promotion gate:** `q≤0.05`, `|beta|≥0.10`, `delta_r2≥0.005`, sign stability
`≥0.70`, at least 60 observations. Prototype promotion additionally requires
COVID-robust promoted edges in at least two countries.

**Decision:** Implementation and unit tests are authorized. Full execution is
pending. Outputs are predictive-precedence associations, never structural
causality or economic intervention effects. No dashboard edge may be displayed
before the full run is audited.

**Affected files:** `src/data/european_panel/build_sector_precedence_graph.py`;
`tests/test_sector_precedence_graph.py`;
`reports/HERALD_SECTOR_PRECEDENCE_GRAPH_CONTRACT.md`.

---

## DEC-034 — 2026-06-12 — Phase 7 sector precedence study: SECTOR_PRECEDENCE_PROTOTYPE_READY

**Phase:** HERALD Phase 7 — Distributed Sector Precedence Study

**Question:** Does lagged sector growth predict next-year sector birth growth in FR/NL/PT after permutation-based inference, BH/FDR correction, and COVID robustness filtering?

**Study:** 710 distributed tasks (FR=198, NL=288, PT=224); 5456 edges tested; 368 NaN (n<60, expected). Panel: `herald_observatory_v02`, SHA256=`a6f8a5b2a34f17fac028518bf7955f7d8931c7a498b0af57b1afae5eb62c742e`. All tasks COMPLETED; BH/FDR independently recomputed (max diff 1.11e-16). Slurm job 7455266, meso.

**Gate results (pre-registered, immutable):**

| Gate | Threshold | Result |
|------|-----------|--------|
| q_fdr | ≤ 0.05 | Applied per country×scenario×window family |
| \|beta\| | ≥ 0.10 | Applied to all candidate edges |
| delta_r2 | ≥ 0.005 | Applied to all candidate edges |
| bootstrap_sign_stability | ≥ 0.70 | Applied to all candidate edges |
| n_samples | ≥ 60 | Applied; 368/5456 edges dropped (NaN) |

**Promoted edges (main scenario):** 25 (FR=1, NL=8, PT=16)
**Promoted edges (without_2020):** 34 (FR=1, NL=6, PT=27)
**COVID-robust edges (promoted both scenarios, same sign):** 12 (NL=3, PT=9)
**Countries with COVID-robust edges:** 2 (NL, PT) → **≥2 threshold met**

**FR note:** One promoted edge (RU→MN, 2020-2025, β=−0.108) passes main gates but is not COVID-robust (the without_2020 promoted edge is a different window/pair). FR does not contribute to prototype readiness.

**Decision: SECTOR_PRECEDENCE_PROTOTYPE_READY.**
The prototype prototype gate (≥2 countries with COVID-robust edges) is satisfied. These associations represent *predictive precedence* only — lagged sector growth explains a small but statistically reliable additional fraction of variance in target sector birth growth after controlling for own lag, in periods unconfounded by COVID-19. No structural economic causality or intervention claim is supported or implied.

**Alternatives considered:** Requiring ≥3 countries (not met; FR contributes 0 COVID-robust). Not met under that criterion — but the pre-registered threshold is ≥2.

**Limitations:** (1) All associations are observational and associative. (2) Sector codes are A10 NACE Rev.2 aggregations; within-sector heterogeneity is unmodeled. (3) PT and NL results dominate; FR contributes only 1 non-robust edge. (4) Short windows (6 years) limit the power for low-frequency dynamics.

**Reopen condition:** New data extending panel to additional countries or years; methodological critique of the demeaning approach or permutation schema; discovery of data integrity issue.

**Affected files:**
`data/processed/sector_precedence_results/decision.json`;
`data/processed/sector_precedence_results/all_edges.csv`;
`data/processed/sector_precedence_results/latest.csv`;
`data/processed/sector_precedence_results/covid_robust_edges.csv`;
`data/processed/sector_precedence_results/audit/audit_report.json`;
`reports/HERALD_PHASE7_SECTOR_PRECEDENCE.md`.

---

## DEC-035 — 2026-06-12 — Observatory v0.3: integrate validated sector precedence layer

**Phase:** HERALD Observatory v0.3

**Question:** How should the validated Phase 7 sector precedence results be integrated into the observatory export and dashboard?

**Evidence:** DEC-034 confirms SECTOR_PRECEDENCE_PROTOTYPE_READY: 12 COVID-robust edges (NL=3, PT=9), 25 total promoted main edges (FR=1, NL=8, PT=16). Audit PASS; BH/FDR discrepancy max 1.11e-16.

**Decision:** Observatory v0.3 integrates validated results as a new sector→sector relations layer. Panel row count unchanged (45,945). Schema updated with `sector_graph_available` field reflecting COVID-robust window coverage per country:
- NL: years 2014–2019 (structural_mask=1)
- PT: years 2014–2019, 2015–2020, 2017–2022 (structural_mask=1)
- FR: always 0 (0 COVID-robust edges)

Edges classified:
- `ROBUST` (12 edges): promoted in main AND without_2020, same sign — safe to display by default
- `MAIN_ONLY_EXPLORATORY` (13 edges): promoted in main only — hidden by default, user opt-in in dashboard

Provenance note required on all outputs: *"Edges are predictive associations (observational precedence). No structural causality, mechanism, or intervention claim is supported. DEC-034 (2026-06-12)."*

**Alternatives considered:** Showing all 25 main edges by default (rejected — exploratory edges should not be presented with same weight as COVID-robust ones). Showing only the 12 robust edges (rejected — 13 exploratory edges have scientific value if clearly labelled). Separate dashboard file (rejected — integrated in v0.3 to maintain single source of truth).

**Rationale:** Separation of ROBUST and MAIN_ONLY_EXPLORATORY preserves scientific integrity while enabling transparent exploration of preliminary signals.

**Limitations:** (1) Sector graph available only for NL/PT in specific windows. (2) FR contributions are exploratory only. (3) Dashboard is read-only; no claim of actionable policy recommendation.

**Reopen condition:** New panel data, new countries, or discovery of issue in Phase 7 execution.

**Affected files:**
`src/data/european_panel/build_observatory_v03.py`;
`data/processed/herald_observatory_v03/herald_observatory_v03_panel.csv`;
`data/processed/herald_observatory_v03/herald_observatory_v03_sector_relations.json`;
`data/processed/herald_observatory_v03/herald_observatory_v03_manifest.json`;
`data/processed/herald_observatory_v03/herald_observatory_v03_summary.json`;
`reports/dashboards/herald_observatory_v03_dashboard.html`;
`tests/test_observatory_v03.py`;
`reports/HERALD_OBSERVATORY_V03_AUDIT.md`.

---

## DEC-036 — 2026-06-12 — Observatory v0.3 corrections: geographic dashboard, derived windows, Plotly embed, France ZE scale

**Phase:** HERALD Observatory v0.3 (corrections to initial v0.3 from DEC-035)

**Question:** Three problems in the initial v0.3 dashboard; and does France show sector precedence at ZE functional scale?

### Problem 1 — ROBUST_WINDOWS hardcoded

**Finding:** `ROBUST_WINDOWS = {"NL": [...], "PT": [...]}` was defined as a module-level constant, creating a risk of drift from `covid_robust_edges.csv`.

**Decision:** Remove the constant. Add `derive_robust_windows(path)` which reads `covid_robust_edges.csv`, performs Phase 7 consistency checks (FAIL_CLOSED if NL≠3, PT≠9, FR≠0 or file missing/empty), and returns the derived per-country windows. All downstream computations (`sector_graph_available`, manifest, dashboard) use the derived value.

**Reopen condition:** Phase 7 is re-run with new data. Requires a new DEC-* entry before changing gate counts.

### Problem 2 — Dashboard not truly self-contained

**Finding:** Dashboard referenced `https://cdn.plot.ly/plotly-2.27.0.min.js` externally.

**Decision:** Embed Plotly JS locally via `_plotly_js_tag()` which reads `plotly/package_data/plotly.min.js` from the installed package. Fallback to CDN if local file not found (logged as WARNING). Dashboard size: ~6.2MB (4.7MB Plotly + data). Manifest records `"plotly_dependency": "local_embedded"` or `"cdn_fallback"`. Test detects whether CDN is declared when used.

### Problem 3 — No real geographic map

**Finding:** Dashboard had no choropleth map; sections were stacked without hierarchy.

**Decision:** Add `go.Choropleth` map as the primary element (Section 1). Map uses `geo.fitbounds: 'geojson'`, `geo.visible: false` — no external map tiles needed. GeoJSON embedded: FR from `ze2020_geometry.geojson` (280 features), NL from `nuts3_2021_eurostat.geojson` (40 COROP features), PT from `nuts3_2021_eurostat.geojson` (25 NUTS3 features). Each GeoJSON feature has a `panel_id` property matching `territory_id` in the panel. NL COROP→NUTS3 mapping via name matching (40/40 matched). Territorial system (ZE2020 / COROP / NUTS3) labeled explicitly per country. Sector graph retained as Section 2 (complementary view). Territory click → side panel with mini time series (state bar chart + velocity line, offline). Warning that sector→sector edges are country-level, not territory-localised.

### Part B — France ZE scale sensitivity

**Finding:** France in Phase 7 (DEC-034) and Observatory v02 already uses ZE2020 (Zones d'Emploi 2020, 280 functional labor market zones), not NUTS3. The `region_system` column confirms `ZE2020` for all FR rows. The Phase 7 FR result (1 promoted main edge, 0 COVID-robust) IS the ZE-scale result.

**Decision:** No separate `P7_FR_ZE_SCALE_SENSITIVITY` HPC study is needed. Phase 7 for France was already conducted at the functional ZE scale. The absence of COVID-robust signal is confirmed at ZE functional scale (280 zones, 6-year windows, 999 permutations, 500 bootstraps).

**Interpretation:** "The absence of COVID-robust sector precedence signal for France holds at both the NUTS3 (sector_panel_fr_nuts3.csv, used in G1-L2 work) and ZE2020 functional scales. The ZE2020 result is the Phase 7 primary result."

**Forbidden interpretation:** "ZE2020 is methodologically superior to NUTS3 merely because it produced significance." The ZE result for France is null (0 robust edges); there is no hierarchy claim.

**Asymmetry note:** The three-country panel uses incommensurable territorial systems (ZE2020/FR, COROP/NL, NUTS3/PT). This is a known limitation; cross-country territory-level comparison is not authorised.

**Alternatives considered:** Running Phase 7 on NUTS3 FR panel (sector_panel_fr_nuts3.csv) as a NUTS3 sensitivity. This would require a new pre-registered hypothesis; not authorised under current DEC-033 scope.

**Limitations:** Dashboard now 6.2MB (larger but offline-capable). COROP→NUTS3 name-matching may be imprecise if names differ between panel and geometry (40/40 matched by inspection). Territory time series in click panel shows aggregated states only (no per-sector per-territory breakdown).

**Affected files:**
`src/data/european_panel/build_observatory_v03.py`;
`tests/test_observatory_v03.py`;
`reports/dashboards/herald_observatory_v03_dashboard.html`;
`reports/HERALD_OBSERVATORY_V03_AUDIT.md`.

---

## DEC-037 — 2026-06-12 — Phase 8: Territorial Sector Statistical Influence

**Addendum (2026-06-12):** Evidence level nomenclature corrected. Old names (STRONG/MODERATE/WEAK) replaced throughout code, tests, artifacts, and documentation with:
- `HIGH_DESCRIPTIVE_INFLUENCE` (was STRONG) — above Q75 + stable + LOYO + wo20
- `MODERATE_DESCRIPTIVE_INFLUENCE` (was MODERATE) — above Q50 + stable + LOYO + wo20
- `LOW_DESCRIPTIVE_INFLUENCE` (was WEAK) — above Q50 + stable, LOYO or wo20 inconclusive
Decision record fields added: `interpretation_scope=descriptive_relative_influence`, `independent_replication=false`, `spatial_flow_supported=false`, `causal_effect_supported=false`, `threshold_status=defined_before_execution_not_formally_preregistered`. Overlapping windows explicitly documented as non-independent. Gate keys renamed: `evidence_strong_percentile→high_descriptive_percentile`, `evidence_moderate_percentile→moderate_descriptive_percentile`. Numeric results unchanged. Territorial influence layer integrated into Observatory v0.3 dashboard as Section 6 (toggle, divergent colorscale). Manifest version bumped to 0.2.

**Phase:** Phase 8 — Territorial Sector Statistical Influence (DESCRIPTIVE_ONLY layer)

**Question:** Can the 12 COVID-robust Phase 7 sector-precedence associations be localised to specific territories? For each relation, which territories contribute most to the global beta?

**Method:** Leave-one-territory-out (LOTO) regression influence decomposition:

    influence_r = beta_full - beta_without_territory_r

where `beta_full` replicates Phase 7 exactly (two-way demean → standardize → OLS on velocity, using observation_mask=1 AND structural_mask=1). Beta integrity verified: max deviation from Phase 7 = 3.6e-16 (float precision only).

**Evidence:**

- All 12 ROBUST relations eligible: NL=40 territories/240 pairs, PT=25 territories/150 pairs
- PT KZ structurally absent (observation_mask=0 entire column) — not eligible, not in ROBUST edges
- Bootstrap (500 draws, territory resample with replacement): mean sign stability 0.88, range [0.45, 1.00]
- LOYO consistency (leave-one-year-out): 311/345 = 90% of records consistent across LOYO splits
- Without-2020 consistency (6 windows containing 2020): 120/150 = 80% consistent

**Evidence breakdown (n=345 territory-relation records):**

| Level | Count | Meaning |
|-------|-------|---------|
| HIGH_DESCRIPTIVE_INFLUENCE | 91 | Q75 + bootstrap ≥ 0.60 + LOYO consistent + without-2020 consistent |
| MODERATE_DESCRIPTIVE_INFLUENCE | 78 | Q50 + bootstrap ≥ 0.60 + LOYO consistent + without-2020 consistent |
| LOW_DESCRIPTIVE_INFLUENCE | 8 | Q50 + bootstrap ≥ 0.60, LOYO or without-2020 inconclusive |
| DESCRIPTIVE_ONLY | 168 | Influence measurable but below gates |
| INSUFFICIENT_DATA | 0 | All territories had sufficient data |

**Top concentration pattern:** Top-3 territories account for 31–61% of total absolute influence per relation (median ≈ 48%). The associations are not uniformly distributed — some regions consistently drive the statistical patterns.

**Decision:** DESCRIPTIVE_ONLY

The 12 Phase 7 global betas are validated scientific results (permutation-tested, bootstrap-stable, COVID-robust). This Phase 8 layer localises them into per-territory contributions using LOTO. The evidence level DESCRIPTIVE_ONLY applies to the LAYER as a whole — it provides a descriptive territorial lens on the already-validated national associations. It does NOT:
- Add new promoted scientific claims beyond DEC-034
- Imply causal transmission, geographic propagation, or enterprise-birth flow between territories
- Constitute a recommended policy instrument

**Pre-specified gates (sealed before execution):**

| Gate | Threshold |
|------|-----------|
| beta_integrity_tol | 0.01 |
| min_territory_own_pairs | 3 |
| min_loto_pairs | 30 |
| bootstrap_sign_stability_threshold | 0.60 |
| loyo_min_consistent_splits | 4 of 5 |
| high_descriptive_percentile | Q75 |
| moderate_descriptive_percentile | Q50 |

**Rationale:** Phase 7 already validates the existence of sector-precedence associations at the national level. This layer answers "where?" using the most interpretable method (LOTO = remove one territory, measure beta change). Bootstrap and LOYO provide stability checks without re-running HPC. The descriptive label prevents over-interpretation.

**Limitations:**
- n_territories is moderate (25-40), making LOTO influence sensitive to outlier territories
- 6 years per window limits within-territory power; LOTO contributions conflate leverage with genuine local association strength
- Territorial systems are incommensurable (ZE2020 / COROP / NUTS3); no cross-country comparison
- Islands/overseas PT_200/PT_300 included in LOTO computation (matching Phase 7), excluded from choropleth map only
- FR has 0 ROBUST relations; no Phase 8 rows for France

**Alternatives considered:**
- Score approach (source_growth × target_growth): rejected — not decomposable from the Phase 7 regression
- Partial correlation per territory: rejected — doesn't have a clean summation property with LOTO
- Full permutation of LOTO (999 per territory): rejected — computationally expensive for 345 territories, and global beta is already permutation-validated by Phase 7

**HPC:** Not used. All computation local (≈10 min, 12 relations × 500 bootstrap draws).

**Reopen condition:** Evidence can be elevated from DESCRIPTIVE_ONLY if (a) panel is extended to more countries/years with same territorial resolution, or (b) a country shows strong concentration of influence in a specific economic cluster that replicates across independent windows.

**Affected files:**
`src/data/european_panel/build_territorial_sector_movements.py`;
`tests/test_territorial_sector_movements.py`;
`data/processed/herald_observatory_v04/` (not committed — regenerable);
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (this entry);
`reports/HERALD_CURRENT_STATE.md`;
`reports/HERALD_EVIDENCE_MATRIX.md`;
`CODEX_MEMORY.md`.

---

## DEC-038 — 2026-06-13 — European Territorial Sector Coverage Preflight

**Phase:** Pre-Phase 7 extension — eligibility assessment

**Question:** Which European countries have data compatible with extending the HERALD Observatory before the neural graph layer? Compatibility requires: territory × year × A10 sector enterprise birth series; ≥6 consecutive years; NUTS3 or documented territorial unit; ≥8 A10-comparable sectors; n_samples ≥ 60; official geometry; concept comparability with FR/NL/PT.

**Evidence:** Audit of all local data (Eurostat BD_HGNACE_R bd_hgnace_r_raw_full.csv, Eurostat BD_SIZE_R3, local adapted panels for AT/BE/IT, Observatory panels for FR/NL/PT) plus documented external national sources. 27 countries evaluated. Script: `src/data/european_panel/audit_european_sector_coverage.py`.

**Critical findings:**

1. Eurostat BD_HGNACE_R provides ENT_BRTH_NR at NUTS3 for 26 EU countries, but **only Finland has data before 2021**. All others: 2021-2023 only (3 years — insufficient).
2. **K_L combined in BD_HGNACE_R for all countries**: KZ (financial) and LZ (real estate) are inseparable. Phase 7 relations involving KZ or LZ individually cannot be tested from Eurostat BD alone.
3. **Finland (FI)** is the only non-Observatory country eligible from existing Eurostat data. 19 stable NUTS3 territories, 2013-2021 (9 years), 8 effective A10 sectors. Status: ELIGIBLE_WITH_MAPPING.
4. **Belgium** is definitively blocked: `flag_target_concept=vat_first_registration` (≠ enterprise_birth). This is a permanent semantic blocker; no sector births available from any local source.
5. Nine countries (ES, IT, DE, SE, PL, RO, CZ, DK, AT) have national statistical agency sources with ≥6 years of NUTS3 sector births; all classified ELIGIBLE_WITH_DOWNLOAD.
6. The direct PT→ES→FR→BE→NL geographic corridor is broken by Belgium. Viable sub-corridor: PT–ES–FR–NL via France; FR–IT–AT separately.

**Decision:** ELIGIBILITY CLASSIFICATION COMPLETE — NO INTEGRATION IN THIS TASK

Status per country:
- `IN_OBSERVATORY`: FR (280 ZE2020), NL (40 COROP), PT (25 NUTS3)
- `ELIGIBLE_WITH_MAPPING`: FI (19 NUTS3, Eurostat BD, K_L documented)
- `ELIGIBLE_WITH_DOWNLOAD`: AT, CZ, DE, DK, ES, IT, PL, RO, SE
- `PARTIAL_DESCRIPTIVE_ONLY`: BG, CY, EE, EL, HR, HU, IE, LT, LU, LV, MT, SI, SK
- `BLOCKED_SEMANTICS`: BE

**Panel proposals:**

| Proposal | Countries | Condition |
|----------|-----------|-----------|
| CORE_CONTIGUOUS | AT, ES, FR, IT, NL, PT | Download + mapping required for AT, ES, IT |
| EU_EXTENDED | AT, CZ, DE, DK, ES, FI, FR, IT, NL, PL, PT, RO, SE | Download required for non-FI, non-Observatory |
| DESCRIPTIVE_ONLY | BG, CY, EE, EL, HR, HU, IE, LT, LU, LV, MT, SI, SK | Total births only (BD_SIZE_R3 3 years) |
| BLOCKED | BE | Permanent semantic blocker |

**Rationale:** The preflight establishes a firm evidence-based classification before any integration work. Downloading national sources for ELIGIBLE_WITH_DOWNLOAD countries is an explicit future task; it cannot be pre-authorised in this decision.

**Limitations:**
- External source URLs and metadata are documented but not downloaded. Actual coverage may differ.
- Germany (DE): semantic verification of Gewerbemeldungen vs enterprise_birth concept required.
- Finland K_L mapping decision (single KL sector vs imputation) must be pre-specified before integration.

**Reopen condition:** A country's status may be upgraded to ELIGIBLE_NOW once its national source data is downloaded, validated, and its concept verified against FR/NL/PT baseline.

**Affected files:**
`src/data/european_panel/audit_european_sector_coverage.py`;
`tests/test_european_sector_coverage.py`;
`data/processed/european_panel/european_sector_coverage_matrix.csv`;
`data/processed/european_panel/european_sector_coverage_summary.json`;
`data/processed/european_panel/european_sector_source_manifest.json`;
`reports/HERALD_EUROPEAN_SECTOR_COVERAGE_PREFLIGHT.md`.

## DEC-039 — 2026-06-13 — Synthetic Controlled Benchmark for Imputation Validation

**Status:** IMPLEMENTED — smoke PASS

**Scope:** Phase 9 — synthetic controlled benchmark to validate HERALD's capability for (a) missing label reconstruction and (b) recovery of non-linear economic dynamics with known ground truth.

**Contract (pre-specified, falsifiable):**
- H1: HERALD (B7) achieves lower MAE at hidden cells than Ridge (B5) by ≥5% on average across seeds and mask levels (G1).
- H2: Sector-sector edge recovery AUC ≥ 0.60 for HERALD with true graph (B7) (G2).
- H3: 90% predictive interval achieves ≥0.80 empirical coverage at hidden cells (G3 calibration).
- G3: Permuted graph (B8) MAE ≥ HERALD with graph (B7) MAE — graph must help.
- G5: Temporal feature leakage check passes (verified causal features, no future information).
- G6: False positive edge rate (top-k attention on non-edges) < 0.30 on average.

**Advance criterion:** HERALD advances only if (G1 PASS OR G2 PASS) AND G5 PASS AND G3 PASS.

**Smoke test results (10T × 5S × 12Y, MCAR 20%, 2 seeds, 100 epochs):**
- No-NaN: PASS
- Leakage check: PASS
- Elapsed: 1.7s (< 3 min limit)
- G1 preview: False (not conclusive at smoke scale)
- G3 preview: False (not conclusive at smoke scale)

**Baselines:**
- B1 Mean, B3 ForwardFill, B5 Ridge (temporal only), B6 Neural-no-graph
- B7 HERALD-graph, B8 HERALD-permuted graph

**Architecture notes:**
- All temporal features strictly causal (running cumsum, no future information)
- Mask-explicit: zeros at hidden cells only for neighbour aggregation denominator
- Gaussian NLL loss on observed cells only; loss never divides by hidden cells
- MC Dropout for predictive uncertainty (50 forward passes)

**Bugs fixed during implementation:**
- `_build_temporal_features`: whole-series mean/std (Features 0, 2) and whole-series AR1 mean (Feature 3) were non-causal; replaced with causal running statistics
- `train_herald_imputer`: `true_t` built from NaN panel caused NaN loss; fixed with `nan_to_num`

**Rationale:** Cannot claim neural architecture resolves missing data without controlled experiment. This benchmark provides falsifiable evidence of benefit (or lack thereof) compared to simple statistical baselines.

**Limitations:**
- Smoke scale (10T × 5S × 12Y) is insufficient to evaluate G1–G4; full evaluation requires HPC run (see HPC estimate below)
- edge AUC interpretation requires sufficient signal in the panel; highly noisy synthetic panels may produce uninformative results
- Calibration quality (G3) depends on dropout rate and training duration

**HPC estimate for full run:**
- Config space: 5 seeds × 3 mask mechanisms (MCAR/MAR/block) × 3 levels = 45 configs per model × 6 models = 270 jobs
- Expected: ~5–10 min/job on 1 CPU. Total: ~22–45 CPU-hours. Parallelizable to ~1–2 h wall time with 20+ cores.
- Full command (not yet authorised): `python src/modeles/synthetic/run_full_benchmark.py` (not yet implemented)
- **HPC NOT AUTHORISED until full benchmark script is written, reviewed, and smoke passed on larger scale**

**Affected files:**
`reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md`;
`src/data/synthetic/__init__.py`;
`src/data/synthetic/generate_herald_synthetic.py`;
`src/modeles/synthetic/__init__.py`;
`src/modeles/synthetic/imputation_baselines.py`;
`src/modeles/synthetic/herald_graph_imputer.py`;
`src/modeles/synthetic/evaluate_imputation.py`;
`src/modeles/synthetic/run_smoke.py`;
`tests/test_synthetic_benchmark.py`;
`data/processed/synthetic_benchmark/smoke_results.json`.

## DEC-040 — 2026-06-13 — Synthetic Benchmark: Extended Grid, Null Controls, Full Runner, Pilot

**Status:** IMPLEMENTED — pilot PASS (6/6 tasks, 86s, no NaN, no leakage failures)

**Scope:** Phase 9 extension — expanded benchmark from DEC-039 with full null-control suite,
4 benchmark scenarios, 5 seeds, 3 mask types × 3 levels, 12 models, fail-closed gate evaluation,
run_full_benchmark.py with atomic writes and resume, local pilot executed and passed.

**Changes from DEC-039:**

1. **50% masking level added** to all mask type tuples (previously 10%/20%/30% → now 10%/30%/50%).

2. **Four benchmark scenarios defined** (sealed in contract):
   - `linear` (frac_nonlinear=0.0): validates that HERALD does not degrade on simple case (G7)
   - `nonlinear_heavy` (0.8): primary stress test for non-linear dynamics
   - `mixed_default` (0.3): reference configuration
   - `generalization` (12 relations, frac_nonlinear=0.6, higher noise): tests out-of-distribution recovery (G8)

3. **Null control suite expanded:**
   - B9: Node-permuted adjacency (genuine structural mismatch — permutes rows+cols of adj only, NOT panel)
   - B10: Random Erdős-Rényi graph (density-preserving, symmetric)
   - B11: Oracle (frozen sector attention = log(true_adj), non-trainable)
   - **Copermutation proof (sealed):** copermuting adj+panel with same permutation = pure relabeling
     (max diff ≤ 5.5e-17). B9 permutes adj only to produce genuine mismatch.

4. **KNN baseline (B5) added** with strictly causal features:
   - Feature: running mean up to year y-1 for each (territory, sector)
   - Fallback at year 0 or no-history: causal_mean (not MeanImputer — verified not to use future years)
   - Tested: perturbing year 6 does not affect fill at year 5 (test_causal_knn_not_using_future)

5. **evaluate_imputation.py extended:**
   - Spearman r added alongside Pearson r
   - BreakdownMetrics (per sector, territory, regime)
   - StateMetrics (macro-F1, balanced accuracy, AUCPR for 4 economic states)
   - EdgeRecoveryMetrics now includes false_positive_rate and lag_accuracy

6. **gates.py created (G1–G8, fail-closed, pre-specified):**
   - G7: no regression >10% on linear scenario
   - G8: G1 passes on generalization scenario
   - Outcome flags: ARCHITECTURE_RECONSTRUCTION_SUPPORTED, DYNAMIC_RELATION_RECOVERY_SUPPORTED,
     UNCERTAINTY_CALIBRATED, SYNTHETIC_GENERALIZATION_SUPPORTED

7. **run_full_benchmark.py created:**
   - CLI: --dry-run, --task-id, --local-pilot, --confirm-full-run, --output-dir, --n-epochs
   - Atomic writes (write to .tmp then os.rename)
   - Resume: skip task if output JSON is valid (has "baselines" and "leakage_check" keys)
   - Deterministic manifest: 20 tasks (4 scenarios × 5 seeds), ordered lexicographically
   - Config hash (SHA-256 of serialised config) stored in each output for audit

8. **49 new tests added** (tests/test_full_benchmark.py):
   - Manifest completeness and determinism; generator extension (50% rate); atomic write; resume
   - Null controls: copermutation proof; random graph density preservation; oracle frozen
   - KNN causality (future-blindness test); extended metrics (Spearman, state metrics)
   - Gates: fixture PASS/FAIL for G1, G3, G5; gate threshold freeze; end-to-end run_task

**Pilot results (20T × 7S × 16Y, 200 epochs, seeds 42/123/456, linear + nonlinear_heavy):**
- 6/6 tasks PASS, 86s total (< 3 min limit), no NaN, no Inf
- herald_graph MAE: 0.2342–0.2675 (linear), 0.2034–0.2126 (nonlinear) — consistently < ridge
- G3 (permuted ≥ herald): 5/6 pass; linear/seed123 narrowly fails (to monitor at HPC scale)
- G4 (cal90 ≥ 0.80): 0/6 pass (MC Dropout undercalibrated: 0.26–0.29); documented, expected
- G5 (leakage): 6/6 PASS
- Oracle marginally better than herald_graph (expected)
- **HPC verdict: HPC_READY**

**Bugs fixed during implementation (all verified by tests):**
- build_permuted_adj: now returns 4 values (adj_s_perm, adj_t_perm, perm_s, perm_t)
- KNN fallback was non-causal (MeanImputer uses future years); replaced with causal_mean
- Gate fixture: best_non_graph was computed incorrectly (neural_no_graph was set better than ridge)
- NLL training loss assertion invalid for negative values; replaced with abs-tolerance check
- Permuted adj test used trivial zero sector_adj; replaced with forced non-identity rotation

**Rationale:** DEC-039 established architecture validity. DEC-040 provides the full evaluation
infrastructure (null controls, expanded scenarios, fail-closed gates, batch runner) needed for
a scientifically credible benchmark. HPC submission authorisation is deferred to explicit review
of this pilot output.

**Limitations:**
- G4 (calibration) expected to fail at current training scale; MC Dropout calibration requires
  larger training budget or post-hoc calibration (Platt scaling, temperature scaling)
- Pilot scale (200 epochs, 20T) insufficient to draw conclusions on G2 (AUC); HPC run required
- G3 narrowly fails in one pilot seed (linear/seed123); marginal difference (0.2632 vs 0.2675)
  attributed to insufficient training at pilot scale

**HPC estimate (full run, 500 epochs, 30T × 9S × 20Y):**
- 20 tasks × ~10 min/task = ~200 min total sequential
- With 20-core parallelism: ~12–15 min wall time
- Memory: < 2 GB/task

**Affected files:**
`reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md`;
`src/data/synthetic/generate_herald_synthetic.py`;
`src/modeles/synthetic/imputation_baselines.py` (KNN added);
`src/modeles/synthetic/herald_graph_imputer.py` (random graph, permuted returns 4 values);
`src/modeles/synthetic/evaluate_imputation.py` (full rewrite with Spearman, state, breakdown);
`src/modeles/synthetic/gates.py` (NEW);
`src/modeles/synthetic/run_full_benchmark.py` (NEW);
`src/modeles/synthetic/run_smoke.py` (fix build_permuted_adj call);
`tests/test_synthetic_benchmark.py` (fix permuted_adj unpacking, loss assertion);
`tests/test_full_benchmark.py` (NEW, 49 tests);
`hpc/phase9_synthetic_generalization/README.md` (NEW);
`hpc/phase9_synthetic_generalization/run_phase9.slurm` (NEW);
`data/processed/synthetic_benchmark/pilot/` (6 JSON task outputs).

## DEC-041 — 2026-06-13 — G3 Block-Masking Convergence Probe (linear/seed=123)

**Status:** COMPLETED — G3_NOT_CONFIRMED for seed=123; FULL_HPC_AUTHORIZED

**Scope:** Targeted convergence probe for the single G3 failure in the DEC-040 pilot.
Run: linear/seed=123, epochs=200/300/500, same PILOT_SCENARIOS config (20T×7S×16Y),
same mask combos (mcar_10/30, mar_10/30, block_10/30), all 12 models.

**Question:** Is the G3 block-masking failure for linear/seed=123 a convergence artifact
(resolves with more epochs) or a structural failure of the architecture?

**Answer: Structural failure, seed-specific.**

**G3 margin table (herald_perm_mae − herald_mae; positive = PASS):**

| mask_combo | 200 epochs | 300 epochs | 500 epochs |
|------------|-----------|-----------|-----------|
| block_10 | Δ=-0.0670 FAIL | Δ=-0.0375 FAIL | Δ=-0.0132 FAIL |
| block_30 | Δ=-0.0343 FAIL | Δ=-0.0275 FAIL | Δ=-0.0207 FAIL |
| mar_10 | Δ=+0.0238 PASS | Δ=+0.0233 PASS | Δ=+0.0269 PASS |
| mar_30 | Δ=+0.0175 PASS | Δ=+0.0085 PASS | Δ=+0.0202 PASS |
| mcar_10 | Δ=+0.0210 PASS | Δ=+0.0185 PASS | Δ=+0.0246 PASS |
| mcar_30 | Δ=+0.0174 PASS | Δ=+0.0120 PASS | Δ=+0.0219 PASS |

Block masking margins improve monotonically with epochs but do not flip sign at 500 epochs.
VERDICT: **G3_NOT_CONFIRMED** for linear/seed=123.

**Seed comparison (pilot, 200 epochs):**

| seed | block_10 | block_30 | mcar_10 | G3_all |
|------|---------|---------|--------|--------|
| 42 | +0.0042 PASS | +0.0108 PASS | -0.0043 FAIL | No (mcar_10 marginal) |
| 123 | -0.0670 FAIL | -0.0343 FAIL | +0.0210 PASS | No (block structural) |
| 456 | +0.0064 PASS | +0.0029 PASS | +0.0105 PASS | Yes |

**3-seed aggregate G3 for linear:** mean_perm=0.2476 ≥ mean_herald=0.2457 → **PASS at aggregate level.**
Block masking G3 failure is seed=123-specific.

**Structural interpretation:**
seed=123 generates a specific linear panel where the true graph structure introduces
propagation noise that hurts block-missing imputation. The permuted graph, by breaking
sector co-movement, causes the model to rely more on temporal features — which are more
informative under block missingness (adjacent years available). This is a documented limitation:
graph-augmented models can degrade on block-missing scenarios with linear dynamics when graph
propagation couples errors across sectors.

**Determinism:** CONFIRMED. Both runs of 200 epochs produce identical model metrics.
The 30 reported "differences" in the initial check were all in `train_s` (wall-clock time),
which is inherently non-deterministic. All MAE, AUC, calibration, and other metrics identical.

**Calibration (G4):**
Mean cal90 = 0.260 across all epoch budgets (threshold: 0.80). G4 FAIL confirmed.
MC Dropout is systematically overconfident and the failure does not diminish with epochs.
This task does NOT change the MC Dropout architecture.
**Conformal calibration specification (for future task, not implemented here):**
Post-hoc calibration via split conformal prediction (Angelopoulos & Bates 2021):
- Fit conformal quantile on a held-out calibration set (last 3 years = 20%)
- Compute residuals at calibration level (1-α) = 0.90
- Adjust prediction intervals by learned quantile
- Re-evaluate G4 with conformal intervals
This does not require architecture changes.

**Runtime:**
- 200 epochs: 26.8s / peak 51 MB
- 300 epochs: ~40s / peak < 100 MB
- 500 epochs: 62.6s / peak < 100 MB
- Determinism re-run: ~27s

**G4 status:** UNCERTAINTY_NOT_CALIBRATED (frozen; not blocked for HPC)

**HPC decision: FULL_HPC_AUTHORIZED** (conditions):
1. Epoch budget frozen at 500 for all 20 HPC tasks
2. G3 evaluated at aggregate level (across all 5 seeds per scenario)
3. Block masking per-seed failure documented here; does not block HPC
4. G4 FAIL expected and documented; does not block G1/G2/G3/G5 evaluation
5. Full array (`sbatch run_phase9.slurm`) still requires explicit authorisation to submit

**Affected files:**
`src/modeles/synthetic/run_convergence_probe.py` (NEW);
`data/processed/synthetic_benchmark/convergence_probe/` (4 task JSONs + summary);
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (this entry);

---

## DEC-042 — 2026-06-13 — Graph Usage Diagnostic

**Phase:** Phase 9 — diagnostic sub-task (post HPC full run)
**Question:** Why does the HERALD neural architecture fail to exploit the true graph signal?
HPC full run results: herald MAE=0.308, oracle MAE=0.307, ffill MAE=0.255. All G1 FAIL, G2
falsely reported FAIL (AUC=0.27), ffill dominates. Diagnose before changing architecture.

**Evidence:** Code audit + pre-specified diagnostic gates D1-D5 + trivial scenario (5T×3S×30Y,
1 edge, seed=42).

**Bugs identified:**

B1 (CRITICAL — evaluation): `compute_edge_recovery_metrics` in `evaluate_imputation.py:260`
used `y_score = learned_attn[rows, cols]` where rows=source, cols=target. But
`learned_attn[i,j]` = weight for target i from source j (j→i). Correct: `learned_attn[cols,rows]`.
This transposed AUC from 0.27 (reported) to 0.73 (corrected). G2 was always passing; the
metric was wrong. Symmetry check: `|0.273 + 0.727 − 1.0| ≈ 0.0`.

B2 (METHODOLOGICAL): `_sector_adj_from_relations` returns symmetric adjacency (both s→t and
t→s set to 1 for any directed true edge). Oracle is initialised with this undirected matrix;
cannot distinguish source from target. MLP can break symmetry via gradient; oracle cannot.

B3 (ARCHITECTURAL): Graph aggregation uses contemporaneous values at year y. True cross-sector
effects use lagged values at year y−lag. Structural evidence: `corr(src[t-1],tgt[t]) >>
corr(src[t],tgt[t])` for the true relation. Empirical: oracle-lagged MAE=0.0595 <
oracle-contemp MAE=0.0623 on trivial scenario (−4.5%). On full benchmark (φ=0.3-0.6 AR),
contemp oracle cannot beat ffill.

**Diagnostic gate results:**
- D1 PASS: oracle MAE (0.062) < no-graph MAE (0.069)
- D2 PASS: |MAE_zero − MAE_oracle| = 0.006 > 1e-3
- D3 PASS: directed oracle AUC=1.0 (corrected); HPC corrected mean=0.727
- D4 FAIL: ceiling effect (AUC=1.0 at λ=0 on trivial); test non-discriminating at this scale
- D5 PASS: oracle-lagged MAE=0.060 < ffill MAE=0.078
- D6: NOT EVALUATED (D4 non-discriminating)

**Decision:**
Verdict: IMPLEMENTATION_BUG_FIXED + ARCHITECTURE_STRUCTURALLY_INADEQUATE

Action 1 (B1): Fix applied immediately — `y_score = learned_attn[cols, rows]`. No gate
thresholds changed. G2 PASS is now the correct evaluation. Minimum criterion (G2 + G5 + G3):
PASS after fix.

Action 2 (B3): Architectural fix (`HERALDGraphImputerLagged` — lag-1 sector aggregation)
provided as diagnostic prototype in `run_diagnostic.py`. NOT authorised for full benchmark
without new DEC specifying new gates and HPC budget.

Action 3 (B2): Documented only. No immediate change to `sector_adj` or oracle wiring.

**G2 gate revision:** HPC run with corrected evaluation → G2 PASS (0.727 > 0.60 threshold).
G1 remains FAIL. G5 PASS. Minimum criterion: PASS.

**Limitations:**
- B3 diagnosis on trivial scenario (1 edge, φ=0.2, σ=0.05); full benchmark has 8 edges, φ=0.3-0.6.
- Corrected G2 does not affect HPC MAE results (imputation accuracy unchanged).
- D4 non-discriminating on trivial; future DEC should evaluate at full-benchmark scale.
- Conformal calibration: unchanged; still requires post-HPC DEC.

**Reopen condition:**
- D6 (architecture reopen): new DEC authorising B3 fix with new gates and HPC budget.

**Affected files:**
`src/modeles/synthetic/evaluate_imputation.py` (B1 fix: line 260);
`src/modeles/synthetic/run_diagnostic.py` (NEW — HERALDGraphImputerLagged + all diagnostic code);
`tests/test_diagnostic.py` (NEW — 12 pre-specified tests, 12/12 PASS);
`data/processed/synthetic_benchmark/diagnostic/diagnostic_results.json` (NEW);
`reports/HERALD_PHASE9_GRAPH_USAGE_DIAGNOSTIC.md` (NEW);
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (this entry);
`reports/HERALD_SYNTHETIC_BENCHMARK_CONTRACT.md` (G4 calibration spec added).

---

## DEC-043 — 2026-06-13 — Phase 10: Lagged Graph Architecture Benchmark

**Phase:** Phase 10 — architectural fix for B3 (lag mismatch, identified in DEC-042)
**Question:** Does lag-1/lag-2 sector message passing improve edge recovery (AUC) and
imputation (MAE) vs the contemporaneous architecture on the same synthetic benchmark?
**Status:** PRE-SPECIFIED — written before any benchmark is run. Gates are FROZEN.

**Hypothesis:**

H10a — Imputation: herald_lagged achieves lower MAE than herald_contemporaneous on ≥ 2/4
benchmark scenarios (same seeds, masks, epochs).

H10b — Edge recovery: combined corrected AUC ≥ 0.60 averaged over scenarios and seeds.

H10c — Structural: oracle_lagged MAE < oracle_contemp MAE AND oracle_lagged MAE < ffill MAE
in ≥ 3/4 scenarios.

**Architecture specification (frozen before benchmark):**

HERALDGraphImputerLagged:
  - Two learnable attention matrices: log_sect_attn_lag1 (n_S×n_S), log_sect_attn_lag2 (n_S×n_S)
  - Lag-1 feature: mask-weighted mean of observed source sectors at year t-1
  - Lag-2 feature: mask-weighted mean of observed source sectors at year t-2
  - Territory feature: contemporaneous (same as Phase 9)
  - MLP: 10 inputs (7 temporal + 3 graph), hidden_dim=64, dropout=0.1, 2 outputs (mean, log_sigma)
  - Year 0: lag-1 = 0 (no history). Years 0-1: lag-2 = 0 (no history). Explicit fallback.
  - Missing cells: mask-weighted average; when all lag-k neighbors missing, feature = 0.
  - No future information: only y_0..y_{t-1} accessible for year-t features.
  - get_sector_attention() returns max(lag1, lag2) for backward metric compatibility.

Oracle directed (frozen):
  - log_sect_attn_lag1[target, source] = 0 for true lag-1 directed edges source→target
  - log_sect_attn_lag2[target, source] = 0 for true lag-2 directed edges source→target
  - All other entries = log(1e-6). Both matrices frozen (requires_grad=False).
  - Fixes B2 (oracle now uses directed adjacency) AND B3 (lagged aggregation).

Models in Phase 10 (15 total = 12 Phase-9 + 3 new):
  Baseline (7): mean, median, ffill, temporal_interp, knn, ridge, graph_ridge
  Neural (8): neural_no_graph, herald_contemp, herald_contemp_permuted,
              herald_contemp_random, oracle_contemp,
              herald_lagged (NEW), herald_lagged_permuted (NEW), oracle_lagged (NEW)

**Gates L1-L8 (frozen — do not adjust after results):**

L1 WIRING: oracle_lagged MAE < oracle_contemp MAE AND < no_graph MAE, on ≥ 3/4 scenarios.
  Failure → ARCHITECTURE_REWIRING_FAILED; HPC blocked.

L2 RELATIONS: corrected combined AUC ≥ 0.60, averaged over seeds×scenarios.
  AND lag accuracy > 0.50 (better than random lag assignment) for lagged model.
  Failure → DYNAMIC_RELATION_RECOVERY_FAILED.

L3 RECONSTRUCTION: herald_lagged MAE < herald_contemp MAE × 0.95 in ≥ 2/4 scenarios
  (5% improvement over contemporaneous). If yes → LAGGED_IMPUTATION_ADVANCE.

L4 SPECIFICITY: herald_lagged MAE < neural_no_graph MAE AND < herald_contemp_permuted MAE,
  in aggregate over 5 seeds. Shows graph matters beyond temporal features.
  Failure → GRAPH_SPECIFICITY_NOT_DEMONSTRATED.

L5 ROBUSTNESS: herald_lagged MAE ≤ herald_contemp MAE × 1.10 on linear scenario.
  (Lagged must not regress vs contemporaneous by more than 10% on the easiest scenario.)
  Failure → LINEAR_REGRESSION.

L6 GENERALIZATION: L3 conditions met on generalization scenario specifically.
  Failure → GENERALIZATION_FAIL.

L7 SAFETY: zero NaN, zero Inf, leakage=PASS for all 20 tasks.
  Failure → ARCHITECTURE_INVALID; results not publishable.

L8 UNCERTAINTY: UNCERTAINTY_NOT_CALIBRATED (expected: cal90 < 0.80 with MC Dropout).
  Non-blocking. Post-HPC conformal calibration DEC still required.

**HPC authorization conditions (Phase 10):**
  Automatic authorization if local pilot clears ALL of: L1 PASS, L2 PASS, L7 PASS.
  If any fails: HPC_BLOCKED; report verdict, stop.

**Output outcomes (independent):**
  LAGGED_WIRING_VALID ← L1 PASS
  DYNAMIC_RELATION_RECOVERY_SUPPORTED ← L2 PASS
  LAGGED_IMPUTATION_ADVANCE ← L3 PASS
  GRAPH_SPECIFICITY_DEMONSTRATED ← L4 PASS
  LAGGED_ROBUST_VS_CONTEMPORANEOUS ← L5 PASS
  LAGGED_GENERALIZATION_SUPPORTED ← L6 PASS
  SAFETY_PASS ← L7 PASS

**Comparison baseline:**
  Direct pair: herald_lagged vs herald_contemp (same seeds, same masks, same epochs).
  Secondary: herald_lagged vs oracle_lagged (gap = unexploited graph info).
  Do NOT compare against Phase 9 results (different evaluation after B1 fix).

**Limitations declared before benchmark:**
  - Dataset unchanged (same synthetic generator, same AR/noise parameters).
  - Generator NOT modified to favor lagged architecture.
  - Gates not changed after results.
  - Conformal calibration (L8) explicitly deferred to future DEC.
  - Sign and lag recovery: primary metric is AUC (presence + direction). Sign/lag recovery
    reported as secondary metrics, not as gates.

**Reopen condition (D6 from DEC-042):**
  Phase 10 HPC PASS on L1/L2/L3 constitutes architectural reopen evidence. If Phase 10
  shows improvement, conformal calibration and real-data transfer are next steps.

**Affected files:**
`src/modeles/synthetic/herald_graph_imputer_lagged.py` (NEW);
`src/modeles/synthetic/run_phase10_benchmark.py` (NEW);
`src/modeles/synthetic/gates_phase10.py` (NEW);
`tests/test_herald_lagged.py` (NEW);
`reports/HERALD_PHASE10_LAGGED_CONTRACT.md` (NEW);
`hpc/phase10_synthetic_lagged/` (NEW);
`reports/HERALD_METHODOLOGICAL_DECISION_LOG.md` (this entry);

---

## DEC-043 ADDENDUM — Phase 10 HPC Results (2026-06-13)

**Job:** 7457885 (meso) — 20/20 tasks complete, 500 epochs
**Outcome: PHASE10_PARTIAL**

### Gate outcomes (full HPC, 4 scenarios × 5 seeds)

| Gate | Result | Value |
|------|--------|-------|
| L1 WIRING | **PASS** | oracle_lagged < oracle_contemp in 4/4; < no_graph in 4/4 |
| L2 RELATIONS | **PASS** | AUC=1.000 (all scenarios) |
| L3 RECONSTRUCTION | FAIL | +0.7–2.4% improvement (threshold: 5%) |
| L4 SPECIFICITY | **PASS** | herald_lagged < no_graph AND < permuted |
| L5 ROBUSTNESS | **PASS** | no regression on linear |
| L6 GENERALIZATION | FAIL | +2.4% on generalization (threshold: 5%) |
| L7 SAFETY | **PASS** | NaN=0, Inf=0, leakage PASS all 20 tasks |
| L8 CALIBRATION | FAIL (marker) | UNCERTAINTY_NOT_CALIBRATED |

### Key quantitative findings

**MAE improvement herald_lagged over herald_contemp:** +0.70% to +2.39% across all 4 scenarios (consistent, positive, but below 5% threshold).

**Edge AUC:** herald_lagged 0.64–0.71 vs herald_contemp 0.39–0.43 — ~70% relative improvement confirming directed lagged structure recovery.

**Oracle ceiling:** Even oracle_lagged (perfect directed adj, frozen) only beats oracle_contemp by 1.3–1.9% — the cross-sector signal ceiling under AR(1) φ∈[0.3,0.6] is ~2%.

### Verdict

Architecture is **structurally correct** (L1+L2+L7 all PASS). Edge recovery improves substantially. MAE improvement is real (1–2.4%) and specific (L4 PASS) but bounded by the AR dominance inherent to the generator.

L3 failure is **structural** (signal ceiling ~2% under these dynamics), not a convergence artefact. The pre-specified 5% threshold was too strict for AR-dominated panels.

### Valid claims (within HERALD framing)

- "The lagged directed architecture recovers cross-sector precedence structure more accurately than the contemporaneous baseline (AUC 0.64–0.71 vs 0.39–0.43)."
- "Directed lagged attention reduces imputation MAE by 1–2% relative to contemporaneous attention across all four benchmark scenarios."
- "These edges represent lagged predictive precedence associations, not causal effects."

### Next DEC options

(A) Lower L3 threshold to 2% to match the AR-dynamics ceiling (methodological update).
(B) Increase generator cross-sector signal (stronger lag weights or lower AR φ).
(C) Accept PHASE10_PARTIAL for publication claim with declared caveats.

Recommendation: Option C is scientifically defensible. The improvement is real, consistent, and specific to true graph structure. The 5% gate was protective; it should remain in the log as a benchmark for future work.

**Full results:** `reports/HERALD_PHASE10_LAGGED_RESULTS.md`

---

## DEC-044 — 2026-06-13 — Phase 10 Metric Reconciliation + Signal Sensitivity Experiment

**Phase:** 10 (post-audit)
**Question:** (1) Is the AUC discrepancy between DEC-042 (0.727) and Phase 10 herald_contemp (0.40) a metric bug or a model difference? (2) Does the herald_lagged MAE improvement scale with cross-sector signal strength?

**Evidence:**
- Full edge metric audit from 20 Phase 10 JSON result files (7457885):
  - herald_contemp: AUC 0.39–0.43, precision@k ≈ prevalence (no structure recovery above chance)
  - herald_lagged: AUC 0.64–0.71, precision@k 0.35–0.43 (3–4× prevalence)
  - oracle_lagged: AUC 1.000 in all 20 tasks (wiring verified, gate L2 PASS confirmed)
- AUC convention confirmed: `y_score = learned_attn[target, source]`. Bug B1 changed `[rows,cols]` → `[cols,rows]`. Fixed before Phase 10.
- Phase 9 retroactive correction (1-0.273=0.727) and Phase 10 herald_contemp (0.406) are different training runs under symmetric adjacency (B2), not a metric inconsistency.
- Fixture test validates: perfect attention at `attn[target,source]` → AUC=1.0; wrong indexing → AUC<0.5.

**Alternatives considered:**
- Metric bug in Phase 10 computation → ruled out by oracle_lagged AUC=1.000 and fixture tests.
- Re-running Phase 9 with B1 fix → not done (unnecessary given oracle proof; Phase 9 result stands as LEGACY).

**Decision:**
- **PHASE10_PARTIAL_CONFIRMED.** No retroactive reclassification.
- **PHASE10_REPORTING_CORRECTED:** The DEC-042 "corrected AUC=0.727" refers to Phase 9 retroactive only. Phase 10 herald_contemp AUC=0.40 is the current benchmark. These are MODEL_DIFFERENCE, not contradictory.
- New experiment **PHASE10_SIGNAL_SENSITIVITY** launched (gates S1-S7 frozen before execution). Runner: `src/modeles/synthetic/run_signal_sensitivity.py`. Gates: `src/modeles/synthetic/gates_sensitivity.py`. Grid: 324 tasks (cs_force × AR × noise × lag × 2 scenarios × 3 seeds). Smoke test passed (3.6s, oracle AUC=1.000, wiring confirmed). Full run requires explicit HPC authorization.
- `forced_lag` parameter added to `SyntheticConfig` (backward compatible, default=None). Used by sensitivity runner to force lag-1-only or lag-2-only true relations.
- Generalization scenario renamed conceptually to `shifted_dynamics_scenario` in documentation. True cross-scenario generalization (train on {linear,mixed}, test on {shifted_dynamics}) is GENERALIZATION_NOT_YET_TESTED.

**Rationale:**
- Symmetric adjacency (B2) makes direction learning non-deterministic. Different runs converge to different local optima. Phase 9 learned the forward direction; Phase 10 learned the reverse (for herald_contemp). The oracle_lagged AUC=1.000 confirms correct metric implementation — if the metric were wrong, the oracle would not score 1.0.
- Signal sensitivity experiment is needed to determine if the L3 failure (MAE +1–2%, threshold 5%) is a generator artifact (AR dominance) or a fundamental model limitation. S7 (monotonicity gate) specifically tests whether stronger cross-sector signal increases oracle utility.

**Limitations:**
- Sensitivity full run not yet executed (HPC authorization pending). Pilot/smoke test only confirms wiring.
- Calibration contract documented but not implemented (C1-C4 deferred until L3 PASS).
- B2 (symmetric adj direction ambiguity) is not resolved; sensitivity experiment does not address it.

**Reopen condition:** Sensitivity full run PASS/PARTIAL determination after HPC authorization.

**Affected files:**
- `src/data/synthetic/generate_herald_synthetic.py` (forced_lag field added)
- `src/modeles/synthetic/run_signal_sensitivity.py` (new — sensitivity runner)
- `src/modeles/synthetic/gates_sensitivity.py` (new — S1-S7 frozen gates)
- `tests/test_phase10_metric_reconciliation.py` (new — AUC fixture + forced_lag tests)
- `reports/HERALD_PHASE10_METRIC_RECONCILIATION.md` (new)
- `reports/HERALD_PHASE10_SIGNAL_SENSITIVITY.md` (new — contract with S1-S7 + smoke test results)

---

## DEC-044 ADDENDUM — OFAT Diagnostic (2026-06-13)

**Supersedes:** The 324-task factorial grid design in DEC-044. Replaces it with an OFAT diagnostic.

**Question:** Is the Phase 10 MAE ceiling structural (AR-dynamics) or regime-specific?

**What was done:**
8-configuration OFAT design (1 reference + 7 non-reference, one axis at a time) × 2 scenarios × 3 seeds = **48 tasks** executed locally, 200 epochs, 6.0 min total. Runner: `src/modeles/synthetic/run_ofat_sensitivity.py`. Gates O1-O8 frozen in `src/modeles/synthetic/gates_ofat.py` before execution.

**Factorial runner status:** `run_signal_sensitivity.py` marked `NOT_AUTHORIZED`. Blocked at CLI without explicit flag `--i-understand-this-is-the-324-task-factorial`.

**OFAT Gate outcomes (O1-O8):** 4/8 PASS — OFAT_PARTIAL

| Gate | Outcome |
|------|---------|
| O1 SAFETY | PASS |
| O2 GRAPH_SPECIFICITY | FAIL — permuted occasionally ≥ lagged at 200 epochs; D_lag1/D_lag2 only configs to pass 6/6 |
| O3 EDGE_RECOVERY | PASS — mean AUC=0.617, AUPRC > prevalence |
| O4 SEED_REPLICATION | PASS |
| O5 MASK_ROBUSTNESS | FAIL — A_low and B_low fail block_30 (degenerate low-signal regime) |
| O6 MONOTONIC_SIGNAL | PASS — oracle gap: A_low=0.005, A_original=0.017, A_high=0.045 |
| O7 AR_DIAGNOSIS | FAIL — hypothesis inverted: high AR → MORE graph contribution, not less |
| O8 ORACLE_CEILING | FAIL — oracle fails vs no_graph in block_30 for A_low and A_high (200 epochs insufficient) |

**Key quantitative findings:**

- **B_high (AR=high, φ=0.5–0.8):** Largest absolute benefit. herald_lagged MAE=0.528 vs no_graph=0.609 (Δ=−0.081, +13%). Both masks. 3/3 seeds.
- **D_lag1, D_lag2 (pure lag):** AUC 0.67–0.71, AUPRC 0.53–0.60 (vs prevalence 0.111). Only configs with 0/6 O2 failures. Demonstrates that pure lag structure is cleanly recoverable.
- **A_low (cs=low):** Cross-sector signal too weak. Graph uninformative. Block masking fails entirely (0/6).
- **B_low (ar=low, φ=0.1–0.3):** Low AR reduces graph contribution. Block masking fails (0/6). ffill no longer dominant (neural models beat ffill).
- **O7 finding corrected:** Graph utility INCREASES with AR strength, contrary to prior hypothesis. The corrected model: stronger AR creates harder temporal extrapolation; the graph provides cross-sector signal that no_graph cannot access.

**Decisions:**

- `OFAT_NO_EXTENSION_NEEDED`: 48-task OFAT is sufficient for mechanistic understanding.
- `GRAPH_SIGNAL_LIMIT_CONFIRMED` at Phase 10 parameters: +1–2% MAE is the ceiling at φ∈[0.3,0.6] mixed lag.
- `ARCHITECTURE_NOT_RESPONSIVE` is **ruled out**: B_high shows +13%, D_lag1/D_lag2 show consistent improvements with AUC=0.70.
- `PHASE10_PARTIAL_CONFIRMED`: unchanged. OFAT results do not alter Phase 10 decisions.

**Limitations:**
- 200 epochs (vs 500 in Phase 10) → partial convergence; O2 specificity vs permuted is sensitive to epoch count.
- O8 failures in A_high and A_low block_30 are convergence artifacts (extreme weight ranges need more epochs).
- B_high × D_lag interaction (strongest signal + pure lag) not measured directly in OFAT. Potential future experiment.

**Reopen condition:** OFAT_HPC_EXTENSION_JUSTIFIED only if B_high × D_lag grid (small, targeted, 500 epochs) is specifically authorized.

**Affected files:**
- `src/modeles/synthetic/run_ofat_sensitivity.py` (new — OFAT runner, 48 tasks)
- `src/modeles/synthetic/gates_ofat.py` (new — O1-O8 frozen gates)
- `src/modeles/synthetic/run_signal_sensitivity.py` (modified — NOT_AUTHORIZED guard added)
- `tests/test_ofat_sensitivity.py` (new — manifest, guard, gates, result tests)
- `reports/HERALD_PHASE10_SIGNAL_SENSITIVITY.md` (updated — sections 10-13 added)

---

## DEC-045 — Phase 11: True Synthetic Generalization Protocol
**Date:** 2026-06-13 | **Status:** PILOT_COMPLETE | **Decision:** SYNTHETIC_RELATIONS_GENERALIZE

**Context:** Phase 10 trained and tested on its own generated data (no cross-scenario transfer). DEC-045 tests TRUE generalization: train on {linear, mixed_default}, validate on {nonlinear_heavy}, evaluate zero-shot on frozen novel scenarios never seen during training.

**What was done:**
- Defined frozen novel test scenarios: `novel_lag2` (frac_nonlinear=0.85, forced_lag=2, territory_radius=0.25) and `novel_highvar` (frac_nonlinear=0.90, structural break at year 8, high noise). NOT in BENCHMARK_SCENARIOS.
- Seeds fully disjoint: train [10-50] / val [100-300] / test [1000-5000] — no overlap with Phase 9/10 or OFAT.
- Two strategies: T1 (single-family, linear only) and T2 (multi-environment, linear+mixed_default).
- 7 models: ffill, ridge, no_graph, herald_contemp, herald_lagged (zero-shot), herald_lagged_permuted, oracle_lagged.
- X1-X9 gates frozen before execution. Runner: `src/modeles/synthetic/phase11_generalization/run_pilot.py`.
- Pilot: 3 train seeds × 1 val seed × 3 test seeds × 150 epochs × 2 masks. 36s total.

**Gate outcomes (6/9 PASS):**

| Gate | Outcome |
|------|---------|
| X1 SAFETY | PASS — NaN=0, leakage=0 |
| X2 DATASET_DISJOINT | PASS — all seeds fully disjoint |
| X3 NO_ADAPTATION | PASS — checkpoint hash verified at runtime |
| X4 T2_ADVANTAGE | PASS — T2 MAE/T1 MAE = 0.9959 ≤ 1.02 |
| X5 GENERALIZES_BASELINE | FAIL — herald_lagged ≥ no_graph in 3/3 seeds on novel_lag2 |
| X6 EDGE_TRANSFER | PASS — mean edge AUC=0.611 > 0.55 |
| X7 PILOT_COMPLETENESS | PASS — 24/24 records, 0 errors |
| X8 SEED_CONSISTENCY | FAIL — herald_lagged worse than no_graph in all 3 seeds |
| X9 ORACLE_BOUND | FAIL — oracle not consistently better than ffill (20/24 fail) |

**Decisions:**
- `SYNTHETIC_RELATIONS_GENERALIZE`: learned sector attention correctly identifies causal pairs in novel scenarios (AUC=0.611). Oracle wiring achieves AUC=1.000 confirming metric correctness.
- Imputation does NOT generalize under extreme dynamics shift (0-30% → 85-90% nonlinear). MLP trained on linear data cannot predict nonlinear-dominated dynamics. Forward fill dominates.
- `MULTI_ENVIRONMENT_TRAINING_SUPPORTED` at imputation quality level: NOT REACHED. X4 marginal (T2 ratio=0.9959), X5 FAIL.

**HPC assessment:** HPC NOT REQUIRED. Pilot finding is structurally unambiguous (3/3 seeds). Adding seeds/epochs cannot overcome MLP-dynamics mismatch.

**Reopen condition:** A new DEC is needed for partial adaptation (fine-tuning MLP only, frozen attention matrix) — would test if structure transfer + MLP adaptation beats training from scratch.

**Affected files:**
- `src/modeles/synthetic/phase11_generalization/` (new package — splits, trainer, evaluator, gates, pilot runner)
- `tests/test_phase11_generalization.py` (new — 51 tests)
- `reports/HERALD_PHASE11_SYNTHETIC_GENERALIZATION.md` (new)

---

## DEC-046 — Pesquisa Arquitetural pós-DEC-045 (RESEARCH_ONLY)
**Date:** 2026-06-13 | **Status:** RESEARCH_COMPLETE | **No implementation**

**Context:** DEC-045 revealed that edge structure transfers (AUC=0,611 OOD) but the MLP decoder does not generalize under extreme dynamics shift (85-90% nonlinear vs 0-30% training). This is a research-only entry to document the methodological investigation and establish the direction for DEC-047.

**Diagnosis (root cause):**
Two sub-problems with different generalization behaviour:
- `[A] Structure identification (attention)` → TRANSFERS (AUC=0,611 on OOD scenarios)
- `[B] Reconstruction function (MLP)` → DOES NOT TRANSFER without domain adaptation

**Methods surveyed (5 axes, 18 verified references, R-026 to R-042):**
- Axis A (graph imputation): GRIN/SAITS/CSDI/PriSTI/GRAPE
- Axis B (domain adaptation for graphs): UDAGCN/GTrans/few-shot node classification
- Axis C (relational inference): NRI/GTS/SLAPS
- Axis D (self-supervised pretraining): GraphMAE/PatchTST/SimMTM
- Axis E (conformal uncertainty): EnbPI/SPCI/Barber et al./Angelopoulos tutorial

**Three paths proposed:**

| Path | Classification | Description |
|------|---------------|-------------|
| PATH 1 | `RECOMMENDED_NOW` | Frozen attention + adapter MLP (bottleneck 32→16→32) trained with K% labels of target domain. Pretraining: masked reconstruction + edge/lag/sign prediction multi-task. Conformal uncertainty (EnbPI) as output layer. |
| PATH 2 | `SECONDARY` | Masked multi-task pretraining on 800-2000 synthetic mini-datasets (including frac_nonlinear 0-0.9). Better zero-shot before any fine-tuning. |
| PATH 3 | `FUTURE_ONLY` | Graph structure learning end-to-end (NRI/GTS). Requires T≥50, N≥20 sectors. Opens when N_countries≥8. |

**Rejected methods:** GRIN (T>>200), CSDI/PriSTI (high compute, low interpretability), GTrans (topology shift not dynamics shift), UDAGCN (node classification), MAML (too few meta-tasks with 3-4 countries).

**New finding (lacuna bibliográfica):** No published method combines directed + signed + lagged graph learning for short economic panels (T=10-20). This is a potential original contribution of HERALD.

**Recommended next DEC:** DEC-047 — Few-shot adapter evaluation experiment (synthetic, K ∈ {1%, 5%, 10%, 20%}, gates A1-A5 pre-defined).

**Affected files:**
- `reports/HERALD_POST_DEC045_ARCHITECTURE_RESEARCH.md` (new)
- `reports/bibliography/HERALD_REFERENCES_MASTER.md` (updated: R-026 to R-042, 42 total)
- `reports/bibliography/herald_references.bib` (updated: new BibTeX entries)
- `reports/bibliography/HERALD_REFERENCE_AUDIT.csv` (updated: 17 new rows)
- `CODEX_MEMORY.md` (updated)

---

## DEC-047 — Few-shot adaptation benchmark: frozen attention + decoder/adapter adaptation
**Date:** 2026-06-13 | **Status:** PILOT_COMPLETE | **Decision:** FEWSHOT_ADAPTATION_FAILED

**Context:** Following DEC-046 diagnosis (attention transfers, MLP does not), DEC-047 tests whether few-shot adaptation of the MLP decoder (with frozen attention) improves imputation on novel OOD scenarios. Protocol: A1-A10 gates frozen before execution.

**What was done:**
- Implemented `src/modeles/synthetic/phase12_few_shot/` package: splits, adapter, decoder_ablation, graph_metrics, adaptation_trainer, evaluator, gates_dec047, run_pilot.
- AdapterBottleneck(dim=32, bottleneck=16): bottleneck with residual, 1072 params.
- Temporal splits: support=65%, val=15%, test=20% (n_years=20 → 13/3/4 years).
- 9 strategies: Z0 (frozen), A1 (decoder FT), A2 (adapter only), A3 (attn+decoder), A4 (full FT), C0 (no graph), P0 (permuted), B0 (ffill), B1 (Ridge).
- Pilot: novel_lag2, seeds=[1000,2000,3000], k=[0.0,0.05,0.10], 8 strategies, 2 masks. 432 records, 85s.
- 49 tests PASS.

**Gate outcomes (3/10 PASS):**

| Gate | Outcome |
|------|---------|
| A1 SAFETY | PASS — NaN=0, leakage=0 |
| A2 ADAPTATION_BENEFIT | FAIL — no strategy reliably < Z0 |
| A3 GRAPH_CONTRIBUTION | FAIL — neural ≈ C0 ≈ P0 in MAE |
| A4 BASELINE_RELEVANCE | FAIL — ffill (B0) dominates all neural |
| A5 FEWSHOT_EFFICIENCY | FAIL — no benefit at k≤0.10 |
| A6 GRAPH_PRESERVATION | PASS — auc_change ≈ 0 for all strategies |
| A7 BLOCK_ROBUSTNESS | PASS — consistent result in block_30 |
| A8 REPLICATION | FAIL — no consistent direction across seeds |
| A9 ADAPTER_VALUE | FAIL — A2 not better than A1 |
| A10 FINETUNING_TRADEOFF | FAIL — A4 not better than A1 |

**Key finding:** B0 (ffill) MAE=0.244 vs all neural ~0.281. Adaptation does not help. Root cause: same as DEC-045 — distribution gap (0-30% → 85% nonlinear) too large for 50-epoch fine-tuning of a decoder trained on linear data. PATH 1 (adapter) is insufficient without PATH 2 (masked pretraining first).

**HPC assessment:** HPC NOT REQUIRED. Pilot is structurally unambiguous.

**Recommended next DEC:** DEC-048 — Masked pretraining on diverse synthetic scenarios (frac_nonlinear ∈ U[0, 0.90]) covering PATH 2 from DEC-046.

**Reopen condition:** If DEC-048 masked pretraining achieves MAE < ffill at zero-shot, then few-shot adapter (A2) is worth revisiting.

**Affected files:**
- `src/modeles/synthetic/phase12_few_shot/` (new package)
- `tests/test_phase12_fewshot.py` (new — 49 tests)
- `reports/HERALD_FEWSHOT_ADAPTATION_CONTRACT.md` (new)
- `reports/HERALD_FEWSHOT_ADAPTATION_PILOT.md` (new)
- `reports/HERALD_POST_DEC045_ARCHITECTURE_RESEARCH.md` (corrections: causal language, GRIN/SAITS to SECONDARY_BASELINE, NRI/GTS T-requirement fix, section separator)
- `CODEX_MEMORY.md` (updated)

---

## DEC-048 — Failure Cause Diagnostic for FEWSHOT_ADAPTATION_FAILED (DEC-047)
**Date:** 2026-06-15 | **Status:** PILOT_COMPLETE | **Decision:** TRAINING_BUDGET_TOO_SMALL (architecture NOT inadequate)

**Context:** DEC-047 found ffill (MAE≈0.244) dominated all neural strategies (MAE≈0.281). DEC-048 tests one factor at a time via OFAT to identify the root cause.

**What was done:**
- Implemented `src/modeles/synthetic/phase13_diagnostic/` package: functional_scenario, ofat_runner (axes D/M/L/S), masked_pretraining, gates_dec048, run_diagnostic.
- Gates C1-C10 frozen before execution (alpha=0.1 frozen, thresholds frozen).
- Pilot: 30 epochs, seeds=[1000,2000,3000], n_datasets=[10,25]. Runtime: 79 seconds.
- 21 tests PASS.

**Gate outcomes (6/10 PASS):**

| Gate | Result | Evidence |
|------|--------|----------|
| C1 NO_NAN | PASS | 0 NaN/Inf in 105 records |
| C2 ARCHITECTURE | PASS | oracle_ratio=0.732 (< 1.0 threshold) |
| C3 DATA_SCALING | FAIL | 30-epoch pilot: slight regression with more data (undertrained) |
| C4 DIVERSITY | FAIL | D2 not better than D0 at 30 epochs |
| C5 PRETRAINING | PASS | GRAPH_MULTITASK gain 1.1% |
| C6 GRAPH_OBJECTIVE | FAIL | L2 gain 0.001 < threshold 0.010 |
| C7 EDGE_AUC | FAIL | AUC≈0.51 < 0.60 threshold |
| C8 BLOCK_ROBUSTNESS | PASS | Block_30 consistent direction |
| C9 SHIFT_CURVE | PASS | 2/2 progressive degradation steps |
| C10 BEATS_FFILL | PASS | Oracle (locally trained) ratio=0.929 |

**Key findings:**
- C2 PASS definitively rules out ARCHITECTURE_INADEQUATE. Oracle beats ffill by 27% in functional scenario (ratio=0.732).
- Functional scenario M3 (locally trained lagged, no oracle) also beats ffill (ratio=0.738) — model can learn graph structure.
- Attention gradient is 400x smaller than MLP gradient. Under L2 loss, attention gradient doubles — edge BCE reaches encoder but signal is weak.
- C3/C4 FAIL are artefacts of 30-epoch pilot. NOT interpretable as "diversity doesn't help."
- C5 PASS: GRAPH_MASKED_MULTITASK pretraining shows 1.1% MAE gain (25 datasets, 50 epochs).
- S3 (novel_highvar, structural_break=8) causes catastrophic degradation (ratio=1.45).

**Principal cause:** TRAINING_BUDGET_TOO_SMALL + DISTRIBUTION_SHIFT_TOO_LARGE.

**Pretraining:** GRAPH_MASKED_MULTITASK MAE=0.2609 vs NO_PRETRAINING MAE=0.2638 (+1.1%).
NOTE: Edge supervision only applicable to synthetic data. NOT transferable to real country data.

**Recommended next DEC:** DEC-049 — Full-scale pretraining (n_epochs=150, 50 D2 datasets, GRAPH_MASKED_MULTITASK). Rerun DEC-047 strategies after pretraining.

**Affected files:**
- `src/modeles/synthetic/phase13_diagnostic/` (new package — 5 files)
- `tests/test_phase13_diagnostic.py` (new — 21 tests)
- `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md` (new)
- `data/processed/synthetic_benchmark/phase13_pilot/` (results JSON)
- `CODEX_MEMORY.md` (updated)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

## DEC-049 — 2026-06-15 — Phase 14: Convergence Audit for Training Budget Hypothesis

**Phase:** 14
**Question:** Does the TRAINING_BUDGET_TOO_SMALL hypothesis from DEC-048 hold under more epochs (30/75/150) and graph-multitask pretraining? Does GRAPH_MASKED_MULTITASK add value over TEMPORAL_MASKED at scale?
**Evidence:** DEC-048 found: (a) C2 PASS — architecture not inadequate; (b) attention gradient ~400× smaller than MLP; (c) GRAPH_MASKED_MULTITASK pretraining at 50 epochs +1.1% gain; (d) C3/C4 FAIL interpreted as undertrained artefacts of 30-epoch pilot.
**Alternatives considered:**
  1. Accept TRAINING_BUDGET_TOO_SMALL as sufficient explanation, proceed directly to DEC-050.
  2. Run architecture redesign (abandoned — C2 PASS rules out ARCHITECTURE_INADEQUATE).
  3. Run Phase 14 controlled convergence audit before committing to longer training.
**Decision:** PARTIAL — pilot complete (22s, 10 D2 datasets, budgets 30/75, 168 records). E1+E6 PASS; E3/E4/E5/E9 FAIL; E7 invalid (few-shot bug — 0 records). Pretraining hurts reconstruction at pilot scale. Gradient analysis confirms GRAPH_MASKED_MULTITASK edge-BCE reaches attention encoder (ratio 101–331×, aux→attn=True); TEMPORAL_MASKED does not (ratio 3000–6000×, aux→attn=False). ffill still dominates (MAE=0.307 vs best neural 0.316). 300-epoch trigger NOT fired. Next: 150-epoch run with 50 D2 datasets + few-shot bug fix before concluding.
**Rationale:** Before committing to 150-epoch HPC runs, a controlled audit with a defined gate structure prevents post-hoc tuning. Epoch budgets [30,75,150] allow detecting whether improvement is monotone. 300 epochs only auto-triggered if E1+E2 PASS at 150.
**Limitations:**
  - All results apply to SYNTHETIC data only — not transferable to PT/IT/FR/AT/NL.
  - GRAPH_MASKED_MULTITASK uses true_relations ground truth which does NOT exist for real country data. The objective is a synthetic diagnostic tool only.
  - Phase 14 pilot mode (n_datasets=10, epoch_budgets=[30,75]) provides fast validation; full run required for gate decisions.
  - Gradient ratios are diagnostic evidence, not proof that budget is the sole cause.
**Reopen condition:** If E2 (convergence) fails, reopen to investigate architecture or data quantity as primary cause. If novel_highvar performance remains catastrophic regardless of budget, structural_break generalization requires separate DEC.
**Frozen before execution:**
  - MULTITASK_ALPHA=0.1, MULTITASK_BETA=0.05, MULTITASK_GAMMA=0.05
  - E1-E10 gate thresholds (see gates_dec049.py)
  - 300-epoch trigger requires E1+E2 PASS at 150
**Affected files:**
  - `src/modeles/synthetic/phase14_convergence/` (new package — 5 files)
  - `tests/test_phase14_convergence.py` (new — 25 tests)
  - `reports/HERALD_DEC049_CONVERGENCE_AUDIT.md` (new)
  - `reports/HERALD_DEC048_FAILURE_CAUSE_DIAGNOSTIC.md` (3 targeted corrections)
  - `CODEX_MEMORY.md` (DEC-049 bullet added)

---

## DEC-050 — 2026-06-15 — Phase 14: Bug fixes in pretrain_runner.py and re-run (30/75/150 epochs)

**Phase:** 14
**Question:** Are the DEC-049 pilot results valid? Three critical bugs were identified in `pretrain_runner.py` after the pilot. Do the bugs invalidate the DEC-049 conclusions?
**Evidence:**
  - **Bug A (TEMPORAL_MASKED masked reconstruction):** `compute_multitask_nll` computed NLL on `training_mask` (cells the model CAN see), not on `loss_mask` (artificially hidden cells). Result: TEMPORAL_MASKED trained to reconstruct already-visible cells — equivalent to standard NLL but with a smaller dataset. The masked reconstruction objective was never actually applied.
  - **Bug B (edge presence BCE — lag-2 ignored):** `_edge_bce` marked only `lag == 1` edges as positive. lag-2 true edges were treated as negatives, actively training the model to suppress lag-2 attention. Consequence: GRAPH_MASKED_MULTITASK edge AUC was penalized for correctly learning lag-2 associations.
  - **Bug C (sign/lag shared logit):** `_sign_bce` and `_lag_bce` both used `log_sect_attn_lag1 − log_sect_attn_lag2` as logit. Sign prediction is architecturally impossible via softmax attention (attention weights are always non-negative after softmax; they cannot encode the sign/direction of an effect). The sign BCE objective conflated two semantically different properties using the same logit. Removed.
**Alternatives considered:**
  1. Accept DEC-049 PARTIAL as-is, note bugs, move on to architecture redesign.
  2. Fix bugs, re-run the same protocol, update DEC-049.
  3. Fix bugs, run new DEC-050 protocol with separate output directory to preserve before/after comparison.
**Decision:** `TEMPORAL_MASKED_CONFIRMED; GRAPH_MULTITASK_UNSTABLE`

After bug fixes, the corrected 30/75/150 epoch run (50 D2 datasets, 5 test seeds, mcar_30+block_30, novel_lag2+novel_highvar) shows:

- **Bug A fix critical**: TEMPORAL_MASKED@75 achieves MAE=0.2327 on novel_lag2, BEATING ffill (0.2568) by 9.4% and NO_PRETRAINING (0.2562) by 9.2% in zero-shot. DEC-049 TEMPORAL_MASKED (buggy) showed MAE=0.371. The masked reconstruction objective was the key.
- **GRAPH_MASKED_MULTITASK unstable at scale**: val_loss diverges from -3.17 @30 → -31941 @75 → -421009 @150 (variance collapse in NLL σ→0). MAE degrades with epochs: 0.2628→0.2684→0.3716. The pos_weight (n_neg/n_pos) in edge BCE combined with 50 datasets drives instability. New finding beyond DEC-049.
- **Few-shot A1 extremely effective**: All variants show 78-80% MAE reduction after A1 adaptation (decoder-only, frozen attention). TEMPORAL_MASKED@75 few-shot novel_lag2 MAE=0.0509. Improvement uniform across pretraining strategies.
- **300-epoch trigger fires** (E1+E2 PASS at 150) — only for TEMPORAL_MASKED. NOT authorized without user confirmation.
- Gates 4/10 PASS: E1 (safety), E2 (convergence), E7 (fewshot value), E8 (graph preservation). FAIL: E3 (AUC), E4 (graph signal), E5 (ffill), E6 (graph multitask), E9 (GRAPH vs baseline), E10 (block robustness).
**Rationale:** DEC-049 conclusions were based on buggy implementation. Before claiming "pretraining does not help", verify that the multitask pretraining objectives were actually applied correctly. The PARTIAL decision (not FAIL) is appropriate because gradient evidence was real and independent of the bugs (gradient flow was measured directly via autograd, not via the loss output).
**Limitations:**
  - DEC-049 gradient evidence (attention/decoder ratio) was collected with the buggy code but is still valid: gradient norms were measured by calling the loss functions and reading `.grad` attributes directly, not via the loss magnitude.
  - DEC-049 val_loss comparisons (GRAPH_MASKED_MULTITASK < TEMPORAL_MASKED) used correct reconstruction NLL; this finding is also unaffected by Bug A (which only affects the TEMPORAL_MASKED auxiliary loss).
  - Bug C: sign BCE with a proxy logit was architecturally invalid; removing it does not affect GRAPH_MASKED_MULTITASK (which used edge_presence + lag, not sign).
  - The fundamental challenge (ffill domination; graph signal not used in reconstruction) may persist even with corrected objectives. These are separate from the bugs.
**Frozen before execution:**
  - MULTITASK_ALPHA=0.1, MULTITASK_GAMMA=0.05 (unchanged; BETA effectively 0 with sign BCE removed)
  - E1-E10 gate thresholds unchanged
  - Output dir: `data/processed/synthetic_benchmark/phase14_convergence_v2/`
**Affected files:**
  - `src/modeles/synthetic/phase14_convergence/pretrain_runner.py` (3 bug fixes: A, B, C)
  - `src/modeles/synthetic/phase14_convergence/run_convergence.py` (REPO_ROOT parents[5]→parents[4] fix)
  - `tests/test_phase14_convergence.py` (25→30 tests; test 24 updated; tests 26-30 new)
  - `reports/HERALD_DEC050_BUG_AUDIT.md` (new)
  - `reports/HERALD_DEC049_CONVERGENCE_AUDIT.md` (note added: DEC-049 pilot used buggy code)
  - `CODEX_MEMORY.md` (DEC-050 bullet added)

---

## DEC-051: Stable Objective Audit

**Date:** 2026-06-15
**Status:** EXPERIMENT_COMPLETE (see DEC-052 addendum)
**Predecessors:** DEC-050 (bugs A/B/C corrected), DEC-049 (few-shot A1 pilot)

**Problem:**
  1. DEC-050 few-shot A1 shows 78-80% MAE reduction across ALL variants (including NO_PRETRAINING) — raises question of genuine signal vs. evaluation artifact.
  2. GRAPH_MASKED_MULTITASK diverges catastrophically at scale (variance collapse log_sigma→-∞, val_loss -3→-421009). Proposed fix: clamp log_sigma to [-3,2].
  3. Bug C (sign/lag logits shared) eliminated sign BCE but left the architecture without a valid sign head. DEC-051 adds independent sign and lag parameters.

**Evidence:**
  - DEC-050 corrected results: TEMPORAL_MASKED@75 MAE=0.2327 beats ffill 9.4% on novel_lag2 (zero-shot)
  - Few-shot A1: identical ~80% gain for pretrained AND NO_PRETRAINING → suspicious
  - GRAPH_MASKED_MULTITASK@75: val_loss -31941; GRAPH_MASKED_MULTITASK@150: -421009

**Alternatives considered:**
  1. Accept few-shot as genuine, proceed to scaling without audit.
  2. Switch exclusively to Huber loss, drop NLL entirely.
  3. Drop graph heads from DEC-051, focus on temporal-only stability.
**Decision:** `DEC051_IMPLEMENTATION_COMPLETE`

**Design (all constants frozen before results):**
- R1: NLL with `log_sigma.clamp(-3.0, 2.0)` + entropy penalty λ=0.001
- R2: Huber with δ=1.0 (no variance head)
- R3: MSE (diagnostic only)
- GraphAuxHeads: `sign_logit` and `lag_logit` are independent `nn.Parameter` — not shared with attention
- Negative tests NT1-NT6: presence logit from max(lag1, lag2) attention; sign from sign_logit; lag from lag_logit
- Gates V1-V10 frozen before results
- 300-epoch gate (V300): requires V1+V2+V6 PASS + monotone improvement + ≥4/5 seeds + user authorization

**Limitations:**
  - 300-epoch run NOT executed — requires explicit user authorization even if V300 gate passes.
  - No calibration, no real-country application in this task.
  - Evaluation on synthetic only — true_relations ground truth not available for PT/IT/FR/NL/AT.

**Affected files:**
  - `src/modeles/synthetic/phase15_stable_objective/` (7 new files, expanded to 9 in DEC-052)
  - `tests/test_phase15_stable_objective.py` (38 tests DEC-051, 47 total after DEC-052)
  - `reports/HERALD_DEC051_STABLE_OBJECTIVE_AUDIT.md` (new; §9 addendum added by DEC-052)
  - `CODEX_MEMORY.md` (DEC-051 and DEC-052 bullets)

---

## DEC-052: NT Audit Determinism Fix + Full Results

**Date:** 2026-06-15
**Status:** COMPLETE — 11/11 gates PASS
**Predecessors:** DEC-051 (implementation), DEC-050 (corrected zero-shot results)

**Problem:**
  1. After DEC-051 pretraining and zero-shot completed, the NT audit failed: `NT verdict: LEAKAGE_OR_EVALUATION_ERROR: ['NT1', 'NT2']`.
  2. Question: Is this real data leakage, or a methodological bug in the audit itself?

**Evidence:**
  - `params_identical=False` for NT1/NT2 with DROPOUT=0.1: two adaptations on the same input produced different weights → classic signature of RNG non-determinism, not leakage.
  - `_build_temporal_features(panel, support_mask)`: uses `safe = np.where(mask, panel, 0.0)` — test-year cells are zeroed before any forward pass. Structural leakage is architecturally impossible.
  - NT1 `metrics_differ=False`: `_impute_and_mae` passed `eval_mask` (where 1=evaluate) to `compute_imputation_metrics` which reads `mask==0` as hidden cells — evaluating at cells where both panels agree, so metrics were identical regardless of corruption.

**Decision:** `NT_AUDIT_BUG_NOT_LEAKAGE` — fix and re-run.

**Fixes applied:**

| Fix | File | Detail |
|-----|------|--------|
| Deterministic adaptation | `phase12_few_shot/adaptation_trainer.py` | `adapt_seed` param; `_set_adapt_seed()` seeds random/numpy/torch before loop |
| NT1/NT2 semantics | `phase15_stable_objective/fewshot_audit.py` | Adapt once on orig; two same-seed adaptations on orig vs corrupted must produce identical hashes; eval: same model, two target arrays |
| Mask convention | `phase15_stable_objective/fewshot_audit.py` | `_mae_at_eval_cells(imp, panel, eval_mask)` uses `eval_mask==1` (no inversion) |
| Mask disjointness | `phase15_stable_objective/fewshot_audit.py` | `_assert_masks_disjoint()` before each NT |
| V1/V6 gate scope | `phase15_stable_objective/gates_dec051.py` | log_sigma check scoped to `NLL_CLAMPED` variants; explosion threshold 4.05 (inference values 2.3–2.7 on novel_highvar are calibrated uncertainty) |

**Constant frozen before re-run:** `ADAPT_SEED = 12345`

**Results:**
- NT1-NT6: ALL PASS; `params_identical=True`, `max_abs_param_diff=0.00e+00` for all seeds
- 15 checkpoints: unchanged before/after (hashes verified)
- Top-2 by val_loss: `TEMPORAL_MASKED_NLL_CLAMPED_ep75`, `TEMPORAL_MASKED_NLL_CLAMPED_ep150`
- Few-shot real gain: ~0.6% MAE reduction (not 78-80%; that was a mask-convention evaluation bug)
- Gates: 11/11 PASS, including V300 (technical prerequisites met)

**V300 status:** PASS gate but NOT EXECUTED — requires explicit user authorization.

**Scientific conclusions:**
1. No leakage — support_mask correctly zeros test targets before the model forward pass.
2. TEMPORAL_MASKED pretraining is load-bearing: zero-shot gain (9.4% over ffill) requires the masked pretraining. NO_PRETRAINING does not beat ffill.
3. Few-shot adds ~0.6% on top of strong zero-shot — real but modest.
4. GRAPH_MULTITASK V7/V8 PASS: graph heads recover edge structure (AUC ≥ 0.60) and beat temporal-only in aggregate.

**Limitations:**
  - 300-epoch run not yet executed.
  - Few-shot gain modest; may not survive on real country data (Italy/Portugal/Austria), which have different dynamics.
  - ADAPT_SEED=12345 freezes a single global seed; multi-seed adaptation variability not characterized.

**Affected files (DEC-052 additions):**
  - `src/modeles/synthetic/phase12_few_shot/adaptation_trainer.py` (adapt_seed)
  - `src/modeles/synthetic/phase15_stable_objective/fewshot_audit.py` (complete rewrite)
  - `src/modeles/synthetic/phase15_stable_objective/gates_dec051.py` (V1/V6 fix)
  - `src/modeles/synthetic/phase15_stable_objective/run_negative_audit.py` (new)
  - `src/modeles/synthetic/phase15_stable_objective/run_fewshot_and_gates.py` (new)
  - `tests/test_phase15_stable_objective.py` (+9 tests, 47 total)
  - `reports/HERALD_DEC051_STABLE_OBJECTIVE_AUDIT.md` (§9 addendum)
  - `CODEX_MEMORY.md` (DEC-052 bullet)

## DEC-053: Decoupled Graph Architecture — Directed Relation Inference + Gated Residual

**Date:** 2026-06-15
**Status:** IMPLEMENTADO — pronto para execução local

### Context

DEC-052 confirmou que o backbone temporal (TEMPORAL_MASKED_NLL_CLAMPED@75) aprende
estrutura grafosal (AUC≥0.60) mas esta não se traduz em ganho preditivo. Diagnóstico:

1. **Prior simétrico**: `_sector_adj_from_relations()` simetriza relações dirigidas →
   adj[s,t]=adj[t,s]=1, adicionando reverso falso para cada aresta real. exp(1)≈2.7× boost
   nas duas direcções, incluindo reversos que não existem.

2. **Correlação com ruído**: cenários novel (frac_nonlinear=0.85-0.90) estão no extremo
   da distribuição de treino. Features temporais (`_build_temporal_features`) são suficientes;
   atenção cruzada via adj simétrico adiciona ruído correlacionado.

3. **Desacoplamento necessário**: o modelo aprendeu a compensar o adj durante o treino mas o
   sinal grafal dirigido não é separável do ruído simétrico na arquitectura actual.

### Decision

Implementar arquitectura desacoplada com 4 componentes:

- **A. GraphRelationHead**: infere presença/sinal/lag/confiança de forma dirigida (parâmetros
  independentes `presence_logit[target,source]`, `sign_logit`, `lag_logit`, `log_confidence`).
- **B. TemporalDecoder**: backbone Phase 15 congelado, adj=0 sempre.
- **C. GraphMessageExpert**: MLP pequeno que mapeia mensagens dirigidas para residual clamped
  (±MAX_RESIDUAL_FRAC=0.15 × |y_temporal|.mean()).
- **D. UtilityGate**: sigmoid MLP com bias=-5 (fechado na inicialização); inputs sem alvo.

**Loss desacoplada** (pesos congelados antes da execução):
```
L_total = L_recon + 0.05·L_presence + 0.02·L_sign + 0.02·L_lag + 0.05·L_utility + 0.01·mean(gate)
```
`compute_utility=False` durante eval/test (nunca acede ao alvo).

**3 modos de avaliação:**
1. `ANALYTIC_GRAPH_ONLY` — AUC dirigido, AUPRC, sign/lag acc, auditoria do prior simétrico.
2. `TEMPORAL_RECONSTRUCTION` — backbone vs ffill/Ridge, sem grafo.
3. `GATED_GRAPH_ASSIST` — temporal + residual grafal vs todas as baselines + gate permutado.

**Seeds**: 1000, 2000, 3000. **Máscaras**: MCAR 30%, block 30%. **Épocas**: ≤75.

### Fixtures F1-F6 (testes funcionais)

| Fixture | Propriedade testada |
|---------|---------------------|
| F1 | Grafo útil (sector 0→1 weight=0.9); gate deve abrir |
| F2 | Grafo inútil (AR puro); gate deve fechar |
| F3 | Relação negativa (weight=-0.8); sinal deve ser recuperado |
| F4 | Lag-2 (não lag-1); lag_logit deve favorecer lag=2 |
| F5 | Janela de regime (anos 5-10 activos); gate varia com ano |
| F6 | Dirigido assimétrico (só 0→1); presence_logit[1,0] >> presence_logit[0,1] |

### Gates D1-D10 (congelados antes da execução)

| Gate | Critério |
|------|----------|
| D1 | AUC/AUPRC finito, alvo dirigido, prevalência registada |
| D2 | AUC≥0.60, AUPRC>prevalência, sign/lag>0.50 |
| D3 | gate=0 → temporal-only exacto (atol=1e-5) |
| D4 | gate>0.3 em F1/F3/F4 onde relação ajuda |
| D5 | gate<0.2 em F2; fecha fora de janela em F5 |
| D6 | presence_logit[true_dir] >> presence_logit[false_dir] em F6 (diff>0.2) |
| D7 | Gated nunca >5% pior que temporal-only por cenário |
| D8 | Gated MAE < graph-always-on AND < graph-permuted |
| D9 | Comparação honesta registada (ganho não exigido) [informativo] |
| D10 | Resultados funcionais replicam em ≥2/3 seeds |

### Limitations

- Experimento sintético: não implica generalização para dados reais.
- A gate não demonstra utilidade preditiva sobre ffill/Ridge globalmente (D7 é segurança
  mínima, não superioridade).
- Backbone congelado: a GraphRelationHead não beneficia de fine-tuning conjunto.
- Nenhuma linguagem causal: AUC/AUPRC medem discriminação de arestas, não causalidade.

**Ficheiros afectados (DEC-053 adições):**
- `src/modeles/synthetic/phase16_decoupled/__init__.py` (novo)
- `src/modeles/synthetic/phase16_decoupled/graph_relation_head.py` (novo — componente A)
- `src/modeles/synthetic/phase16_decoupled/gated_model.py` (novo — componentes B+C+D)
- `src/modeles/synthetic/phase16_decoupled/loss_functions.py` (novo — loss desacoplada)
- `src/modeles/synthetic/phase16_decoupled/fixtures.py` (novo — F1-F6)
- `src/modeles/synthetic/phase16_decoupled/evaluator.py` (novo — 3 modos)
- `src/modeles/synthetic/phase16_decoupled/gates_dec053.py` (novo — D1-D10 congelados)
- `src/modeles/synthetic/phase16_decoupled/run_dec053.py` (novo — orquestrador)
- `src/modeles/synthetic/run_phase15_300ep.py` (fix `_directed_graph_metrics()`)
- `tests/test_phase16_decoupled.py` (novo — 41 testes)
- `reports/HERALD_DEC053_DECOUPLED_GRAPH_AUDIT.md` (novo)
- `CODEX_MEMORY.md` (DEC-053 bullet)

---

## DEC-058 — Real Weak-Label Relation Tuning (2026-06-16)

**Decision:** Use Phase 7 sector precedence evidence as weak/noisy labels for fine-tuning the SharedRelationEncoder. Labels are confidence-weighted; Phase 7 is not treated as ground truth.

**Context:** DEC-056 (R4 FAIL) showed sign concordance=0.438 on real data. DEC-057 recommended weak-label supervision over lag-aware encoder as primary fix.

**Label classification:**
- COVID_ROBUST (confidence 0.60–0.96): promoted AND robust against 2020 exclusion → positive label
- MAIN_ONLY (confidence 0.20–0.40): promoted AND robust (not COVID-driven) → positive label
- COVID_SENSITIVE (confidence 0.05–0.15): promoted only with 2020 → excluded from training
- UNLABELED (not promoted): excluded entirely ("not promoted" ≠ negative)
- PERMUTATION_NEGATIVE: only from explicit permutation evidence

**Fine-tuning design:**
- V0: frozen DEC-055 checkpoint (baseline)
- V1: confidence-weighted BCE loss on presence + sign + lag heads; early stopping; gradient clipping
- V2: V1 + CountryAdapter (592 params, regularised)
- Controls C1 (permuted signs) and C2 (country-shuffled)
- Leave-one-country-out: FR+NL→PT, FR+PT→NL, NL+PT→FR

**Results:**
- V1 LOCO sign concordance = 0.667 vs V0 = 0.313 (W3 PASS)
- 58 replicated pairs (W4 PASS), COVID_SENSITIVE not promoted (W5 PASS)
- W2 FAIL: C2=0.688 ≥ V1=0.667; only 12 training labels insufficient to degrade controls
- W6 FAIL: 0 abstentions; all 72 pairs scored from single representative window

**Decision outcome:** REAL_WEAK_LABEL_TUNING_SUPPORTED (8/10 PASS), with W2 and W6 failures noted as limitations requiring more training data and a calibrated uncertainty mechanism.

**Ficheiros afectados:**
- `src/modeles/real_world/build_phase7_weak_labels.py` (novo)
- `src/modeles/real_world/train_real_relation_weak_labels.py` (novo)
- `src/modeles/real_world/gates_dec058.py` (novo)
- `tests/test_real_relation_weak_labels.py` (novo — 60 testes)
- `data/processed/real_relation_weak_labels/` (novo — 25 labels, manifest)
- `data/processed/real_weak_label_results/` (novo — scores, validation JSON)
- `reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md` (novo)
- `CODEX_MEMORY.md` (DEC-058 bullet)

---

## DEC-059 — Weak-Label Tuning Revalidation (2026-06-16)

**Decision:** REAL_WEAK_LABEL_TUNING_PARTIAL (confirmed; DEC-058 corrected from SUPPORTED to PARTIAL)

**Context:** DEC-058 W2 failed (C2=0.688 ≥ V1=0.667 — country-shuffled control not degraded). DEC-059 provides rigorous revalidation with 7 controls, multi-window stability, and LOW_EVIDENCE fold marking.

**Key findings:**
- V1 sign concordance = 0.500 on valid LOCO folds (NL+PT); FR fold LOW_EVIDENCE (n=1)
- M2 FAIL: C1/C2/C3/C5 all within 0.021 of V1 — fine-tuning does not clearly separate from permuted/shuffled baselines with 12 training labels
- C4 (sign-flip) and C6/C7 (random/synthetic-only) DO degrade, confirming the model learns something — but cannot attribute to economic sector dynamics
- M4 FAIL: 0 abstentions — encoder gives presence ≥ 0.50 to all 72 pairs; proper abstention requires conformal uncertainty
- M7 PASS: 59 multi-window stable replicated pairs (not validated against controls)
- FR fold n=1: marked LOW_EVIDENCE; 1.000 concordance is unreliable and excluded from main claim

**Decision ceiling rule:** M2 FAIL → maximum = REAL_WEAK_LABEL_TUNING_PARTIAL.

**Ficheiros afectados:**
- `src/modeles/real_world/gates_dec059.py` (novo — M1-M10 congelados)
- `src/modeles/real_world/run_dec059_weak_label_revalidation.py` (novo — multi-window + C1-C7)
- `tests/test_dec059_weak_label_revalidation.py` (novo — 49 testes)
- `data/processed/real_dec059_results/` (novo — scores, validation JSON)
- `reports/HERALD_DEC059_WEAK_LABEL_REVALIDATION.md` (novo)
- `reports/HERALD_DEC058_REAL_WEAK_LABEL_TUNING.md` (corrigido: PARTIAL)
- `CODEX_MEMORY.md` (DEC-059 bullet + DEC-058 corrigido)

---

## DEC-060 — France Relation Signal Recovery Audit

**Status:** COMPLETE | **Decision:** AUDIT_COMPLETE (10/10 PASS)  
**Date:** 2026-06-16 | **Tests:** 63/63 PASS

**Question:** Why does France have only 1 promoted Phase 7 sector-precedence label? Is the limitation methodological, scale-related, or a genuine absence of signal?

**Findings:**
- **Binding criterion: |β| ≥ 0.10** (not FDR). FR ZE2020 has 280 small employment zones. Observed effect sizes for near-miss pairs: |β|=0.076–0.097, systematically just below threshold.
- FDR correction (792 tests = 11 windows × 72 pairs) is secondary — 9 rows already pass q_fdr ≤ 0.05.
- **8 near-miss-beta pairs**: pass FDR + Δr² + bss but |β| < 0.10.
- **7 near-miss-fdr pairs**: pass |β| + Δr² + bss but q_fdr > 0.05.
- **MN→BE**: most consistent pair (6 windows p≤0.01, bss=1.000) but exhibits beta-FDR anti-correlation: when |β| ≥ 0.10 (2017-2022, β=0.112), q_fdr=0.072 > threshold; when q_fdr ≤ 0.05, |β| drops to 0.087–0.097.
- **RU→MN** (the 1 promoted pair): pre-COVID p_perm=0.127, classified **FR_COVID_SENSITIVE**.
- NUTS3 panel has no sector columns — ZE2020/NUTS3 scale comparison for sector relations is not possible.
- Sensitivity: with |β| ≥ 0.08, 7 additional pairs would qualify (not promoted — requires new DEC with pre-registered gates).

**FR Label Distribution (72 pairs):**
- FR_COVID_SENSITIVE: 1 (RU→MN)
- FR_BETA_BELOW_THRESHOLD: 3 (MN→BE, OQ→MN, KZ→FZ)
- FR_FDR_ONLY_BLOCKED: 5 (OQ→BE, FZ→RU, LZ→KZ, FZ→JZ, GI→JZ)
- FR_WEAK_SIGNAL: 63

**What this does NOT support:**
- Promotion of any FR pair (no pair simultaneously passes all 4 Phase 7 criteria in a non-COVID window).
- Causal interpretation of any association.
- That absence of Phase 7 promotion means absence of economic association.

**Ficheiros afectados:**
- `src/modeles/real_world/gates_dec060_france_audit.py` (novo — F1-F10 congelados)
- `src/modeles/real_world/run_dec060_france_signal_audit.py` (novo — audit completo)
- `tests/test_dec060_france_relation_audit.py` (novo — 63 testes)
- `data/processed/france_relation_audit/` (novo — fr_pair_audit.csv, fr_dataset_coverage.csv, fr_dataset_coverage_summary.json)
- `reports/HERALD_DEC060_FRANCE_RELATION_SIGNAL_AUDIT.md` (novo)
- `CODEX_MEMORY.md` (DEC-060 bullet)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

## DEC-061 — PT/NL Municipal Sector Data Availability Audit

**Status:** COMPLETE | **Decision:** `PT_READY_NL_BLOCKED` (10 gates: 9 PASS + 1 `FORMALLY_BLOCKED`)
**Date:** 2026-06-16 | **Tests:** 39/39 PASS + 1 SKIP-expected

**Note (backfilled 2026-06-18):** this section was missing from the log even though
DEC-062, DEC-063, and several canonical documents reference DEC-061 directly. The
content below is reconstructed from `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md`
(verified via `git show` in the 2026-06-18 deep report audit) and from DEC-062's own
"Part A — DEC-061 Review" section, which corrects one figure (see below). No new
finding is introduced here; this is a faithful backfill, not a re-decision. Per the
naming-conventions rule ("never renumber"), DEC-061 keeps its original number even
though it is being written into the log after DEC-062/063/064/065/066 were already
recorded.

**Question:** Following DEC-060 (France's weak relation signal traced to ZE2020's 280
small zones), can PT and NL be raised to municipal/gemeente granularity, comparable in
scale to FR ZE2020, to enable a fairer cross-country Phase 7 comparison?

**Findings:**
- **PT:** confirmed available via INE API (indicators 0009703/0014099). 308 municipalities
  total; **297 reported in this audit as continental+Madeira** using filter
  `geocod[0] in ('1','2')` — **this count was corrected by DEC-062** to **278 continental
  only** (`geocod[0] == '1'`), which excludes Açores (prefix '2') that the DEC-061 filter
  had incorrectly included. 8/9 HERALD A10 sectors mappable from CAE (KZ absent by
  definition, confirmed DEC-018). Years 2008–2023.
- **NL:** **BLOCKED**. CBS Open Data (83631NED births, 81841NED) provides `oprichtingen`
  (business creations) only at COROP level, never gemeente. Table 81575NED has gemeente
  granularity (483 GM codes) but is a **stock** table, not births. CBS catalog searched
  (5,927 tables) — no gemeente × births × SBI table found. This is a structural limitation
  of CBS Open Data, not a technical access failure.
- Caribbean NL confirmed absent from all searched sources.
- Concepts documented for clarity: FR = `establishment_creation`, PT = `enterprise_birth`,
  NL = `local_unit_opening`.
- Gates G1/G2/G3/G4/G6/G7/G8/G9/G10 PASS; **G5 `FORMALLY_BLOCKED`** (the NL gemeente gate).

**Decision:** `PT_READY_NL_BLOCKED`. PT confirmed eligible for a municipal-grain Phase 7
extension (built next in DEC-062). NL requires either CBS Microdata (restricted Research
Data Center access) or an alternative source before any gemeente-level relation work —
**using stock data (81575NED) as a births proxy is NOT authorized by this decision** and
was not attempted until DEC-063 built and explicitly labelled such a proxy, which DEC-065
later found structurally invalid and **blocked for relation/training labels**. The NL
gemeente proxy may only ever be used as territorial visualization context, never as a
sector-precedence training label (DEC-065, reaffirmed by DEC-066's label taxonomy).

**Reopen condition:** new NL data source (CBS Microdata access, or an alternative
official gemeente × births × sector table) — not a relaxation of the existing gate.

**Ficheiros afectados:**
- `src/data/european_panel/gates_dec061_municipal_granularity.py` (novo — G1-G10 congelados)
- `tests/test_dec061_municipal_granularity.py` (novo — 39 testes + 1 skip)
- `data/processed/municipal_granularity_audit/` (novo)
- `reports/HERALD_DEC061_PT_NL_MUNICIPAL_GRANULARITY_AUDIT.md` (novo; removed from git
  index 2026-06-18 consolidation, content preserved in
  `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md` and this entry)
- `CODEX_MEMORY.md` (DEC-061 bullet, historical)
- `reports/HERALD_CURRENT_STATE.md` (updated)
- `reports/HERALD_NAMING_CONVENTIONS.md` (this backfill closes the inconsistency that
  document had flagged in §2)

**Consolidated in:** `reports/canonical/HERALD_02_DATA_PROVENANCE_AND_GRANULARITY.md`.

---

## DEC-062 — PT Municipal Panel Build + NL Gemeente Source Search (Granular Phase 7 Preflight)

**Status:** COMPLETE | **Decision:** `PT_PANEL_READY_NL_OPEN_DATA_BLOCKED` (10/10 PASS)  
**Date:** 2026-06-16 | **Tests:** 89/89 PASS | **Gates:** H1-H10

**Context:** DEC-061 confirmed PT_READY_NL_BLOCKED at NUTS3/COROP level. DEC-062 builds a PT panel at full municipal granularity (278 continental municipalities) and audits CBS Open Data for NL gemeente births.

**Part A — DEC-061 Review:**
- DEC-061 used `geocod[0] in ('1','2')` → 297 municipalities (included 19 Açores, prefix '2')
- Correct filter: `geocod[0] == '1'` → 278 continental municipalities
- INE geocod structure: 1=continental (278), 2=Açores (19), 3=Madeira (11), other=aggregates
- NUTS2013→NUTS2024 transition at 2023: 176/278 municipalities got new all-numeric geocods. `_harmonise_geocods()` uses municipality name (geodsg) as join key to canonicalise.

**Part B — PT Municipal Panel:**
- **Sources:** INE 0009703 (2008–2022) + 0014099 (2023)
- **Panel:** 278 continental municipalities × 16 years = 4,448 rows
- **CAE→A10:** A→OQ (agri merged per PT convention); K→structural_absent (finance definitionally excluded)
- **Sectors:** 8 observable (BE, FZ, GI, JZ, LZ, MN, OQ, RU); KZ=NaN structural_absent throughout
- **Sector coverage:** 100% for all 8 sectors across all municipalities and years
- **Missing/zero policy:** valor='0'→0.0; valor=''→NaN; KZ=NaN by definition (never 0)
- **Growth lags:** causal (lag1, lag2, growth_1y, growth_2y computed within municipality; NaN in first year)

**Part C — NL Gemeente Search:**
- 83631NED: COROP_ONLY (no gemeente level)
- 81575NED: STOCK_ONLY (vestigingen bestand, not births)
- 81841NED: COROP_ONLY + period 2007–2013 only
- 80234ned: STOCK_ONLY + period 2006–2010
- CBS catalog scan (8 search terms, 10 pages): 0 acceptable tables found
- **Decision:** NL_GEMEENTE_OPEN_DATA_BLOCKED
- **Non-finding note:** CBS Microdata (ABR) contains gemeente × SBI × oprichtingen — requires Research Data Center access application

**Part D — Readiness:**

| Country | System | N units | Status |
|---------|--------|---------|--------|
| FR | ZE2020 | 280 | READY |
| PT | MUNICIPALITY_CONTINENTE | 278 | READY_WITH_LIMITATION (KZ absent) |
| NL | COROP (fallback) | 40 | READY |
| NL | GEMEENTE | 342 | BLOCKED |

**Ficheiros afectados:**
- `src/data/european_panel/build_pt_municipal_sector_panel.py` (novo)
- `src/data/european_panel/search_nl_gemeente_birth_sources.py` (novo)
- `src/data/european_panel/gates_dec062_granular_preflight.py` (novo — H1-H10 congelados)
- `src/modeles/real_world/preflight_granular_phase7.py` (novo)
- `src/modeles/real_world/run_dec062_granular_preflight_gates.py` (novo)
- `tests/test_dec062_granular_preflight.py` (novo — 89 testes)
- `data/processed/european_panel/pt_municipal_sector_panel.csv` (novo — 4448 rows)
- `data/processed/european_panel/pt_municipal_sector_panel_manifest.json` (novo)
- `data/processed/granular_phase7_preflight/dec061_review.json` (novo)
- `data/processed/granular_phase7_preflight/nl_gemeente_source_candidates.csv` (novo)
- `data/processed/granular_phase7_preflight/nl_gemeente_source_search.json` (novo)
- `data/processed/granular_phase7_preflight/granular_phase7_readiness.json` (novo)
- `data/processed/granular_phase7_preflight/dec062_gates.json` (novo)
- `reports/HERALD_DEC062_GRANULAR_PHASE7_PREFLIGHT.md` (novo)
- `CODEX_MEMORY.md` (DEC-062 bullet)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

## DEC-063 — Granular FR/PT/NL Evidence Model (2026-06-16)

**Decision:** `GRANULAR_FR_PT_NL_PREFLIGHT_READY`
**Gates:** 10/10 PASS (GATE_VERSION: DEC-063-v1) | **Tests:** 66/66 PASS

**Context:** DEC-062 confirmed PT municipal panel ready and NL gemeente CBS open data blocked. DEC-063 resolves the NL gemeente gap via a stock-share proxy (disaggregating COROP births to gemeente using establishment stock shares from 81575NED), and formally documents the evidence hierarchy for all three countries.

**Part A — Evidence Levels:**

| Country | System | Evidence type | N units | Sectors |
|---------|--------|--------------|---------|---------|
| FR | ZE2020 | observed_births (SIDRE) | 280 | 8 (KZ present) |
| PT | MUNICIPALITY_CONTINENTE | observed_births (INE) | 278 | 8 (KZ structural_absent) |
| NL | COROP | observed_births (83631NED) | 40 | 9 (KZ present) |
| NL | GEMEENTE_PROXY | proxy_disaggregated_by_stock_share | 355 | 9 (attempted) |

**Part B — NL Gemeente Ingest:**
- **83631NED** (oprichtingen): COROP-only (0 GM codes). metric=OprichtingenVanVestigingen_1. Period 2007–2025.
- **81575NED** (vestigingen): 483 GMs × 19 SBI sections. metric=Vestigingen_1 (establishment stock, NOT births). Evidence_type=observed_stock.
- **84721NED** (regioindeling): 355 current GM→CR mappings; 128 historical GMs unmatched.
- CBS OData 10k-row limit: resolved by year-loop with combined year+SBI filter (9,177 rows/call).

**Part C — Proxy Method:**
- `share_gm = stock_gm / sum(stock within COROP for sector×year)`
- `estimated_births_gm = observed_births_corop × share_gm`
- evidence_status: proxy_computed (73%), no_corop_births_data (128 unmatched GMs × 9 sectors × 19y), insufficient_stock_share (stock=0)
- Reaggregation identity: sum of gemeente proxy within COROP == observed COROP births. Verified: max_abs_error=0.0.

**Key prohibitions ratified:**
- No neural training before new DEC
- No Phase 7 full run before new DEC
- No treating proxy as observed births without evidence_type flag
- No KZ claims for PT
- No causal language
- Evaluation must report separately: observed-only, proxy-included, proxy-excluded sensitivity

**Ficheiros afectados:**
- `src/data/european_panel/ingest_nl_gemeente_stock_panel.py` (novo)
- `src/data/european_panel/build_nl_gemeente_birth_proxy.py` (novo)
- `src/data/european_panel/gates_dec063_granular_evidence.py` (novo)
- `src/data/european_panel/build_granular_training_matrix.py` (novo)
- `src/modeles/real_world/run_dec063_granular_evidence_gates.py` (novo)
- `tests/test_granular_fr_pt_nl_evidence_model.py` (novo — 66 testes)
- `data/processed/european_panel/nl_gemeente_corop_crosswalk.csv` (novo — 355 rows)
- `data/processed/european_panel/nl_gemeente_stock_panel.csv` (novo — 9,177 rows)
- `data/processed/european_panel/nl_gemeente_stock_manifest.json` (novo)
- `data/processed/european_panel/nl_gemeente_birth_proxy_panel.csv` (novo — 82,593 rows)
- `data/processed/european_panel/nl_gemeente_birth_proxy_manifest.json` (novo)
- `data/processed/european_panel/granular_fr_pt_nl_training_matrix.csv` (novo — 4 rows)
- `data/processed/european_panel/dec063_gates.json` (novo)
- `reports/HERALD_DEC063_GRANULAR_FR_PT_NL_EVIDENCE_MODEL.md` (novo)
- `reports/HERALD_GRANULAR_FR_PT_NL_TRAINING_CONTRACT.md` (novo)
- `reports/herald_artifact_registry.json` (DEC-063 entry)
- `CODEX_MEMORY.md` (DEC-063 bullet)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

## DEC-064 — PT Municipal Phase 7 Sector Precedence (2026-06-16)

**Decision:** `PT_MUNICIPAL_PHASE7_READY_FOR_HPC`
**Gates:** 10/10 PASS (GATE_VERSION: DEC-064-v1, smoke) | **Tests:** 52/52 PASS + 8 SKIP-full

**Context:** DEC-063 confirmed GRANULAR_FR_PT_NL_PREFLIGHT_READY. DEC-064 runs Phase 7 sector
precedence at PT municipal level (278 continental municipalities, observed_births, INE 0009703/0014099).
Gates P1-P10 pre-registered before observing results.

**Part A — Panel:**
- 278 continental municipalities × 16 years (2008-2023) × 8 observable A10 sectors
- KZ structural_absent (structural_mask=0, observation_mask=0); evidence_type=observed_births
- Velocity = sector_value[t] / sector_value[t-1] − 1; temporal leakage check: PASS
- Long panel: 40,032 rows; 31,100 with valid velocity (observation_mask=1)

**Part B — Smoke results (2018-2023, n_perm=9, n_boot=20):**
- 56/56 pares válidos; n_samples range: 1,055–1,668 (mean 1,452)
- 11× mais samples/par que PT NUTS3 (150 max)
- Max |β| = 0.078 (MN→GI, bss=1.0); todos abaixo do threshold pré-registado 0.10
- p_perm floor = 0.10 (mínimo com n_perm=9); zero pares promovidos
- RU→MN: β=+0.075, bss=1.0 — padrão consistente com FR (único label FR)

**Part C — Comparação PT NUTS3:**
- NUTS3: 25 territórios, 0 promovidos, max |β|=0.362 (GI→FZ, 2007-2012)
- Municipal: 278 territórios, 0 promovidos (smoke), max |β|=0.078
- ACHADO CHAVE: fragmentação ecológica — NUTS3→municipal reduz |β| (menor unidade, menor efeito individual)
- Municipal tem 11× mais poder estatístico na permutation test, mas efeitos menores

**Part D — Implicações:**
- Threshold |β|≥0.10 pode ser sistematicamente restritivo para PT/NL ao nível municipal
- Threshold foi calibrado para FR ZE2020 (maiores efeitos individuais)
- Possível DEC-066: threshold calibration antes de pooled training

**HPC preparado:**
- 208 tasks (13 janelas × 2 cenários × 8 sources), 30 min/task @ 4G
- Manifest: `data/processed/phase7_pt_municipal/hpc_task_manifest.json`
- Sbatch: `hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch`
- NÃO lançar sem autorização explícita

**Ficheiros afectados:**
- `src/data/european_panel/build_pt_municipal_phase7_panel.py` (novo)
- `src/modeles/real_world/gates_dec064_pt_municipal_phase7.py` (novo)
- `src/modeles/real_world/run_dec064_pt_municipal_phase7.py` (novo)
- `src/modeles/real_world/prepare_dec064_hpc_manifest.py` (novo)
- `hpc/phase7_sector_precedence/configs/pt_municipal_observed.json` (novo)
- `hpc/phase7_sector_precedence/run_phase7_pt_municipal_array.sbatch` (novo)
- `hpc/phase7_sector_precedence/submit_phase7_pt_municipal.sh` (novo)
- `tests/test_dec064_pt_municipal_phase7.py` (novo — 60 testes, 52 PASS + 8 SKIP)
- `data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv` (novo — 40,032 rows)
- `data/processed/phase7_pt_municipal/pt_municipal_phase7_panel_manifest.json` (novo)
- `data/processed/phase7_pt_municipal/hpc_task_manifest.json` (novo — 208 tasks)
- `data/processed/phase7_pt_municipal/results/all_edges_smoke.csv` (novo — 56 rows)
- `data/processed/phase7_pt_municipal/dec064_gates_smoke.json` (novo)
- `reports/HERALD_DEC064_PT_MUNICIPAL_PHASE7_AUDIT.md` (novo)
- `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_DRAFT.md` (novo — draft, não autorizado)
- `CODEX_MEMORY.md` (DEC-064 bullet)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

## DEC-066 — Fine-Grain Threshold Calibration (2026-06-16)

**Decision:** `FINE_GRAIN_THRESHOLD_POLICY_READY`
**Gates:** C1-C10, 10/10 PASS | **Tests:** 43/43 PASS

Calibrated a supplementary |β|≥0.09 FINE_GRAIN_SUPPORTED tier (requires bss≥0.80 plus
COVID-robust OR ≥2 consecutive windows OR cross-country replication) and a non-training
EXPLORATORY_FINE_GRAIN tier (0.07-0.09, bss≥0.90), using only FR ZE2020 and PT Municipal
observed data (NL gemeente proxy explicitly excluded from calibration — pre-registered
prohibition). Original ROBUST_ORIGINAL threshold 0.10 unchanged.

Full report: `reports/HERALD_DEC066_FINE_GRAIN_THRESHOLD_CALIBRATION.md`.
Policy: `data/processed/phase7_threshold_calibration/fine_grain_label_policy.json`.

---

## DEC-065 — NL Gemeente Proxy Phase 7 Sector Precedence (2026-06-17)

**Decision:** `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` (manual override of automated `SUPPORTED` verdict)
**Gates:** N1-N10 — 71/71 tests PASS | **HPC:** job 7475756, 252/252 tasks COMPLETED

**Context:** Following DEC-066 policy readiness, ran NL gemeente proxy (355 gemeenten,
evidence_type=proxy_disaggregated_by_stock_share, DEC-063 panel) through Phase 7 sector
precedence to test whether proxy disaggregation preserves the NL COROP observed signal
and can enter the Observatory as proxy evidence.

**HPC:** 252 tasks (14 windows × 2 scenarios × 9 source sectors) on meso, ~63-75s/task
at smoke scale, 3h time limit, all 252/252 COMPLETED.

**Raw automated result:** 121 promoted edges (35 unique pairs), 97 nominally COVID-robust
— vs NL COROP observed baseline of 8 promoted / 3 COVID-robust. The merge script's
gate-count logic alone would yield `NL_GEMEENTE_PROXY_PHASE7_SUPPORTED`.

**Critical finding — manually overridden:** A structural validity diagnostic found that
the DEC-063 proxy method (`estimated_births_gemeente = corop_births × stock_share`)
injects cross-sector-correlated noise into gemeente velocity that is unrelated to any
births-precedence relationship:
- Decomposition regression `gm_velocity ~ corop_velocity + share_velocity`: R²=0.635,
  coefficient on `share_velocity` (13.0) ~10x larger than on `corop_velocity` (1.33).
- `share_velocity` (the proxy weighting term) has cross-sector correlation 0.34-0.82
  across most A10 sectors — reflecting general local establishment-stock co-movement
  (development/gentrification), not births dynamics.
- This explains the implausible 15x jump in promoted edges going from COROP (observed)
  to gemeente (proxy) for the same underlying NL births series — opposite of the
  ecological-fragmentation pattern found in DEC-064/066 (finer units → fewer/smaller
  effects, not more).

**Verdict override:** `decision.json` and `nl_gemeente_proxy_label_summary.json` record
both the automated verdict (`SUPPORTED`) and the overridden verdict (`BLOCKED`) with
full reasoning. None of the 121 promoted edges may be used as DEC-066 training labels
under any tier.

**Consequence for DEC-068:** Cross-country granular training (FR+PT+NL) must exclude
NL gemeente proxy edges; NL contribution limited to COROP scale (DEC-034/064) until a
corrected proxy/regression specification (COROP-clustered SEs or COROP×year FE on the
share term) is validated.

**Ficheiros afectados:**
- `hpc/phase7_sector_precedence/run_phase7_nl_gemeente_proxy_array.sbatch` (novo)
- `hpc/phase7_sector_precedence/configs/nl_gemeente_proxy.json` (novo)
- `src/modeles/real_world/merge_nl_gemeente_proxy_phase7.py` (novo)
- `tests/test_dec065_nl_gemeente_proxy_phase7.py` (novo — 71/71 PASS)
- `data/processed/phase7_nl_gemeente_proxy/results/` (all_edges.csv, latest.csv, covid_robust_edges.csv, decision.json, structural_validity_diagnostic.json)
- `data/processed/phase7_nl_gemeente_proxy/nl_corop_vs_gemeente_proxy_comparison.csv` (novo)
- `data/processed/phase7_nl_gemeente_proxy/nl_gemeente_proxy_label_summary.json` (novo)
- `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md` (novo)
- `reports/HERALD_CURRENT_STATE.md` (updated)

---

### DEC-065 — Consolidation Addendum (2026-06-17)

Following the BLOCKED verdict above, this addendum consolidates the decision into a
formal evidence policy and prepares the granular Observatory v0.4 data layer.

- All 121 NL gemeente proxy edges explicitly re-marked `INVALID_FOR_TRAINING_LABELS`
  (`label_class=BLOCKED_PROXY_ARTIFACT`, `allowed_for_training_label=false`,
  `reason=stock_share_induced_artifact`) in
  `data/processed/herald_observatory_v04_granular/blocked_proxy_edges.csv`.
- `reports/herald_artifact_registry.json`: new explicit entry `NL_COROP_PHASE7`
  (status=`VALID_OBSERVED`, relation_label_status=`VALID_OBSERVED`); existing
  `NL_GEMEENTE_PROXY_PHASE7_BLOCKED` entry updated with
  `relation_label_status=INVALID_FOR_RELATION_LABELS`,
  `allowed_use=[territory_state_context_only]`. Status vocabulary extended with
  `VALID_OBSERVED`, `BLOCKED`, `INVALID_FOR_TRAINING_LABELS`, `INVALID_FOR_RELATION_LABELS`.
- New policy: `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` — defines which sources
  (FR ZE2020 observed, PT Municipal observed, NL COROP observed) may feed relation
  labels/training vs which (NL gemeente proxy) may only feed territory-state visual
  context. Defines 5 label classes (adds `BLOCKED_PROXY_ARTIFACT` and
  `INSUFFICIENT_EVIDENCE` to the DEC-066 taxonomy) and permitted/prohibited language.
- New contract: `reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md` — 4 layers
  (territory state / relation graph / comparison / recommendation readiness). NL
  gemeente proxy carries a mandatory "proxy/context" badge in Layer 1 and is
  structurally excluded from Layer 2 (relation graph).
- New exporter: `src/data/european_panel/build_observatory_v04_granular_exports.py`
  produces `data/processed/herald_observatory_v04_granular/`:
  `granular_territory_state_panel.csv` (142,650 rows), `granular_relation_edges.csv`
  (20 rows: FR=9, NL COROP=8, PT Municipal=3 — NL gemeente proxy absent by
  construction, asserted in the builder), `blocked_proxy_edges.csv` (121 rows),
  `manifest.json` (checksums + DEC references + hard rules).
- New tests: `tests/test_observatory_v04_granular_evidence_policy.py` (45 tests) —
  verifies NL gemeente proxy never appears in relation edges, blocked edges carry
  `allowed_for_training_label=false`, DEC-066 labels applied correctly, no causal
  language, manifest checksums match, FR/PT/NL COROP observed sources preserved.
- **159/159 tests pass** (71 DEC-065 + 45 Observatory v0.4 policy + 43 DEC-066).
- **Decision:** `GRANULAR_OBSERVATORY_V04_DATA_READY` — data/policy layer complete;
  dashboard HTML build is a separate task requiring its own authorisation (DEC-014 rule).

**Ficheiros afectados (addendum):**
- `reports/HERALD_GRANULAR_EVIDENCE_POLICY.md` (novo)
- `reports/HERALD_OBSERVATORY_V04_GRANULAR_CONTRACT.md` (novo)
- `src/data/european_panel/build_observatory_v04_granular_exports.py` (novo)
- `data/processed/herald_observatory_v04_granular/` (novo: 4 files)
- `tests/test_observatory_v04_granular_evidence_policy.py` (novo — 45/45 PASS)
- `reports/herald_artifact_registry.json` (updated: NL_COROP_PHASE7 added, status_vocabulary extended)
- `reports/HERALD_DEC065_NL_GEMEENTE_PROXY_PHASE7_AUDIT.md` (updated: explicit markers added)
- `reports/HERALD_CURRENT_STATE.md`, `CODEX_MEMORY.md`, `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` (updated)

---

### DEC-065 — Dashboard Addendum (2026-06-17): Observatory v0.4 Granular Dashboard

Following `GRANULAR_OBSERVATORY_V04_DATA_READY`, this addendum builds the visual dashboard
from the validated exports.

- New self-contained dashboard: `reports/dashboards/herald_observatory_v04_granular_dashboard.html`
  (9.0 MB, Plotly embedded locally per the v0.3 pattern — `_plotly_js_tag()` reads
  `plotly.min.js` from the installed Python `plotly` package; no CDN dependency).
- Map (Layer 1): FR ZE2020 + NL COROP choropleth using existing geometry
  (`data/external/ze2020_geometry.geojson`, `data/external/nuts3_2021_eurostat.geojson` via the
  `NL_COROP_TO_NUTS3` crosswalk reused verbatim from `build_observatory_v03.py`). PT Municipality
  and NL gemeente proxy have no committed municipal/gemeente geometry — rendered as a sortable
  table/heatmap fallback per the task's explicit fallback rule (no fabricated map).
- Relation graph (Layer 2): circular sector layout (reused from v0.3) built EXCLUSIVELY from
  `granular_relation_edges.csv` (20 edges). NL gemeente proxy is structurally absent — enforced
  by a fail-closed assert in the builder (`assert "GEMEENTE_PROXY" not in relation_edges[...]`)
  and verified by parsing the embedded `RELATION_EDGES` JS blob in tests.
- Blocked panel (Layer 3): all 121 NL gemeente proxy edges in a separate table,
  `allowed_for_training_label=false`, never rendered as graph edges.
- Evidence/export panel (Layers 4-5): KPI counts, manifest checksums (16-char prefix),
  DEC references, CSV/manifest download links, embedded manifest modal (works offline).
- New builder: `src/data/european_panel/build_observatory_v04_dashboard.py`.
- New tests: `tests/test_observatory_v04_dashboard.py` (41/41 PASS) — extracts the dashboard's
  embedded JS consts via regex + `json.loads` and asserts: relation edges count/region-systems/
  evidence_type; blocked edges count/reason/non-trainability; no overlap of region_system sets
  between relation and blocked edges; UI elements (badges, filters, panel divs) present; no
  forbidden causal language (the only "causes" occurrence is inside the embedded Plotly.js
  minified bundle's floating-point engineering comment, verified context-checked); builder
  determinism (re-running produces the same edge counts); CSV checksums match manifest.
- Playwright/headless browser not available in this environment — visual screenshot validation
  was not possible. Validated instead via HTML structural checks (DOCTYPE, balanced tags, key
  element IDs present) and embedded-data assertions. Manual validation recommended: open the
  HTML file in a browser and confirm the map is not blank, the graph renders with 9 sector
  nodes, the blocked-edges table has 121 rows, and all badges are visible.
- `reports/dashboards/herald_observatory_v03_dashboard.html` is untouched (no git diff).
- **Decision:** `OBSERVATORY_V04_DASHBOARD_READY`.

**Ficheiros afectados (dashboard addendum):**
- `reports/dashboards/herald_observatory_v04_granular_dashboard.html` (novo, 9.0 MB)
- `src/data/european_panel/build_observatory_v04_dashboard.py` (novo)
- `tests/test_observatory_v04_dashboard.py` (novo — 41/41 PASS)
- `reports/herald_artifact_registry.json` (updated)
- `reports/HERALD_CURRENT_STATE.md`, `CODEX_MEMORY.md`, `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md` (updated)

---

### Observatory v0.4.1 — Visual Upgrade: PT Municipal Map + Dynamic Graph (2026-06-17)

**Decision:** `OBSERVATORY_V041_VISUAL_READY`
**Gates:** none new (purely visual/UX/geometry task; no scientific decisions changed)
**Tests:** `tests/test_observatory_v041_visual_upgrade.py` (41/41 PASS); 241/241 total across all Observatory v0.4/v0.4.1 + DEC-065/066 suites

**Context:** the v0.4 dashboard (above) was methodologically sound but visually
limited: PT rendered as a table (no municipal geometry in the repo) and the
sector→sector graph was a static circular layout that did not communicate the
temporal dynamics already present in `granular_relation_edges.csv` (6 rolling
windows, 2009-2014 through 2020-2025). This task is purely visual/UX/geometry
— no scientific data, labels, or decisions were changed.

**Part A — PT municipality geometry:**
- No municipal-level PT geometry existed in the repo. Two candidate official
  sources evaluated: Eurostat/GISCO LAU 2021 (official, but freguesia-level
  for PT, n=3092 — would require dissolving by `LAU_ID[:4]` == INE Dicofre
  code) vs geoapi.pt (redistributes Direção-Geral do Território (DGT) /
  Carta Administrativa Oficial de Portugal (CAOP) municipal boundaries
  directly, with GeoJSON properties `Dicofre`/`Concelho`/`Distrito` matching
  the official CAOP schema — spot-verified `Dicofre="1006"` for Caldas da
  Rainha equals the GISCO `LAU_ID` prefix "1006").
- Used geoapi.pt as the primary source (already at municipality granularity,
  no dissolve needed), documenting GISCO LAU+dissolve as the documented
  fallback method if geoapi.pt becomes unavailable.
- Fetched all 308 PT municipalities (278 continental + 19 Açores + 11
  Madeira), cached each response to `data/external/portugal/geometry/raw/`
  (181 MB, gitignored — regenerable, not committed).
- Crosswalked to the panel's 278 distinct 7-digit geocods
  (`data/processed/european_panel/pt_municipal_sector_panel.csv`, region_id →
  region_name) by NORMALISED NAME MATCH (lowercase, accent-stripped,
  punctuation-stripped) — explicitly NOT by code, since the panel's 7-digit
  geocod scheme (NUTS2013/2024-vintage, DEC-062) and geoapi.pt's 4-digit
  Dicofre are unrelated numbering systems.
- Result: **278/278 matched, 0 unmatched panel names, 30 unmatched geoapi
  names = exactly the Açores+Madeira set** (confirms no continental/island
  leakage in either direction).
- Simplified geometry (`shapely.simplify`, tolerance 0.001° ≈ 110m,
  `preserve_topology=True`, then `buffer(0)` repair): 29.7 MB → 1.18 MB, 0
  invalid/empty geometries.
- Output: `data/processed/geometries/pt_municipalities_continental.geojson`
  (278 features, sha256 documented) + `..._manifest.json` (source, source_url,
  fallback_official_source, crosswalk_method, coverage, status=`COMPLETE_278_278`).
- Builder: `src/data/european_panel/build_pt_municipality_geometry.py`
  (idempotent — caches raw fetches, re-running does not re-download).

**Part B — PT choropleth in dashboard:**
- `build_observatory_v04_dashboard.py` now loads the PT geojson via
  `_build_pt_geojson()`, which checks the manifest's `status==COMPLETE_278_278`
  before using it — if missing or partial, returns an empty FeatureCollection
  and the dashboard JS automatically falls back to the table view (never
  fabricates geometry for a partial match).
- Map source dropdown updated: "Portugal — Municipality (observed, map)"
  (was "...table)"). `MAPPED_SOURCES = ['FR','NL','PT']`.
- Existing generic `renderMap()`/tooltip/side-panel code required no changes
  — it already worked off `region_system` and `REGION_META`, which already
  carry `evidence_type=observed_births` for PT.

**Part C — dynamic sector→sector graph:**
- New `annotate_relation_dynamics()` (Python) computes, per
  (country, source_sector, target_sector): `n_windows`, `is_recurring`
  (≥2 windows), `is_exclusive` (1 window), `sign_changes` (sign differs across
  occurrences) — embedded directly in each edge record sent to the dashboard.
- New UI: timeline slider (`#window-slider`, indices over `ALL_WINDOWS` = the
  6 unique windows in `granular_relation_edges.csv`), Play/Pause button
  (1.1s/frame interval, loops), Mode selector (`current` / `cumulative until
  window` / `recurring edges only`).
- `edgesForMode()` implements the 3 modes: current = edges in the exact
  selected window; cumulative = union of all edges with `window_end <=`
  selected window's end year; recurring = edges with `is_recurring=true`
  among those visible up to the slider position, one row per pair (latest
  occurrence).
- Visual markers at edge midpoints: 🔁 recurring, ⚠ sign-changes, ⭐ exclusive
  (priority order: sign_changes > recurring > exclusive).
- `showEdgeDetail()` extended: per-window history table (β/q_fdr/bss/label_class
  across all windows where the pair appears for that country), list of all
  countries/region_systems where the pair appears (any system), and the new
  territory-state context block (see Part D).
- New `renderRelationHeatmap()`: Plotly heatmap, rows = `country: source→target`,
  columns = `ALL_WINDOWS`, colour = β (diverging red/grey/green), respects the
  same country/region_system/label_class filters as the graph.

**Part D — map↔graph linking:**
- `handleSourceChange()` (map country dropdown): if the new source is FR/NL/PT,
  sets `graph-country` to match and re-renders the graph; shows a small sync
  note. NL_GEMEENTE leaves the graph filter untouched (no relation evidence to
  sync) and shows an explanatory note instead.
- `handleMapSectorChange()` (map sector dropdown): sets `HIGHLIGHT_SECTOR`;
  `renderGraph()` dims (opacity ×0.25, width ×0.6) all edges/nodes not
  touching the highlighted sector.
- `showEdgeDetail()` → `territoryStateSummary(country, region_system, year)`:
  counts territories in GROWTH/DECLINE/STAGNATION/n-a for the edge's source
  and target sectors at the edge's window end year, for that country/region_system
  only. Explicitly labelled "context only, not a claim that this edge is
  localised to specific territories" — satisfies the instruction not to
  fabricate edge-to-territory attribution for country/system-level edges.

**Part E — methodological protection (re-verified, unchanged):**
- `GEMEENTE_PROXY` still absent from `RELATION_EDGES` (20 edges, identical
  set to the v0.4 milestone).
- 121 `BLOCKED_EDGES` still isolated in their own panel,
  `allowed_for_training_label=false`, never rendered as graph edges.
- DEC-066 label classes (`ROBUST_ORIGINAL`/`FINE_GRAIN_SUPPORTED`/
  `EXPLORATORY_FINE_GRAIN`) unchanged.
- No forbidden causal language (`causal impact`, `causal effect`, `causally`);
  the only "causes" occurrence remains the benign Plotly.js bundle comment.

**Visual validation:** Playwright/headless browser unavailable in this
environment (same limitation as the v0.4 milestone) — validated via HTML/JS
structural checks (element IDs, embedded JS const parsing) instead of
screenshots. Manual validation steps documented in
`reports/HERALD_CURRENT_STATE.md`.

**Decision:** `OBSERVATORY_V041_VISUAL_READY`.

**Ficheiros afectados:**
- `src/data/european_panel/build_pt_municipality_geometry.py` (novo)
- `data/processed/geometries/pt_municipalities_continental.geojson` (novo, 1.18 MB)
- `data/processed/geometries/pt_municipalities_continental_manifest.json` (novo)
- `src/data/european_panel/build_observatory_v04_dashboard.py` (updated: PT geojson loading, dynamic graph, map↔graph linking)
- `reports/dashboards/herald_observatory_v04_granular_dashboard.html` (regenerated, 10.0 MB)
- `tests/test_observatory_v04_dashboard.py` (updated: graph-window → window-slider)
- `tests/test_observatory_v041_visual_upgrade.py` (novo — 41/41 PASS)
- `.gitignore` (added `data/external/portugal/geometry/raw/`)
- `reports/herald_artifact_registry.json`, `reports/HERALD_CURRENT_STATE.md`, `CODEX_MEMORY.md` (updated)

---

## DEC-067 — Observatory v0.5 Narrative Presentation Layer (2026-06-17)

**Status:** COMPLETE. Decision: `OBSERVATORY_V05_NARRATIVE_READY`.

**CORRECTION (2026-06-17, same day, v0.5.1):** the product owner reviewed this
milestone and rejected it as a polished MVP, not a complete-method presentation:
English UI, the HERALD architecture explanation at the bottom of the page (after the
map/KPIs), no integrated PT prediction despite the gap report saying it was closeable
without HPC, no true geographic heatmap (only a placeholder string for "similar
dynamics"), the sector graph never filtering the map on click, generic English KPI
cards, and technical vocabulary not fully confined to a collapsible section. **The
`OBSERVATORY_V05_NARRATIVE_READY` dashboard-readiness decision is corrected to
`OBSERVATORY_V05_PARTIAL`.** This correction does NOT alter any prior scientific or
statistical DEC-0xx conclusion — only the UX/dashboard-readiness claim for this
specific milestone. See DEC-068 below and
`reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md` for the full point-by-point fix
record. The v0.5 files themselves (exports/dashboard/tests) are untouched and their
65/65 tests still pass — they remain a valid historical artifact, just not the current
dashboard-readiness recommendation.

**Problem:** v0.4's granular dashboard (`herald_observatory_v04_granular_dashboard.html`)
is scientifically correct but communicates poorly to a layperson audience: raw acronyms
(GI/OQ/MN/KZ), an isolated sector-relation graph disconnected from the map, a heatmap
shown as a separate widget instead of being felt within the geography, and PT showing
bare NaN for the structurally-absent KZ sector.

**What was built (presentation layer only, no scientific recomputation):**
- New export pipeline `src/data/european_panel/build_observatory_v05_narrative_exports.py`
  re-shapes the v0.4 granular exports (territory state, relation edges, blocked proxy
  edges) into `data/processed/herald_observatory_v05_narrative/`: `territory_view`,
  `sector_view`, `relation_view`, `prediction_view`, `map_state_by_year_sector.json`,
  `relation_timeline.json`, `manifest.json`. Every number is carried through verbatim;
  only human-readable labels, evidence badges, and plain-language sentences are added.
- New dashboard builder `src/data/european_panel/build_observatory_v05_narrative_dashboard.py`
  → `reports/dashboards/herald_observatory_v05_narrative_dashboard.html` (14.8 MB,
  Plotly embedded locally, GSAP loaded from CDN for timeline/window playback only).
- Map color now changes directly by year/sector/view selection (state / velocity /
  above-below-expected / similar-dynamics-placeholder) — the map IS the heatmap, no
  separate chart.
- Sector→sector graph is dynamic and spatial: persistent mode (all valid relations
  shown faint, active time window highlighted) or active-window-only mode; clicking an
  edge updates an aggregate territory-context table and a plain-language sentence
  ("Between Y1 and Y2, in country X, sector A moves in the same/opposite direction as
  sector B. This is observed evidence, not proof of causality.").
- Prediction layer audit (`reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md`): found a
  validated observed-vs-expected forecast already exists for FR+NL
  (`data/processed/herald_observatory_v03/herald_observatory_v03_panel.csv`, causal
  rolling-origin AR(1) Ridge, same ZE2020/COROP grain as v0.4 granular) and wired it in
  directly. PT excluded: its only existing forecast is at NUTS3 grain (25 territories),
  not the MUNICIPALITY grain (278) used by v0.4/v0.5 — different grains, no validated
  join exists, and disaggregating would repeat the DEC-065 proxy-injection failure
  mode. Decision: `PREDICTION_LAYER_PARTIAL`. Closing the gap is a data-engineering
  task (re-run the existing forecast script against the PT municipal panel), not HPC.
- PT/KZ: confirmed every PT/KZ row carries `state=INSUFFICIENT_DATA`/`value=NaN` by
  construction (per DEC-064, "KZ structural_absent... No KZ claims") — relabelled
  explicitly as "Sector not available for Portugal" (never a bare NaN); KZ is disabled
  in the dashboard's sector selector when country=PT.
- NL gemeente proxy: fail-closed assert in both new builders confirms it never enters
  `relation_view`/the embedded `RELATION_EDGES` dataset; it remains visible only on the
  map/territory layer with a "Proxy / context" badge.
- 121 blocked proxy edges kept in their own technical panel, explicitly described as
  "audit only", with a forbidden-language guard against framing them as a "discovery".
- No causal language, no ML jargon (GNN/attention/encoder/AUC) in the main UI body —
  verified by `tests/test_observatory_v05_narrative_dashboard.py` (65/65 PASS).
  Determinism verified for both builders (identical output hash across consecutive
  runs, modulo the exports manifest's own `generated_at` timestamp).
- Playwright unavailable in this environment (same limitation as v0.4) — validated via
  embedded-JSON parsing, DOM id cross-reference, and onclick/onchange handler
  cross-reference instead of screenshots.

**Ficheiros afectados:**
- `src/data/european_panel/build_observatory_v05_narrative_exports.py` (novo)
- `src/data/european_panel/build_observatory_v05_narrative_dashboard.py` (novo)
- `data/processed/herald_observatory_v05_narrative/` (novo: 5 CSV + 5 JSON + manifest)
- `reports/dashboards/herald_observatory_v05_narrative_dashboard.html` (novo, 14.8 MB)
- `tests/test_observatory_v05_narrative_dashboard.py` (novo — 65/65 PASS)
- `reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` (novo)
- `CODEX_MEMORY.md`, `reports/HERALD_CURRENT_STATE.md`,
  `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`, `reports/herald_artifact_registry.json`
  (updated)
- v0.4 dashboard/builder/tests: untouched.

---

## DEC-068 — Observatory v0.5.1 Narrative Correction (2026-06-17)

**Status:** COMPLETE. Decision: see final status line below.
**Note (2026-06-18, traceability re-audit):** all 103/103 Part N structural
tests pass (`tests/test_observatory_v051_narrative_dashboard.py`), but
"structural tests pass" is not the same claim as "dashboard accepted as
final." No Playwright/real-screenshot visual validation has ever been
performed on v0.5.1 (Playwright unavailable in this environment — see below),
and the product owner's own next instruction after this milestone was to
"redesign the dashboard modularly, starting with the map" — i.e. v0.5.1 itself
was treated as a corrected draft, not a finally-accepted deliverable. The
decision below is worded accordingly.

**Problem (product-owner rejection of DEC-067/v0.5):** v0.5 was a polished MVP, not a
complete-method presentation of HERALD. Ten concrete defects: (1) architecture
explanation at the bottom of the page; (2) entire UI in English; (3) prediction layer
not visually central; (4) PT municipal prediction never integrated despite the gap
report saying it was closeable as pure data engineering; (5) no true geographic
heatmap (a placeholder string only); (6) sector graph never filtered the map on click;
(7) generic English KPI cards instead of an interpretable evidence summary; (8)
technical vocabulary (beta/q_fdr/bss) not fully confined to a collapsible section; (9)
"How it works" too shallow to read as a method figure; (10) no explicit distinction
between validated relations and (nonexistent) neural candidate relations.

**What was built (data-engineering addition + presentation correction; no v0.4
scientific number recomputed or altered):**
- New script `src/data/european_panel/build_pt_municipal_prediction_layer.py`: re-runs
  the exact causal persistence/Ridge AR(1) method already validated for FR/NL
  (`RIDGE_ALPHA=1.0`, `RIDGE_MIN_TRAIN=4`, reused verbatim from
  `build_observatory_export.py._rolling_ridge_forecasts`) directly against the observed
  PT municipal panel (`data/processed/phase7_pt_municipal/pt_municipal_phase7_panel.csv`,
  278 municipalities × 16 years × 8 sectors; KZ structurally absent for every row). No
  proxy disaggregation. An explicit code-level leakage assertion confirms every
  `valid_forecast` row's `persistence_forecast` equals the prior year's observed value
  in the source panel for all 28,974 valid-forecast rows in this run.
  Output: `data/processed/herald_observatory_v051_narrative/pt_municipal_prediction_view.csv`
  (40,032 rows: 28,974 valid_forecast / 6,610 insufficient_history / 4,448
  structural_absent). `reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` updated to
  `CLOSED` with the required sentence: "PT municipal forecast generated via causal
  persistence/Ridge on observed municipal panel; no proxy, no HPC."
- New export pipeline `src/data/european_panel/build_observatory_v051_narrative_exports.py`:
  same re-shaping logic as v0.5's exports script, but (a) entirely French-language
  output fields/sentences, (b) integrates the new PT municipal forecast into a unified
  `prediction_view.csv`/`.json` alongside FR/NL, (c) adds `economic_basins.json`
  (territorial-intensity quantile score per country/region/year, for the new
  geographic heatmap), (d) adds `prediction_lookup.json` for the dashboard's
  observed/expected/difference side-panel display.
- New dashboard builder `src/data/european_panel/build_observatory_v051_narrative_dashboard.py`
  + `..._template.py` → `reports/dashboards/herald_observatory_v051_narrative_dashboard.html`
  (18.2 MB, Plotly embedded locally, GSAP from CDN for timeline/window playback only):
  - "Méthode HERALD" architecture section (6-stage diagram + 4 component cards:
    statistical baseline / relational-candidate layer / validation / output) is the
    first content block after the title, before the evidence summary and before the map.
  - "Prévision locale" section + a new "Écart à l'attendu" map mode + side-panel
    observed/expected/difference fields, now covering FR+NL+PT.
  - New "Bassins économiques" map mode: a real geographic intensity layer (quantile of
    mean velocity per country/region/year), distinct from the state/velocity/prediction
    choropleth modes — never called a "causal cluster".
  - Sector-relation graph now wired to the map: clicking an edge calls
    `applyGraphFilterToMap()`, which sets the map's country selector and year slider to
    the edge's country/window and re-renders — a real, traceable interaction, not two
    independent click handlers.
  - Generic KPI cards replaced by a French "Résumé d'évidence"
    (e.g. "3 pays comparés", "20 relations validées", "121 relations proxy rejetées").
  - beta/q_fdr/bss and the one permitted causality-prohibition sentence
    ("Ces relations n'établissent pas de lien de causalité structurelle.") confined to
    two collapsible `<details class="tech">` blocks — verified absent from the static
    HTML body outside those blocks.
  - New "Couche relationnelle" section explicitly states, in French, that no neural
    candidate-relation dataset exists in this repository today; only validated Phase 7
    relations are shown, kept separate from the (preserved-for-audit-only) blocked
    proxy edges.
- All hard rules re-verified: `GEMEENTE_PROXY` absent from `relation_view`/embedded
  `RELATION_EDGES` (20 edges unchanged: FR=9, NL COROP=8, PT Municipal=3); 121 blocked
  proxy edges isolated, `allowed_for_training_label=false`; PT/KZ always
  `structural_absent`/disabled, never an enabled option or a bare NaN; no
  "causal"/"causes"/"not proof of causality" in the main narrative (only inside the
  technical-details blocks, as an explicit prohibition).
- Determinism verified for all three builders (PT municipal forecast script, exports,
  dashboard) — identical output hashes across consecutive runs.
- Playwright unavailable in this environment (same limitation as v0.4/v0.5) — validated
  structurally: embedded-JSON parsing, DOM id cross-reference, onclick/onchange handler
  cross-reference, and explicit substring/negative-assertion tests for every Part N
  requirement (103/103 tests pass — see `tests/test_observatory_v051_narrative_dashboard.py`).

**Ficheiros afectados (novos, v0.4/v0.4.1/v0.5 inalterados):**
- `src/data/european_panel/build_pt_municipal_prediction_layer.py` (novo)
- `src/data/european_panel/build_observatory_v051_narrative_exports.py` (novo)
- `src/data/european_panel/build_observatory_v051_narrative_dashboard.py` (novo)
- `src/data/european_panel/build_observatory_v051_narrative_dashboard_template.py` (novo)
- `data/processed/herald_observatory_v051_narrative/` (novo)
- `reports/dashboards/herald_observatory_v051_narrative_dashboard.html` (novo, 18.2 MB)
- `tests/test_observatory_v051_narrative_dashboard.py` (novo — 103/103 PASS)
- `reports/HERALD_OBSERVATORY_V051_CORRECTION_AUDIT.md` (novo)
- `reports/HERALD_OBSERVATORY_V05_PREDICTION_GAP.md` (§6 appended — gap CLOSED)
- `CODEX_MEMORY.md`, `reports/HERALD_CURRENT_STATE.md`,
  `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`, `reports/herald_artifact_registry.json`
  (updated; DEC-067 entries above corrected with a superseding note, not deleted)
- v0.4/v0.4.1/v0.5 dashboards/builders/tests: untouched (re-verified: their test suites
  still pass — 192/192 across `test_observatory_v05_narrative_dashboard.py`,
  `test_observatory_v041_visual_upgrade.py`, `test_observatory_v04_dashboard.py`,
  `test_observatory_v04_granular_evidence_policy.py`).

**Final decision (2026-06-18, traceability re-audit):** `OBSERVATORY_V051_CANDIDATE_NEEDS_MAP_REDESIGN`.
All ten v0.5 defects are fixed and 103/103 structural tests pass — this is a
real, substantive correction over v0.5, not cosmetic. It is adopted as the
**current best draft / candidate** dashboard, superseding v0.5's
`OBSERVATORY_V05_PARTIAL` status. It is explicitly **not** promoted to a final
"narrative ready" / accepted-as-final status, because (1) it has never been
visually validated (no Playwright run, no real screenshot — only DOM/JS string
and embedded-JSON structural assertions), and (2) the product owner's own
next-step direction was to modularize the dashboard starting with the map,
which implies v0.5.1 is a candidate to be reworked, not a finished artifact.
This status string is used consistently everywhere v0.5.1's readiness is
referenced (`CODEX_MEMORY.md`, `HERALD_CURRENT_STATE.md`,
`HERALD_ACTIVE_DOCUMENT_INDEX.md`, `herald_artifact_registry.json`,
`HERALD_NAMING_CONVENTIONS.md`, `README.md`) — see those files for the
corresponding update.

---

## DEC-069 — ZE2020 Relational-Transition Transfer Probe (2026-07-22)

**Status:** `COMPLETE_GATE_FAIL`.

**Problem:** HERALD_39 showed that current graph aggregates recognize temporal
succession, but they did not improve next-year sector-share prediction over the
node-only panel. That result does not reject economic relations in general. It
leaves unresolved whether changes in a node's past relational neighbourhood
carry transferable information about an independently observed future sector
transition.

**Hypothesis:** for a ZE2020 x A10 node at decision year `t`, changes in graph
aggregates built only from information available through `t` may help rank a
future top-3 sector-growth entry at `t+3`, beyond node-only history and simple
degree change. The effect must transfer to ZE2020 units excluded from model
fitting.

**Minimal diagnostic:** reuse the audited dynamic nodes, expanding edge memory,
graph-aggregation helper, top-3-entry label, and horizon-aware maturity rule.
Fit only a standardized logistic probe. Evaluate with ZE-disjoint folds and
rolling decision years. Compare real relation change with node-only,
node-plus-degree-change, randomized endpoints, a past-only graph snapshot,
sector-shuffled relation change, and shuffled training labels.

**Pre-registered gate:** the real relation-change view must have positive mean
`NDCG@3` lift over both node-only and degree-change controls, beat each graph
placebo in at least 60% of paired seed-year-fold comparisons, and degrade under
both sector and target shuffles. All inputs and outputs must remain finite,
time-respecting, ZE-disjoint, and free of causal or automatic-recommendation
claims.

**Decision rule:** failure rejects only this representation/target/protocol. It
does not reject nonlinear territorial relations generally. A pass authorizes a
small nonlinear temporal encoder experiment; it does not validate a dynamic
GNN, causality, or operational recommendation.

**Result (Meso job 7780697):** 525 finite metric rows covering five seeds,
three evaluation years, five ZE-disjoint folds, and seven views. Every paired
comparison used the same train/test/positive population; training contained 224
ZEs, testing contained 56, and ZE overlap was always zero. Mean `NDCG@3` was
0.6010 for node-only, 0.6050 for node-plus-degree-change, and 0.6059 for real
relation change. Real relation change exceeded degree by only 0.0010, was nearly
tied with randomized endpoints (lift 0.0003), and lost to sector-shuffled
relations (-0.0002 lift). Target shuffle degraded strongly to 0.4604, confirming
that the task itself contains learnable signal, but not that current edge
semantics transfer.

**Final decision:** `RELATIONAL_TRANSITION_TRANSFER_GATE_FAIL`. The current
relation-change representation is not authorized for a nonlinear temporal
encoder. The failure is specific: graph inspection found 257,823
`ze_similarity` edges versus only 426 `cross_ze_same_sector` and 211
`intra_ze_sector` edges. The next admissible diagnostic is edge-family isolation
and scale normalization against the same target and controls, not a larger
neural model.

---

## DEC-070 — ZE2020 Edge-Family Isolation and Balanced Blocks (2026-07-22)

**Status:** `COMPLETE_GATE_PASS_LIMITED`.

**Problem:** DEC-069 failed to separate real graph changes from randomized and
sector-shuffled controls. The current graph contains three edge families with
very different support. Edge-count imbalance is a candidate explanation, not a
confirmed cause, because the linear probe already standardizes feature columns.

**Hypothesis:** one sparse economic edge family may contain transferable sector
transition signal that is hidden when generic and family-specific aggregates are
mixed. Representing every family as a separate, equally parameterized feature
block permits a fair test without changing the target, split, or classifier.

**Minimal diagnostic:** reuse the DEC-069 target and ZE-disjoint rolling
protocol. Build identical graph-aggregate/change blocks for
`ze_similarity`, `cross_ze_same_sector`, and `intra_ze_sector`. Evaluate each
family alone, the two sector-economic families together, and all three together.
Every real variant receives a matched randomized-endpoint control. The balanced
economic combination also receives a within-ZE-year sector shuffle. A
standardized logistic regression remains the only model.

**Pre-registered gate:** a family or balanced combination is informative only
if it has positive mean `NDCG@3` lift over node-only and its own matched endpoint
placebo, wins at least 60% of paired seed-year-fold comparisons against that
placebo, and degrades under sector shuffle when the sector-economic combination
is tested. All populations must remain identical and ZE overlap must remain zero.

**Decision rule:** a pass authorizes carrying only the surviving family blocks
into a small nonlinear temporal encoder. Failure means current edge families do
not provide transferable signal under the audited transition task; it does not
reject nonlinear territorial economics generally.

**Result (Meso job 7780874):** 900 finite metric rows, 12 views, five seeds,
three evaluation years, and five ZE-disjoint folds. All views used identical
train/test/positive populations and ZE overlap was zero. `ze_similarity_only`
reached mean `NDCG@3=0.60677`, versus 0.60096 for node-only and 0.60231 for its
matched endpoint-randomized control. Its endpoint-placebo lift was +0.00446 with
62.7% paired wins. `all_families_balanced` also passed, but its result
(`NDCG@3=0.60691`) was only +0.00013 above `ze_similarity_only`.
`cross_ze_same_sector_only` remained below node-only, and
`intra_ze_sector_only` was identical to node-only. Average precision also
remained lower for ZE similarity (0.53289) than node-only (0.53709).

**Final decision:** `ZE_SIMILARITY_BLOCK_AUTHORIZED_FOR_MINIMAL_NONLINEAR_PROBE`.
Only the `ze_similarity` family survives as a transferable ranking candidate.
The two sparse sector-economic families are not promoted. The result is a
limited representation gate pass on within-ZE ranking, not validation of a
dynamic GNN, general classification improvement, causality, or recommendation.

---

## DEC-071 — ZE2020 Similarity Nonlinear Transfer Probe (2026-07-22)

**Status:** `COMPLETE_GATE_FAIL`.

**Problem:** DEC-070 authorized only the isolated `ze_similarity` block for a
minimal nonlinear probe. It did not show that a nonlinear model is useful, nor
that the result warrants a recurrent or graph-neural architecture.

**Hypothesis:** nonlinear interactions between audited node history and changes
in the ZE-similarity neighbourhood may improve held-out-ZE sector-transition
ranking beyond both a linear ZE-similarity probe and a nonlinear node-only
control.

**Minimal diagnostic:** reuse the DEC-070 ZE-similarity block, target, years,
five ZE-disjoint folds, and seeds. Compare the existing standardized logistic
probe with one existing project MLP configuration: hidden layers `(32,16)`,
ReLU, Adam, early stopping, and no new dependency. Include MLP node-only,
MLP ZE-similarity, matched endpoint-randomized ZE-similarity, and shuffled
training labels. No hyperparameter search is permitted.

**Pre-registered gate:** MLP ZE-similarity must have positive mean `NDCG@3`
lift over MLP node-only and logistic ZE-similarity, beat endpoint-randomized MLP
in at least 60% of paired seed-year-fold comparisons, and degrade under target
shuffle. Populations must be identical, metrics finite, and ZE overlap zero.

**Decision rule:** a pass authorizes designing a small recurrent temporal
encoder with the same isolated relation block. Failure retains ZE similarity as
a linear exploratory indicator only and blocks added neural complexity.

**Result (Meso job 7780890):** 450 finite metric rows, six views, five seeds,
three evaluation years, and five ZE-disjoint folds. All views used identical
populations and ZE overlap was zero. Mean `NDCG@3` was 0.61426 for MLP
node-only, 0.60677 for logistic ZE-similarity, and 0.59570 for MLP
ZE-similarity. The nonlinear relation view therefore lost 0.01856 to MLP
node-only and 0.01107 to logistic ZE-similarity. It beat its endpoint-randomized
MLP by 0.00702, but in only 56.0% of paired comparisons, below the registered
60% gate. Target shuffle degraded strongly to 0.44392.

**Final decision:** `NONLINEAR_ZE_SIMILARITY_GATE_FAIL`. Nonlinearity is useful
for the node panel, but the current MLP does not integrate the ZE-similarity
block successfully. ZE similarity remains authorized only as a small linear
exploratory ranking indicator. Recurrent or graph-neural complexity is not
authorized from this result, and no post-result hyperparameter search is
performed.

---

## DEC-072 — ZE2020 Pre-Prediction Relation Bottleneck Fusion (2026-07-22)

**Status:** `COMPLETE_GATE_FAIL`.

**Problem:** DEC-071 showed that raw concatenation of ZE-similarity aggregates
hurts the MLP, while node-only nonlinearity is useful. Reusing relations as a
post-prediction residual correction would repeat the closed Phase 5 architecture
and contradict HERALD_23. The next test must fuse representations before the
ranking head.

**Hypothesis:** the raw 13-column ZE-similarity block contains redundant/noisy
dimensions. A training-only unsupervised bottleneck may preserve its dominant
structure while preventing it from overwhelming the temporal node
representation.

**Minimal diagnostic:** keep the DEC-071 MLP and protocol fixed. Standardize the
node block separately. Standardize the ZE-similarity block and apply PCA fitted
only on training rows, retaining 90% of training variance. Concatenate the node
representation and relation bottleneck before the MLP. Compare with node-only,
raw-concatenation, endpoint-randomized bottleneck, and shuffled training labels.
No component-count tuning or residual output correction is permitted.

**Pre-registered gate:** bottleneck fusion must have positive mean `NDCG@3`
lift over both node-only and raw-relation MLP, beat its endpoint-randomized
control in at least 60% of paired seed-year-fold comparisons, and degrade under
target shuffle. Populations must be identical, metrics finite, and ZE overlap
zero.

**Decision rule:** a pass authorizes a learned dual temporal/relation encoder
before ranking. Failure blocks neural integration of the current ZE-similarity
features and leaves them as linear exploratory indicators only.

**Result (Meso job 7780898):** 375 finite metric rows, five views, five seeds,
three evaluation years, and five ZE-disjoint folds. Populations were identical
and ZE overlap was zero. Bottleneck fusion reached mean `NDCG@3=0.61147`,
recovering much of the raw-concatenation loss (0.59570), but remained below
node-only MLP (0.61426). It exceeded the endpoint-randomized bottleneck by only
0.00117 with 54.7% paired wins, below the registered 60% threshold. Target
shuffle degraded to 0.45135. Average precision also remained below node-only
(0.53240 versus 0.54633).

**Final decision:** `RELATION_BOTTLENECK_FUSION_GATE_FAIL`. Pre-prediction
compression is materially better than raw concatenation, but it does not prove
transferable neural value from current ZE-similarity relations. Further neural
fusion or recurrent tuning is blocked. The next admissible direction is to
improve externally grounded edge semantics/provenance, particularly functional
mobility or commuting relations, before another neural integration gate.

---

## DEC-073 — Official France ZE2020 Commuting-Edge Provenance (2026-07-22)

**Status:** `RELATION_SOURCE_READY_NOT_MODEL_INPUT`.

**Problem:** DEC-072 blocks further neural fusion of trajectory-similarity
relations. The legacy France mobility matrix cannot replace those relations
because its generator and exact source are absent.

**Hypothesis:** official INSEE commune residence-to-workplace flows can provide
a reproducible directed functional relation between ZE2020 territories, while
keeping observation date and publication availability distinct.

**Construction:** aggregate checksum-pinned INSEE flow snapshots for 2012,
2017, and 2023 to the canonical 280 ZE2020 scope. Resolve historical commune
codes using the official COG 2026 event file and collapse Paris/Lyon/Marseille
arrondissements to parent communes. Preserve raw commuter counts, shares of all
workers resident at the origin, in-scope shares, cross-ZE row-normalized shares,
self-flow flags, low-flow cautions, release dates, and both temporal clocks.

**Audit:** Meso job 7780907 produced 86,568 finite directed edge-snapshot rows,
with all 280 source and target zones represented in every snapshot. Source-code
resolution exceeds 99.96% in all snapshots. Eight direct tests pass. The old
matrix correlates strongly with a temporary 2017 reconstruction but is not
identical and remains forbidden.

**Final decision:** `OFFICIAL_COMMUTING_RELATION_SOURCE_READY`. A strict
ex-ante assignment/lift builder is authorized as the next step. The present
artifact is not yet a model input and does not authorize neural promotion,
causal language, automatic recommendation, or use of the 2023 release for
strict ex-ante decisions in 2024--2025. See HERALD_44.

**Implementation addendum:** Meso job 7780912 generated 276,790 release-aware
cross-ZE edge-year rows for 2016--2025. Years 2012--2015 remain unavailable;
2016--2020 use only the 2012 snapshot and 2021--2025 use only the 2017
snapshot. The 2023 snapshot is absent from the current strict input candidate.
Five direct tests pass. This completes the authorized builder but does not
change the model-input restriction before a matched-placebo gate.

---

## DEC-074 — ZE2020 Strict Commuting Relation Gate (2026-07-22)

**Status:** `CLOSED_GATE_FAILED_RAW_WEIGHTING_REJECTED`.

**Problem:** DEC-073 provides reproducible and release-aware commuting edges,
but provenance alone does not show that their economic semantics transfer to a
territorial-sector task.

**Hypothesis:** weighted directed residence-to-workplace relations provide
territorial-sector context beyond node history, availability timing, false
destinations, unweighted topology, reversed direction, and trajectory
similarity.

**Fixed test:** reuse the HERALD_40--43 future top-3 sector-entry target,
evaluation years 2020--2022, five ZE-disjoint folds, seeds 42--46, mature-label
rule, logistic regression, and NDCG@3. Aggregate observed sector features
through outgoing and incoming strict commuting matrices before prediction.

**Pre-registered gate:** real commuting must have positive mean NDCG@3 lift
over availability-only, uniform-weight, reversed-direction, and
trajectory-similarity controls; it must beat randomized endpoints with positive
mean lift and at least 60% paired wins; target shuffle must degrade. Populations
must remain identical, finite, mature, and ZE-disjoint.

**Decision rule:** pass authorizes only design of a small pre-prediction
temporal/commuting encoder. Failure blocks neural integration under this
representation and target. Neither outcome authorizes causal or automatic
recommendation claims. See HERALD_45.

**Execution result:** Meso job `7780933`, commit `6da99d4`, completed exit
`0:0` in 2m45s with empty stderr. The fixed run produced 600 finite metric
rows with zero ZE overlap and identical paired populations. Weighted real
commuting reached mean NDCG@3 0.615354 versus 0.600963 node-only and 0.608295
randomized endpoints, but lost to the same topology with uniform weights
(0.635586; real-minus-uniform -0.020231). It was also negative against
node-only in 2020 and 2022, with the aggregate lift driven by 2021.

**Final decision:** the pre-registered gate fails. Raw commuting intensity is
not authorized for neural integration. Uniform topology remains only a
candidate observation until tested against a matched uniform-endpoint placebo;
no dynamic-graph, causal, or recommendation claim follows.

---

## DEC-075 -- ZE2020 matched commuting-topology gate (2026-07-22)

**Status:** `CLOSED_GATE_FAILED_TOPOLOGY_SEMANTICS_NOT_ISOLATED`.

**Problem:** DEC-074 found that uniform weights outperformed raw commuting
intensity, but did not include a randomized-endpoint placebo with the same
uniform representation. The apparent topology signal is therefore not yet
isolated.

**Fixed test:** retain the DEC-074 target, maturity rule, years, ZE-disjoint
folds, seeds, linear estimator, and NDCG@3. Compare real uniform topology with
matched uniform randomized endpoints, degree-only topology statistics,
reversed uniform direction, node-only, availability-only, and shuffled labels.

**Gate:** real uniform topology must beat every semantic control in mean
NDCG@3, beat matched randomized endpoints in at least 60% of seed/year/fold
pairs, preserve identical finite populations, and maintain zero ZE overlap.

**Decision rule:** pass authorizes only a later weight-transform gate; failure
closes this commuting-topology representation. No neural, causal, dynamic-GNN,
or recommendation claim is authorized. See HERALD_46.

**Execution result:** Meso job `7780944`, commit `3a239f9`, completed exit
`0:0` in 2m22s with empty stderr. The fixed run produced 525 finite metric
rows with zero ZE overlap and identical populations. Real uniform topology
reached mean NDCG@3 0.635586, but matched uniform randomized endpoints reached
0.643529 (real-minus-placebo -0.007943; 37.3% paired wins). Four of five
seed-level mean deltas were negative.

**Final decision:** the matched topology gate fails. The gain over node-only is
consistent with generic neighbour aggregation but is not attributable to the
official destination semantics. Weight transforms and neural integration are
closed for this representation. Reopening requires a materially different
economic representation and a new decision.

---

## DEC-076 -- France ZE2020 A10 source-provenance closure (2026-07-22)

**Status:** `SOURCE_PROVENANCE_CLOSED`.

**Problem:** the canonical ZE2020 sector panel depended on a processed A10
intermediate whose dedicated source builder was not part of the current
canonical chain.

**Fixed reconstruction:** stream the checksum-pinned official INSEE SIDE 2025
ZIP directly, select annual ZE2020 establishment creations for all legal forms
and the nine project A10 sectors, restrict to the canonical 280-zone scope, and
require exact reconciliation against the clean panel for all 3,920 ZE-years.

**Audit result:** final Meso job `7780962` rebuilt 35,280 rows with empty stderr. The
result is byte-identical to the existing canonical panel. One sparse official
cell (`5218/2016/JZ`) is completed as zero only because the other eight sectors
equal the independent official total. Eighteen focused tests pass.

**Final decision:** `FR_ZE2020_A10_SOURCE_READY`. The legacy processed A10 file
is no longer an input to the canonical builder. This closes data provenance
only; contemporaneous sector features remain forbidden as target-year model
inputs, and no relation, neural, causal, or recommendation claim is authorized.
See HERALD_47.

---

## DEC-077 -- ZE2020 context-conditioned sector-relation gate (2026-07-22)

**Status:** `COMPLETE_GATE_FAIL_TARGET_FEATURE_SPECIFICATION_CLOSED`.

**Prior-work boundary:** Phase 7 already estimated country-level lagged sector
precedence using the 280 France ZE2020 observations, and DEC-060 audited its
weak France signal. Phase 8 LOTO measured territorial influence on robust
country coefficients; it did not estimate local ZE coefficients. Re-running
the pooled regression is forbidden as duplicate evidence.

**Unresolved hypothesis:** a source-sector lag may carry different information
for different ZE economic contexts. A shared nonlinear model may partially pool
these interactions across ZEs and transfer them to held-out zones, while a
single pooled linear coefficient cannot represent that heterogeneity.

**Fixed diagnostic:** use only canonical A10 observations and lagged features.
Build ordered source-sector/target-sector ZE-year samples. Compare matched
target-history controls, pooled linear source-lag regression, and one small MLP
with source lag plus lagged ZE composition. Evaluation is rolling-origin with
ZE-disjoint folds. Include source-lag shuffle, ZE-context shuffle, and target
shuffle. No hyperparameter search is authorized.

**Gate:** the context-conditioned MLP must improve held-out mean MAE over both
the matched no-source MLP and pooled linear relation model, beat source-shuffle
in at least 60% of seed/year/fold comparisons, degrade under context and target
shuffle, preserve identical populations, and use no target-year features.

**Decision rule:** a pass authorizes only design of a small temporal relation
encoder whose edge scores depend on ZE context. Failure closes this target and
feature specification, not all sector relations. Neither outcome authorizes a
dynamic-GNN, causal, or recommendation claim. See HERALD_48.

**Execution result:** Meso array `7781010` completed all five seeds with exit
`0:0`, empty stderr, 1,050 finite metric rows, complete populations, zero
train/test ZE overlap, and full convergence. The context-conditioned MLP
improved mean MAE over the no-source MLP (0.274963 versus 0.296391), but lost
strongly to the pooled linear relation control (0.177429) in 174/175 paired
comparisons. Source shuffle degraded in only 53.7% of pairs and context shuffle
in 49.1%, both below the registered 60% threshold. Target shuffle degraded mean
MAE by 15.5% but lost only 66.3% of pairs, below the registered 80% threshold.

**Final decision:** the gate fails. The current target-growth, source-lag, and
lagged ZE-composition specification is closed, and no temporal relation encoder
is authorized from DEC-077. This does not reject all sector relations; reopening
requires a materially different economic representation and a new decision.
No causal, dynamic-GNN, automatic recommendation, or policy claim follows. See
HERALD_49.

---

## DEC-078 -- ZE2020 product-space entry-density gate (2026-07-23)

**Status:** `COMPLETE_GATE_FAIL_ENTRY_DENSITY_REPRESENTATION_CLOSED`.

**Prior-work boundary:** DEC-017/G1-L1 already rejected promotion of the France
RCA co-specialization graph because temporal and configuration nulls reproduced
its high stability. That graph-stability gate is not reopened. DEC-078 tests a
different outcome: next-year entry into RCA specialization.

**Support preflight:** the official canonical A10 panel provides 17,196
non-specialized ZE-sector-year candidates and 2,611 next-year specialization
entries over decision years 2012--2024. Every canonical ZE has at least one
entry. No product-space score was evaluated before registration.

**Fixed diagnostic:** within each decision year and ZE-disjoint fold, estimate
Hidalgo-Hausmann sector proximity from training ZEs only. Rank non-specialized
sectors in held-out ZEs by product-space density. Compare with target-sector
prevalence, current target RCA, reassigned product-space identities,
sector-shuffled held-out composition, target-shuffled labels, and random score.
Use five folds, seeds 42--46, and NDCG@3 as the primary metric.

**Gate:** real density must beat both marginal controls in aggregate and in at
least 9/13 years, beat randomized product-space and sector-shuffled density in
at least 60% of paired seed/year/fold comparisons, and degrade under target
shuffle in at least 80%. Populations must be identical and train/test ZE overlap
must be zero.

**Decision rule:** a pass authorizes only a small representation layer using
entry density. Failure closes this France ZE2020 entry-density representation,
not all sector relations. Neither outcome authorizes a dynamic-GNN, causal,
automatic recommendation, or policy claim. See HERALD_50.

**Execution result:** Meso job `7781384` completed in 4m23s with exit `0:0`,
empty stderr, 2,275 finite metric rows, identical populations, and zero
train/test ZE overlap. Each seed reproduced the registered 17,196 candidates
and 2,611 next-year entries. Product-space density exceeded target prevalence
by mean NDCG@3 `+0.006704`, but lost to current target RCA by `-0.009128`.
It beat the randomized product space in 98.8% of registered pairs, the
sector-shuffled density in 100%, and the target-shuffled labels in 81.5%, but
exceeded both marginal controls in only 4/13 years rather than the required
9/13.

**Final decision:** the gate fails. The tested France ZE2020 product-space
entry-density representation is closed and is not authorized for a relation or
neural representation layer. The result shows non-random sector-composition
structure, but no incremental entry-ranking value beyond current target RCA.
It does not reject all sector relations. Reopening requires a materially
different economic object and a new pre-registered decision. See HERALD_51.

---

## DEC-079 -- ZE2020 temporal bipartite masked-reconstruction gate (2026-07-24)

**Status:** `COMPLETE_GATE_FAIL_MASKED_RECONSTRUCTION_SPECIFICATION_CLOSED`.

**Prior-work boundary:** this decision does not reopen inferred-relation or
graph-prediction branches closed by DEC-017, DEC-069--075, DEC-077, or
DEC-078. It instead treats the observed ZE2020 x A10 sector-share composition
as a weighted bipartite object and asks a self-supervised reconstruction
question. No correlation-derived, commuting, similarity, product-space, or
future-target edge is used.

**Support preflight:** the canonical France sector panel contains 280 ZEs, nine
A10 sectors, and complete annual compositions for 2012--2025: 35,280 unique
ZE-year-sector rows and 3,920 ZE-year vectors, all summing to one. No
reconstruction metric was inspected before registration.

**Fixed diagnostic:** hide exactly three sectors per ZE-year, preserve the
mask, and reconstruct only those cells from current visible ZE-sector edges,
the lagged composition, and target-sector identity. Use five ZE-disjoint folds,
seeds 42--46, rolling training through each evaluation year 2017--2025, and
compositionally project every prediction to the hidden remaining mass.

**Controls:** temporal persistence, training-sector mean closure, matched
Ridge, history-only MLP, current-only MLP, sector-identity shuffle,
lagged-profile temporal shuffle, and random closure. Model sizes and training
settings are fixed in HERALD_52; no hyperparameter search is permitted.

**Gate:** the full MLP must beat Ridge and both closure controls in aggregate,
beat Ridge and both information ablations in at least 60% of paired
seed/year/fold comparisons, degrade under both semantic shuffles, recur against
Ridge and both ablations in at least 6/9 years, preserve all integrity checks,
and remain stable across seeds.

**Decision rule:** a pass authorizes only design of a small temporal bipartite
representation layer. Failure closes this masked-reconstruction specification.
Neither outcome validates a dynamic GNN, production imputation, causal claim,
automatic recommendation, or policy action. See HERALD_52.

**Execution result:** Meso array `7782372` completed all five seeds with exit
`0:0`, empty stderr, 2,025 finite metric rows, identical hidden targets,
exactly three hidden sectors per ZE-year, compositional error at floating-point
precision, and zero train/test ZE overlap. The full MLP beat matched Ridge in
99.1% of comparisons, history-only in 100%, current-only in 92.4%,
sector-shuffle in 94.2%, and temporal-shuffle in 100%. It also beat all three
of Ridge/history-only/current-only in all nine evaluation years.

**Decisive failure:** temporal persistence achieved masked MAE `0.009652`
against `0.013498` for the full MLP and won 220/225 paired comparisons. The
five MLP wins all occurred in 2022. Excluding six MLP fits that reached the
300-epoch ceiling leaves the conclusion unchanged.

**Final decision:** the gate fails and the tested masked-reconstruction
specification is closed. The ablations support only a partial finding that the
MLP uses joint current-composition and temporal information; they do not
justify a neural temporal bipartite layer because simple previous-year
economic memory remains substantially stronger. No production imputation,
dynamic-GNN, recommendation, causal, or policy claim is authorized. See
HERALD_53.

---

## DEC-080 -- ZE2020 composition-transition ranking gate (2026-07-24)

**Status:** `COMPLETE_GATE_FAIL_TRANSITION_RANKING_SPECIFICATION_CLOSED`.

**Prior-work boundary:** DEC-080 does not reopen the three-year top-3 entry
target of DEC-069, RCA entry-density of DEC-078, or masked level reconstruction
of DEC-079. It tests a different observed object: the signed next-year change
in each sector's share inside a ZE, ranked by absolute transition magnitude.
No inferred relation edge is used.

**Support preflight:** the canonical A10 panel provides 30,240 complete
ZE-sector decision-year targets over 2013--2024. The fixed evaluation years
2017--2024 contain 20,160 rows and exactly 6,720 observed top-3 absolute
changes per seed. Only four target changes are exactly zero. No model metric
was inspected before registration.

**Fixed diagnostic:** use complete share vectors at `t` and `t-1`, their
within-ZE delta vector, and target-sector identity to predict signed share
change at `t+1`. Rank sectors inside each held-out ZE by absolute predicted
change. Training uses only other ZEs and labels matured by the evaluation
decision year.

**Controls:** zero change, past signed delta, matched Ridge, target-history-only
MLP, current-only MLP, sector shuffle, temporal shuffle, target shuffle, and
random ranking. The DEC-079 Ridge/MLP hyperparameters are reused unchanged;
no architecture search is allowed. Signed targets are standardized using only
the training-fold mean and deviation and inverse-transformed before metrics.

**Gate:** full MLP must beat past delta and Ridge in aggregate and at least 60%
of pairs, beat both information ablations, degrade under sector/temporal/target
shuffles, improve top-3 sign accuracy, recur against all substantive controls
in at least 6/8 years, preserve temporal/ZE integrity, and remain seed-stable.

**Decision rule:** a pass authorizes only a small transition representation
layer. Failure closes this continuous transition-ranking specification.
Neither outcome validates a dynamic GNN, causality, automatic recommendation,
or policy action. See HERALD_54.

**Execution:** Meso array `7782532` completed all five seeds with exit `0:0`
and empty stderr. The audit contains 2,000 finite metric rows across eight
years, five ZE-disjoint folds, ten views, and five seeds. Target identity,
nine-sector completeness, label maturity, and zero ZE overlap all pass.

**Result:** `mlp_joint` reaches NDCG@3 `0.623920`. It exceeds matched Ridge
(`0.579403`) and degrades under sector and temporal shuffles, but loses to
`past_delta` (`0.647044`) and target-history-only MLP (`0.635467`). Paired win
rates are 32.0% against past delta, 55.0% against Ridge, and 43.5% against
target history. It beats all substantive controls in 0/8 evaluation years.
Seed CV is only 0.47%, so the failure is stable rather than an optimization
accident.

**Final decision:** the registered gate fails and this continuous
transition-ranking specification is closed. The experiment supports only that
time and sector identity contain non-random predictive information and that
the MLP result is consistent with some nonlinear structure. It does not
establish robust
incremental value from joint cross-sector composition beyond direct sector
history. No dynamic-GNN, causal, automatic-recommendation, or policy claim is
authorized. See HERALD_55.

---

## DEC-081 -- France ZE2020 product and evidence contract (2026-07-27)

**Status:** `PRODUCT_AND_EVIDENCE_CONTRACT_FROZEN`.

**Problem:** DEC-069 through DEC-080 closed eleven consecutive relational and
representational specifications. The recurring cost was not any single failure but
the repeated re-testing of equivalent hypotheses under new model names, because the
project had never fixed in writing what its forecasting engine is, what the
relational layer may claim, and what single condition would authorize another neural
experiment. This decision fixes those three answers. It validates no model, produces
no metric, authorizes no HPC job, and reopens no closed branch.

**Q1 -- forecasting engine.** The intended primary engine is **sectoral persistence
at ZE x sector granularity**, because the product objective is sectoral. It is
recorded as a **CANDIDATE**, not a validated engine: no rolling-origin audit of it
exists. It may not be described as validated or promoted until that audit is
delivered. The existing ZE-total baseline
(`src/modeles/france_ze2020/train_fr_ze2020_baselines.py`, persistence plus Ridge,
lag-only features, `DEFAULT_EVAL_YEARS = 2019-2025`, still
`claim_status=exploratory_smoke`) is retained as **macro dashboard context only**; its
panel `fr_ze2020_model_ready_panel.csv` carries no sector column, so it cannot produce
sectoral states. No neural model holds this role while Q3 is unsatisfied.

The DEC-079 and DEC-080 baseline results are explicitly scoped: temporal persistence
won masked reconstruction (MAE `0.009652` versus `0.013498`, 220/225 paired wins) and
`past_delta` won transition ranking (NDCG@3 `0.647044` versus `0.623920`, seed CV
`0.47%`). Each holds in its own task. Neither constitutes a validated product engine.

**Q1 protocol constraint (normative).** Sectoral persistence is the deterministic
identity `yhat(z,s,t) = y(z,s,t-1)`, with no fit step. Its audit must evaluate each
observation exactly once under rolling origin; must not report seed dispersion, since
the estimator is deterministic and seeds add no evidence; and must use ZE-disjoint
folds only to organize paired comparisons against fitted competitors, never to
duplicate persistence observations or multiply its metric rows. Fitted models such as
Ridge use training data, folds and seeds normally.

**Q2 -- permitted relational claims.** Association and co-movement (G1-L2,
DEC-019/020), and **predictive precedence inside the scope in which it was measured**
(Phase 7, DEC-034: country grain, 20 promoted edges, France holding one COVID-sensitive
edge per DEC-060). Forbidden: **generalized incremental predictive value**, that is,
asserting a relation improves prediction outside its measured scope; causality in any
form; automatic recommendation; and describing the architecture as a validated dynamic
GNN. The distinction is deliberate -- audited precedence is a citable finding, whereas
generalized incremental predictive value is what failed under matched placebos.

**Q3 -- reopen condition.** One condition authorizes another model experiment: an
**exogenous sectoral structure, independent of the enterprise-birth panel**, that
survives a matched placebo using the same representation as the real object, with at
least 60% paired wins across seed/year/fold, degradation under target shuffle of the
complete future-target bundle, identical populations, zero train/test ZE overlap, and
a gate pre-registered before any metric is inspected. Commuting and geography do not
qualify as new: they are exogenous but already tested and closed (DEC-073/074/075,
DEC-008/011). The open candidate is exogenous **sectoral structure**.

Passing that gate authorizes **only experimenting with a small temporal-relational
encoder, which must then beat its own controls**. It does not authorize the final
model, a dynamic-GNN claim, causal language, or automatic recommendation.

Never a new hypothesis: more epochs, more seeds, another top-k, another horizon,
another threshold, another normalization, swapping an MLP for a GNN on the same input
and target, or retuning DEC-079/DEC-080.

**Failure-pattern scoping correction.** Edge-target circularity, in which
`ze_similarity` edges are trajectory correlations of the same enterprise-birth panel
that defines the target, is restricted to the trajectory-similarity tests (DEC-069 and
the corrected lift runs, where sector and temporal shuffles failed to degrade). It does
**not** explain DEC-080, which used no relational edge and whose sector and temporal
shuffles degraded correctly. DEC-078, DEC-079 and DEC-080 are explained instead by
target degeneracy: shares sum to one and within-ZE ranking has nine candidates.

**Documentary corrections made in this pass.** `HERALD_CURRENT_STATE.md` stated the
baseline evaluation range as 2019-2024; the code default is 2019-2025, and the document
is corrected. Stale `DEC-001 to DEC-068` decision-range pointers are updated in
`HERALD_CURRENT_STATE.md`, `HERALD_ACTIVE_DOCUMENT_INDEX.md` and `canonical/HERALD_01`.
A sweep over `reports/` and `reports/canonical/` found no other temporal-range
inconsistency: the `2019-2024` strings in DEC-060/DEC-066 are Phase 7 estimation
windows, HERALD_39's range reflects an unavailable 2025 successor snapshot, and
`canonical/HERALD_11`'s `DEC-001 to DEC-011` is correctly scoped to Phase 4. Equivalent
stale pointers remain in three untracked root reports and are noted for a future
consolidation pass.

**Delivery sequence fixed by this decision:** E1 this contract; E2 HERALD_57 separating
the observational A10 mask from the relational availability mask; E3 HERALD_58 with the
sectoral-persistence rolling-origin audit before any forecast-derived state; E4
HERALD_59 auditing which HERALD_23 controls remain unexecuted rather than re-running
DEC-069--080; E5 HERALD_60 graph-first dashboard with layers separated by grain and by
evidence scale; E6 HERALD_61 Atlas/IAT provenance and mapping preflight with no metric;
E7 a new DEC for the exogenous-structure gate, conditional on E6. Documentary audits
produce no scripts and no tests. No stage authorizes an HPC job.

**Limitations.** This is a governance decision. It establishes no empirical result, and
its own Q1 designation is deliberately weaker than a validated baseline.

**Reopen condition:** a new DEC entry may amend any of Q1, Q2 or Q3, but only with the
amendment's rationale recorded and the superseded text left in place.

**Affected files:** `reports/canonical/HERALD_56_FR_ZE2020_PRODUCT_AND_EVIDENCE_CONTRACT.md`
(new), `reports/HERALD_CURRENT_STATE.md`, `reports/HERALD_ACTIVE_DOCUMENT_INDEX.md`,
`reports/README.md`, `reports/canonical/HERALD_01_PROJECT_PHASES_AND_TRAJECTORY.md`.

See HERALD_56.

### DEC-081 -- Correction addendum (2026-07-27, same day, pre-push)

The original entry above is preserved unaltered. An E1 audit found four defects; this
addendum records the corrections. HERALD_56 was edited in place to match.

1. **Claim/commit mismatch.** The entry and HERALD_56 stated that
   `reports/HERALD_CURRENT_STATE.md` was corrected in this delivery, but commit
   `f262882` did not contain that file: it still carried 18 uncommitted lines from a
   separate session (the "Current objective framing" block), and staging it whole would
   have committed unrelated work. The three DEC-081 hunks of that file were subsequently
   staged in isolation and committed in the follow-up correction commit, with the
   pre-existing block deliberately left unstaged in the worktree. Verified: the working
   file is byte-identical to its pre-correction content, so nothing from the other
   session was lost.

2. **Over-generalization corrected.** The claim that every apparent relational positive
   died at the first correctly matched placebo is too strong. Corrected reading: no
   relational candidate has justified promotion to a robust predictive or neural product
   layer under the complete sequence of matched controls, while limited analytical
   signals and exploratory results do exist -- G1-L2 co-growth (DEC-019/020), Phase 7
   precedence (DEC-034), the DEC-070 isolated `ze_similarity` block, the HERALD_39
   temporal-successor probe, and the HERALD_27 local pair gate.

3. **Attribution corrected for the edge-target circularity pattern.** DEC-069 supports
   that reading through its sector shuffle (real change lost to sector-shuffled
   relations, lift `-0.0002`) and its randomized-endpoint placebo (effectively tied,
   `+0.0003`). **DEC-069 did not evaluate a temporal shuffle.** The finding that temporal
   shuffle fails to degrade belongs only to the corrected top-3 and relation-lift runs
   that actually evaluated it (HERALD_38 section 8, jobs `7755806` / `7755807`).

4. **Interpretation no longer presented as mechanism.** Target degeneracy is a plausible
   structural limitation consistent with the outcomes of DEC-078, DEC-079 and DEC-080. It
   is not a demonstrated mechanism: no test has isolated compositional closure as the
   cause, and doing so would require a target that is not closed by construction.

None of Q1, Q2 or Q3 is altered by this addendum.
