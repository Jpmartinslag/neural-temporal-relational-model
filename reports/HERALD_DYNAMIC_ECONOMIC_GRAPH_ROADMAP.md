# HERALD — Dynamic Economic Graph Roadmap

**Created:** 2026-06-10  
**Revised:** 2026-06-10 (data inventory corrected after panel inspection)  
**Status:** PLANNING — G0 gate partially satisfied; implementation not yet authorized  
**Audit classification:** `PASS_WITH_LIMITATIONS` (planning document; empirical validation pending)

---

## Methodological Audit — This Document

| Item | Value |
|------|-------|
| Scientific question | Can a dynamic economic graph capture sector-territory relations that explain enterprise-birth dynamics and eventually support territorial recommendations? |
| Hypothesis | Observable sector-territory relations learned from FR/NL/PT enterprise-birth A10 (2008–2023) encode economic proximity structures that are temporally stable, economically coherent, and differ from geographic contiguity — and these structures can be validated independently of WMAPE |
| Unit of analysis | NUTS3 territory × economic sector (A10 pair, 9 common business sectors) |
| Population | FR (306 ZE), NL (40 COROP), PT (25 NUTS3); BE as employment-only complement |
| Period | FR 2012–2024; NL 2015–2025; PT 2008–2024; sector bridge via bd_hgnace_r 2019–2023 |
| Sources | Canonical panels (`france_panel.csv`, `nl_panel.csv`, `pt_panel.csv`); `bd_hgnace_r_raw.csv` (FR/NL/PT sector births 2019-2023); national employment qtensors; mobility surveys (NL, BE, PT) |
| Transformations | Causal lagged features only; no t-year information in edge construction |
| Assumptions | Sector co-growth patterns across NUTS3 encode productive proximity; T≈10-14 constrains method complexity |
| Possible confounders | MAUP; COVID 2020; NUTS revision instability (FR codes); national classification differences |
| Leakage risks | Edge weights computed with t-year data = leakage; all graph construction uses data through t-1 |
| Claims permitted | Graph reveals economic structure (associative); graph validated independently of WMAPE |
| Claims prohibited | Causal relations between sectors; policy recommendations without intervention study |
| Decision | Roadmap approved for planning; implementation blocked pending full G0 gate |

---

## Context: Why This Roadmap Exists

Phases 4P and 4Q tested geographic queen-contiguity lags on the Italian harmonized panel and found no predictive gain (gate FAIL, p=0.19 and p=0.32 respectively). The **geographic graph branch is closed** under the current 2008–2020 data.

This closure does **not** imply that all graph representations are useless. It implies that one specific class of spatial lag (geographic contiguity, linear, first-order, counts and growth) does not provide predictive signal in the current data and protocol.

The new direction is a qualitatively different scientific question:

> **How do sector-territory economic relations evolve over time, and what do those dynamics reveal about growth, crisis, stagnation and recovery?**

This is primarily an **interpretive and explanatory** task. Forecasting improvement is a secondary, downstream question. The recommendation system is the terminal use case.

---

## Real Data Inventory (verified 2026-06-10 from canonical panels)

### Enterprise births A10 (sector-level)

| Country | mask_sector_a10 | Source | Years available | Notes |
|---------|----------------|--------|----------------|-------|
| FR | 0.923 | SIDE/SIRENE NAF→A10, canonical `france_panel.csv` | 2012–2024 | 92.3% rows; Corsica/DOM excluded |
| NL | 1.000 | CBS SBI→A10, canonical `nl_panel.csv` | 2015–2025 | Complete |
| PT | 0.941 | INE CAE→A10, canonical `pt_panel.csv` | 2008–2024 | 94.1% rows |
| BE | 0.000 | StatBel VAT (births only, A10 not in panel) | — | Enterprise births A10 absent |
| IT | 0.000 | bd_size_r3 = aggregate `B-S_X_K642`, no A10 | — | **A10 not available at NUTS3** |
| AT | 0.000 | bd_size_r3 = aggregate `B-S_X_K642`, no A10 | — | **A10 not available at NUTS3** |

> **Critical correction:** `bd_size_r3` in its current form uses NACE aggregate `B-S_X_K642` (all market activities except financial holding). It provides total enterprise births and stock for the Path H panel, but does **not** supply A10 territorial breakdown for IT or AT. Any earlier claim that "AT has complete A10" or "IT has A10" is incorrect and removed from this document.

### Employment A10 (qtensor)

| Country | mask_employment | Source | Notes |
|---------|----------------|--------|-------|
| FR | 1.000 | URSSAF effectifs, `france_panel.csv` | Full ZE×A10×lag |
| NL | 1.000 | CBS 83582NED, `nl_panel.csv` | Full COROP×A10 |
| PT | 1.000 | Eurostat `nama_10r_3empers` + ARDECO, `pt_panel.csv` | Full NUTS3×A10 |
| BE | 1.000 | ONSS Q4, `belgium_qtensor_jobs_panel.csv` | Employment A10 available; births A10 absent |
| IT | 0.000 | Not in panel | |
| AT | 0.000 | Not in panel | |

### Sector bridge: Eurostat bd_hgnace_r

`data/external/eurostat_business_demography/bd_hgnace_r_raw.csv`

| Country | Years | Indicators | Coverage | Notes |
|---------|-------|-----------|---------|-------|
| FR | 2019–2023 | ENT_BRTH_NR, ENT_DTH_NR, ENT_NR, EMP_NR | NUTS3 | Sector births available; not yet mapped to A10 |
| NL | 2019–2023 | ENT_BRTH_NR, ENT_DTH_NR, ENT_NR, EMP_NR | NUTS3 | Sector births available |
| PT | 2019–2023 | ENT_BRTH_NR, ENT_DTH_NR, ENT_NR, EMP_NR | NUTS3 | Sector births available |

> `bd_hgnace_r` uses NACE sections (B-E, F, G, H, I, J, K_L, M_N, P_Q, R_S_X_S94) — not identical to A10 but mappable. This source extends temporal coverage for FR/NL/PT births by sector beyond the canonical panels. It should be used as a **complementary source**, not a replacement for existing sector panels.

### Mobility / commuting

| Country | Source | Location | Notes |
|---------|--------|----------|-------|
| NL | CBS 85481NED COROP commuting 2022 | `data/external/netherlands/raw/commuting/85481NED_corop_commuting_2022.json` | Available |
| BE | Census 2011 municipal commuters | `data/external/belgium/raw/commuting/TU_CENSUS_2011_COMMUTERS_MUNTY.txt` | Available; dated 2011 |
| PT | INE commuting survey | `data/external/portugal/raw/ine_commuting_0012340.json` | Available |
| FR | Not yet downloaded | — | ZE boundaries defined partly by commuting flows |
| IT | Not yet downloaded | — | |
| AT | Not yet downloaded | — | |

### Other existing assets

| Asset | Location | Countries |
|-------|----------|-----------|
| NUTS3 geometries (ZE2020/NUTS3) | `data/external/nuts3_2021_eurostat.geojson` | All EU |
| Stock (enterprise count lag) | All canonical panels | FR/NL/BE/PT/IT/AT |
| EU macro signals (partial) | All canonical panels | FR/NL/PT (partial) |
| Causal lagged features | All canonical panels | All |

### Common sector A10 columns in all panels

All panels share 9 common business sectors (agriculture excluded from common set):

`sector_BE` · `sector_FZ` · `sector_GI` · `sector_JZ` · `sector_KZ` · `sector_LZ` · `sector_MN` · `sector_OQ` · `sector_RU`

Agriculture (A/AZ) is absent from the common set — coverage is insufficient across countries to include it in the initial graph nucleus.

---

## Strategic Architecture: Three Blocos

### Bloco 1 — Temporal Forecasting (active)

Persistence is the best-balanced LOCO baseline (PT/IT/AT harmonized panel, Phase 4N). No architecture restart. Permitted improvements: non-graph frugal country-specific Ridge variants; conformal prediction intervals; post-2020 window extension when data available.

### Bloco 2 — Dynamic Economic Graph (this document)

See below.

### Bloco 3 — Recommendation (terminal, not started)

Requires Bloco 1 + Bloco 2 validated. Cannot be claimed as a current capability.

---

## Bloco 2 — Dynamic Economic Graph

### Node definition (proposed, pending G0 formal commitment)

- **Node:** territory × sector pair `(NUTS3_id, sector_A10)`
- **Node attributes (observed):** enterprise births (lag1, lag2), stock_lag1, employment (lag1), growth_1y (causal), growth_2y (causal), mask flags
- **Snapshot:** annual (year t; all attributes from data through t-1)
- **Missing:** `NaN + mask_sector_a10`, never zero-imputed

### Edge definition (proposed, pending G0 formal commitment)

Edges are organized in layers, from most to least interpretable:

| Layer | Semantic | Data | Leakage-safe |
|-------|---------|------|-------------|
| 1. Sector co-presence | Both sectors present in same territory | births/stock by sector | Yes (lagged) |
| 2. Economic structure similarity | Pearson/cosine similarity of sector-share vectors at t-1 | sector births distribution | Yes |
| 3. Causal co-growth | Correlation of sector growth rates, computed over rolling past window | causal growth features | Yes (rolling past only) |
| 4. Commuting / mobility | Functional area connection (worker flows) | NL/BE/PT commuting files | Yes (static or lagged) |
| 5. Geographic adjacency | Queen contiguity control | NUTS3 shapefile | Yes (static) |

> **Geographic adjacency (layer 5)** is kept only as a **spatial control and null model baseline** — it was tested and rejected as a predictive feature in Phase 4P/4Q.  
> **Edge weights** represent association or similarity, never structural economic causality.  
> **Negative edges** are permitted only when the method (e.g. partial correlation) and economic interpretation explicitly justify them.

### Country nucleus for G1

| Role | Countries | Justification |
|------|-----------|--------------|
| **Sector nucleus (G1 core)** | FR, NL, PT | mask_sector_a10 > 0.9; births A10 confirmed in canonical panels |
| **Employment complement** | BE | Employment A10 available (`belgium_qtensor_jobs_panel.csv`); births A10 absent |
| **Path H aggregate only** | IT, AT | mask_sector_a10 = 0; bd_size_r3 provides only aggregate NACE; remain in enterprise_birth LOCO panel |

IT and AT are not excluded from the project — they remain canonical LOCO domains for total enterprise birth. They are excluded from the **sector graph nucleus** because sector A10 data does not exist for them at NUTS3 level.

---

### G0 — Conceptual Contract Gate

**Current gate status: 4/10 items formally satisfied. Implementation BLOCKED until all 10 are checked.**

| # | Item | Status | Evidence |
|---|------|--------|---------|
| 1 | Formal node and edge definition with semantic meaning | ⬜ OPEN | Proposed above; pending formal commitment in a signed G0 document |
| 2 | Data confirmed available for ≥2 countries at required granularity | ✅ DONE | FR mask_sector_a10=0.923, NL=1.000, PT=0.941 (verified from panels 2026-06-10) |
| 3 | Falsifiable hypothesis stated | ⬜ OPEN | Proposed above; pending explicit pre-registration |
| 4 | Baseline defined (persistence or Ridge) | ✅ DONE | Persistence (Phase 4N): IT 0.055, AT 0.075, PT 0.132, balanced 0.087 |
| 5 | Null model specified (permuted graph, configuration model) | ⬜ OPEN | Permutation approach identified but not formally specified |
| 6 | Causal temporal protocol written (no t leakage in edge construction) | ✅ DONE | Enforced since Phase 4E; all edge features use data through t-1 |
| 7 | Stability metrics pre-specified | ⬜ OPEN | Not yet formally pre-specified |
| 8 | Acceptance criteria pre-registered | ⬜ OPEN | Not yet |
| 9 | Permitted scientific claims listed | ✅ DONE | Evidence Matrix + README claims gate |
| 10 | Post-experiment audit plan written | ⬜ OPEN | Not yet |

Items 1, 3, 5, 7, 8, 10 must be completed in the G0 contract document before implementation begins.

---

### G1 — Observable Graph (first implementation target)

Build edges from directly observed data — no statistical estimation, no learning.

**Recommended implementation order:**

1. **Sector distribution similarity** (FR/NL/PT): cosine similarity of sector-share vectors at t-1. Simple, auditable, no estimation. Produces a territory-to-territory graph for each year.
2. **Sector co-growth correlation** (rolling 5-year window): Pearson correlation of A10 sector growth rates across territories. Rolling window keeps it causal.
3. **Commuting-weighted territory graph** (NL/BE/PT): Use existing commuting files to define functional-area proximity between territories.

Do **not** start with GLASSO, TVGL, DSBM, or any GNN at G1. These are conditional on G1 validation passing.

---

### G2 — Learned Sparse Graph (conditional on G1 validation)

Learn conditional dependence structure. **Only after G1 is validated under G4.**

**T≈10–14 annual observations is a severe constraint.** With p=40–306 territories × 9 sectors, direct estimation is impossible. The following ordering respects this constraint:

| Priority | Method | Why | Constraint |
|----------|--------|-----|-----------|
| 1 | Rolling Pearson/Spearman (5-year window) | No estimation; O(p²) correlations | Always feasible |
| 2 | Sparse VAR-Granger (L1) with **explicit causality disclaimer** | Low-rank; regularized | T≥2p needed; aggregate sectors to reduce p |
| 3 | GLASSO with strong regularization (λ >> default) | Sparse; T>p if sector-aggregated | p must be << T; test at country-sector level |
| 4 | TVGL (Hallac et al. 2017) | Detects structural change | T≥15 recommended; treat as experimental |
| 5 | DSBM (Matias & Miele 2017) | Community evolution | K≤5 communities; T≥10 | 
| 6 | NMF (temporal) | Interpretable factors | Low-rank; always feasible |
| 7 | Graph structure learning / GNN end-to-end | Rich but overparameterized | T>>100 required; treat as future work |

> Methods 1–3 are **primary candidates** for this project. Methods 4–6 are **conditional experiments**. Method 7 is **future work** only.  
> **Granger predictability ≠ economic causality**. All Granger/VAR edges must be labeled "Granger-predictive edge" in every output.

---

### G3 — Economic Dynamics

Detect and characterize economic dynamics from the evolving graph.

| Phenomenon | Detection method | Notes |
|------------|-----------------|-------|
| Growth wave | Increasing edge density + positive community growth | With T≈13, at most 1–2 structural breaks per edge |
| Crisis | Community fragmentation + edge disappearance | 2009 and 2020 are anchor events |
| Stagnation | Persistent low-weight edges; static community | Compare 2012–2014 to 2016–2019 |
| Recovery | Re-emergence of edges after break | Post-2009 and post-2020 patterns |
| Structural break | CUSUM or BOCPD on edge weight time series | Anchor vs COVID outlier treatment |
| Sector shock propagation | Temporal diffusion of anomaly | Aggregate to reduce noise |

> 2020 is a known outlier (COVID). Always report sensitivity excluding 2020.

---

### G4 — Graph Validation (independent of WMAPE)

| Criterion | Method | Threshold type |
|-----------|--------|---------------|
| Sparsity | Edge density vs configuration model | Exploratory threshold; report and interpret |
| Bootstrap temporal stability | Re-estimate on leave-one-year-out; Jaccard similarity | Exploratory threshold (≥0.5 as starting point; justify if different) |
| Temporal stability | Consecutive-year edge overlap | Descriptive metric |
| Permutation robustness | Edge weights vs within-country/within-sector permuted null | p ≤ 0.05 per edge (FDR-corrected); pre-registered |
| Known-relation recovery | Edges expected from economic literature | Descriptive; report recovery rate with confidence interval |
| Geographic coherence | Moran's I on sector-similarity edge weights | Descriptive |
| Economic coherence | Sectors known to co-locate compared to graph | Literature-based; descriptive |
| Community persistence | NMI year-over-year | Descriptive metric |
| Null model comparison | Real graph vs permuted-temporal + configuration model | Pre-registered test |
| MAUP sensitivity | Re-run at NUTS2 level if data available | Sensitivity analysis; report |
| COVID robustness | Re-run excluding 2020 | Sensitivity; report delta |

> **All thresholds labeled.** No threshold is universal. Pre-registered thresholds apply only to the specific test for which they are pre-registered.

### Null models (corrected)

Priority null models, from most to least preferred:

1. **Within-country/within-sector temporal permutation** — shuffle years within each territory-sector pair; preserves marginal distributions
2. **Territory-identity permutation** — relabel which territory is which; preserves overall structure
3. **Configuration model** — preserve degree sequence; randomize connections
4. **Column permutation** (as used in Phase 4P/4Q) — equivalent to `P W P^T`; preserves degree multiset
5. **Erdős-Rényi** — last resort baseline; least informative; must not be primary null

> Geographic contiguity null model must be kept separate as a **domain control** to distinguish "economic graph" from "geographic graph."

---

### G5 — Explanation

Produce human-readable outputs:

1. Edge ranking by weight + bootstrap stability
2. Influence maps (degree centrality, PageRank)
3. Community maps with economic labels (per year)
4. Temporal edge evolution: birth, death, weight change
5. Correlation of graph communities with forecast residuals (descriptive, not causal)

> **Attention weights require permutation test before being called explanations.** Any GNN attention used in G6 must be validated against a null (random-graph) baseline before being interpreted.

---

### G6 — Integration with Forecasting (conditional on G1–G5)

Only after G1–G5 are complete and validated under G4.

- Use graph as a regularizer or residual correction component.
- Apply same gate as Phase 4P/4Q: ≥1% gain vs persistence, p ≤ 0.05 graph-control, ≥5/T yearly wins.
- If gain is not demonstrated: graph remains an interpretive tool only. Report honestly.

---

## Bloco 3 — Economic Recommendation (terminal use case, NOT STARTED)

Requires Bloco 1 + Bloco 2. Cannot be claimed as current capability.

Components when developed:
- Forecast of territorial economic trajectory (Bloco 1)
- Sector-territory economic graph validated (Bloco 2)
- Existing territorial capacity (sector employment, enterprise stock)
- Sector relatedness (product space, I-O, skill similarity — Pachot et al. 2021/2022)
- Productive compatibility and risk quantification
- Recommendation explanation in economic terms

---

## G0 Gate: Next Steps to Reach 10/10

The 6 remaining open items require a dedicated G0 contract document:

1. **Item 1** — Formally commit to `territory × sector A10` as node definition, with the edge layer structure above
2. **Item 3** — State the falsifiable hypothesis: *"The sector co-growth similarity graph (FR/NL/PT, rolling 5-year window) is more stable under bootstrap resampling than the geographic contiguity graph, and its community structure is consistent with known economic geography"*
3. **Item 5** — Formally specify null models in priority order (as above)
4. **Item 7** — Pre-specify stability metrics with justification for each threshold
5. **Item 8** — Pre-register acceptance criteria for each validation test
6. **Item 10** — Write post-experiment audit plan

Write these in a new document: `reports/HERALD_G0_FORMAL_CONTRACT.md`

---

## Summary: Three Scientific Tracks

| Track | Status | Immediate action |
|-------|--------|-----------------|
| Bloco 1: Temporal forecasting | Active | Non-graph improvements; conformal intervals; no architecture restart |
| Bloco 2: Economic dynamic graph | Blocked at G0 (4/10) | Write G0 formal contract; verify bd_hgnace_r A10 mapping |
| Bloco 3: Recommendation | Not started | Deferred until Bloco 2 complete |
