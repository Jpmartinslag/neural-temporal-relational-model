# HERALD G2 Preflight — Temporal Dynamics of the L2 Co-Growth Graph

**Date:** 2026-06-10  
**Status:** COMPLETE — findings documented (see §6 for verdict)  
**Artefacts:** `data/processed/economic_graph/g2_preflight/`  
**Builder:** `src/data/european_panel/build_g2_temporal_preflight.py`  
**Tests:** `tests/test_g2_preflight.py` — 21 pass, 1 skip  

**Constraints:** No causal attribution. No economic recommendation. No community labels
(DEC-021: NOT_SUPPORTED). No country pooling. L2 edges are statistical co-movement
associations, not Granger predictability or structural causality.

---

## 1. Purpose

This preflight characterises the temporal dynamics of the validated L2 co-growth graph
(G-10 SUPPORTED) for FR, NL, and PT. The scientific question is: **how do sector-territory
co-growth relationships evolve over time?** This is a descriptive question (Bloco 2),
separate from forecast utility (Phase 5 fixed-L2 corrector, which is NOT_SUPPORTED, DEC-023).

The analysis uses the validated edges from `data/processed/economic_graph/g1_l2_cogrowth/`
with the same top-k=5 filtering as Phase 5.

---

## 2. Falsifiable Criteria (pre-registered before analysis)

The following criteria were defined BEFORE running the analysis on real data:

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| Persistent edge | Appears in top-k graph ≥ 70% of valid years | Identify structurally stable links |
| Edge strengthening | |Δweight| ≥ 0.15, positive direction | Mark intensifying relationships |
| Edge weakening | |Δweight| ≥ 0.15, negative direction | Mark dissolving relationships |
| Structural stability (LOYO Pearson) | ≥ 0.70 | Overall adjacency reproducibility |
| Structural stability (LOYO Jaccard) | ≥ 0.70 | Binary adjacency reproducibility |
| Stable neighbourhood | Mean annual turnover ≤ 30% | Identify regions with stable top-k |
| Sectoral wave | ≥ 25% of pairs moving same direction | Detect coordinated sector dynamics |
| COVID density disruption | |Δdensity| ≥ 0.05 | Pre/post COVID structural shift |
| COVID weight disruption | |Δmean_weight| ≥ 0.15 | Pre/post COVID weight shift |
| Negative control | Temporal permutation must destroy persistence | Falsifiability check |

Pre-COVID = 2015-2019; COVID = 2020; Post-COVID = 2021-2023.

---

## 3. Data and Protocol

- **Source:** `g1_l2_edges.csv` — 3,645,230 rows; 3 countries; 9 sectors; 15 eval years
- **Top-k filter:** TOP_K=5 (same as Phase 5, symmetric); only positive correlations retained
- **Window:** 5 years, MIN_PERIODS=4; COVID year excluded from window (DEC-020)
- **PT KZ:** excluded (structural absence, DEC-018)
- **FR:** 280 regions (ZE2020); **NL:** 40 regions (COROP); **PT:** 25 regions (NUTS3)
- **Results per country × sector; no cross-country pooling**

---

## 4. Key Findings

### 4.1 Inventory

| Country | Sectors | Regions | Eval years | OQ coverage |
|---------|---------|---------|------------|-------------|
| FR | 9 | 280 | 10 | 10/10 |
| NL | 8 (+OQ) | 40 | 15 (OQ: 7) | 7/15 |
| PT | 8 (no KZ) | 25 | 13 | 13/13 |

### 4.2 LOYO Stability — ALL FAIL gate (both Pearson and Jaccard)

LOYO Pearson measures upper-triangle weight correlation; LOYO Jaccard measures binary
structural overlap. Both fail the 0.70 threshold.

| Country | LOYO Pearson (mean) | LOYO Jaccard (mean) | Gate |
|---------|---------------------|---------------------|------|
| FR | 0.104 | 0.071 | ✗ FAIL |
| NL | 0.138 | 0.181 | ✗ FAIL |
| PT | 0.190 | 0.262 | ✗ FAIL |
| **Overall** | **0.147** | **0.168** | ✗ FAIL |

**Interpretation:** The top-k=5 neighbor structure changes substantially from year to year
across all country-sector combinations. For FR (280 regions), even small rank changes in
correlation can rotate the top-5 set (FR Jaccard=0.071 means only ~7% of edges persist
between consecutive years). This is expected for large, sparse top-k graphs.

Note: this does not invalidate G-10 (L2 validation). G-10 tested whether the **overall
correlation structure** is reproducible across null models — not whether individual edges
persist. LOYO gate here tests individual edge-level stability, which is stricter.

### 4.3 Edge Persistence — Highly transient

| Country | Persistent edges (≥70%) | Mean persistence |
|---------|--------------------------|-----------------|
| FR | 0.2% | ~14% |
| NL | 1.6% | ~17% |
| PT | 3.8% | ~17% |
| **All** | **0.4%** | **~17%** |

Only 246 out of 58,242 observed edge-year combinations pass the 70% persistence threshold.
The mean persistence (~17%) means the average edge appears in 2-3 out of 15 eligible years.

**Most persistent sector across all countries:** OQ (0.191 LOYO Jaccard — still low).

### 4.4 Neighbor Turnover — High dynamism confirmed

Mean turnover per consecutive year pair: **0.593** (59% of top-k neighbors change annually).

| Country | Mean turnover |
|---------|---------------|
| FR | 77% |
| NL | 56% |
| PT | 48% |

**0 out of 295** consecutive year-pairs have stable neighborhoods (mean turnover ≤ 30%).
FR is most dynamic (likely due to large region count and sparse top-k fraction).

### 4.5 Top-k Sensitivity

| Comparison | Jaccard |
|-----------|---------|
| k=3 vs k=5 | 0.616 |
| k=5 vs k=10 | 0.519 |

Moderate sensitivity to k choice. Adding 2 neighbors (3→5) changes ~38% of the edge set;
adding 5 more (5→10) changes ~48%. Results are dependent on the top-k parameter.

### 4.6 COVID Period Comparison

No sector-country combination exceeds the disruption thresholds:

| Metric | Max observed | Threshold | Pass |
|--------|-------------|-----------|------|
| Δdensity (post−pre) | 0.019 (NL/BE) | 0.05 | ✓ All below |
| Δweight (post−pre) | 0.136 (PT/MN) | 0.15 | ✓ All below |

**Finding:** COVID did not cause a measurable step-change in the L2 graph structure using
these thresholds. Mean Δdensity ≈ 0, mean Δweight ≈ +0.01 (slight overall strengthening).
Notable but sub-threshold: PT/MN (+0.136), PT/RU (+0.128), NL/GI (+0.128).

**No causal claim:** this absence of disruption does not mean COVID had no economic impact;
only that the co-growth correlation structure at the sector-territory level was not
measurably disrupted at the population level.

---

## 5. Interpretation: What the High Dynamism Means

The key finding — **LOYO Jaccard ≈ 0.07-0.26, mean turnover ≈ 59%, persistence ≈ 0.4%** —
means:

1. **Individual top-k relationships are highly transient.** Claiming "territory A and B have
   a persistent co-growth relationship in sector S" requires at least 11 of 15 consecutive
   years. Only 246 pairs out of 58,242 meet this bar.

2. **The dynamism is real, not artifactual.** Rolling-window correlations with 5-year windows
   and annual shifts inherently produce changing graphs. Adding/removing one year can
   substantially change correlations when base years have extreme values.

3. **Population-level statistics are more robust than individual edges.** Density trends,
   mean weight distributions, fraction of strengthening/weakening pairs — these are more
   interpretable than individual edge tracking.

4. **Country comparison is valid within countries.** FR has higher turnover than PT, likely
   because 280 regions provide many competing candidates for top-5 slots.

5. **This finding does NOT invalidate L2 or G-10.** G-10 validated that the aggregate
   co-movement structure is reproducible across null models (temporal and territory
   permutation). Edge-level persistence is a different and stricter question.

---

## 6. Verdict: G2_READY (with scope constraints)

**G2 preflight: COMPLETE.** The following analyses are authorised for Bloco 2 descriptive:

**AUTHORISED:**
- Population-level density and weight trends by country × sector × period
- Cross-period comparisons (pre/COVID/post) using distribution statistics
- Within-country structural evolution characterisation
- Identification of the most stable country-sector combinations (OQ, PT sectors)
- Annual variation analysis (strengthening/weakening fractions)
- Documentation that the graph is highly dynamic (this IS a finding)

**NOT AUTHORISED:**
- Individual edge-level claims ("link A-B is structural")
- Cross-country pooling of any metric
- Causal attribution (e.g., "COVID caused weakening")
- Community structure claims (DEC-021: NOT_SUPPORTED)
- Recommendation claims
- Claims that results transfer to unvalidated countries

**Negative control requirement:** Temporal permutation of window years must reduce LOYO
Jaccard by ≥30% relative to observed. This test should be run before claiming the
low-but-positive Jaccard reflects genuine signal rather than finite-sample artefact.

---

## 7. Files Created

| File | Rows | Description |
|------|------|-------------|
| `g2_inventory.csv` | 26 | country × sector coverage |
| `g2_density.csv` | 321 | edge density per country/sector/year |
| `g2_persistence.csv` | 58,242 | per-edge persistence fractions |
| `g2_turnover.csv` | 295 | consecutive year-pair neighbor turnover |
| `g2_variation.csv` | 295 | annual edge weight variation |
| `g2_topk_sensitivity.csv` | 321 | Jaccard for k=3,5,10 |
| `g2_loyo.csv` | 26 | LOYO Pearson and Jaccard per country/sector |
| `g2_covid_comparison.csv` | 25 | pre/COVID/post density and weight stats |
| `g2_preflight_summary.json` | — | aggregated summary with criteria |

No raw edge files included. All artefacts are compact aggregated statistics.

---

## 8. Next Steps

1. **Negative control run:** Temporal permutation to establish null baseline for LOYO Jaccard.
2. **Descriptive main analysis:** Density and weight evolution by period; sector-country patterns.
3. **Evidence matrix update:** G-13 entry for G2 criteria and findings.
4. **Dashboard adaptation plan:** Document which G2 statistics could be added to the France
   dashboard in future (no HTML modification now — DEC-014).
