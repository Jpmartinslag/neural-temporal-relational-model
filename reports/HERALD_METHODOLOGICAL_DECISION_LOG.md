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
