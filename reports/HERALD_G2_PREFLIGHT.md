# HERALD G2 Preflight — Temporal Dynamics of the L2 Co-Growth Graph

**Date:** 2026-06-10 (preflight) / 2026-06-11 (corrected controls)
**Status:** COMPLETE — corrected controls and COVID audit run 2026-06-11
(DEC-024c/d); aggregate signal is COVID-robust only for FR;
G2_EDGE_STABILITY_NOT_SUPPORTED
**Artefacts:** `data/processed/economic_graph/g2_preflight/`
**Builder:** `src/data/european_panel/build_g2_temporal_preflight.py`
**Tests:** `tests/test_g2_preflight.py` — 42 pass, 1 skip

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

## 2. Falsifiable Criteria (pre-registered before analysis, DEC-024)

The following criteria were defined BEFORE running the analysis on real data:

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| Persistent edge | Appears in top-k graph ≥ 70% of valid years | Identify structurally stable links |
| Edge strengthening | \|Δweight\| ≥ 0.15, positive direction | Mark intensifying relationships |
| Edge weakening | \|Δweight\| ≥ 0.15, negative direction | Mark dissolving relationships |
| Structural stability (LOYO Pearson) | ≥ 0.70 | Overall adjacency reproducibility |
| Structural stability (LOYO Jaccard) | ≥ 0.70 | Binary adjacency reproducibility |
| Stable neighbourhood | Mean annual turnover ≤ 30% | Identify regions with stable top-k |
| Sectoral wave | ≥ 25% of pairs moving same direction | Detect coordinated sector dynamics |
| COVID density disruption | \|Δdensity\| ≥ 0.05 | Pre/post COVID structural shift |
| COVID weight disruption | \|Δmean_weight\| ≥ 0.15 | Pre/post COVID weight shift |
| Negative control gate | ≥2 countries, ≥50% sectors FDR-significant (BH q=0.05), observed > null median | Validates temporal signal vs finite-sample artefact |

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

---

## 7. Corrected Controls (DEC-024c, 2026-06-11)

**Builder:** `src/data/european_panel/build_g2_corrected_controls.py`
**Source:** `sector_panel_fr_nl_pt.csv` (NOT `g1_l2_edges.csv` — see prior control §7.2)
**Protocol:** 199 permutations N1 + 199 permutations N2, full pipeline per permutation;
BH/FDR q=0.05 per metric × null family; seeds N1=42, N2=137.

### 7.1 Metrics

| Metric | Definition | Values (k=5) |
|--------|------------|-------------|
| **M1** | Consecutive Jaccard J(G_t, G_{t+1}); mean/median/min | FR 0.18–0.19 · NL 0.37–0.49 · PT 0.45–0.51 |
| **M2** | Mean pairwise Jaccard over ALL (t,s) year pairs | FR 0.06–0.06 · NL 0.16–0.26 · PT 0.24–0.26 |
| **M3** | True LOYO reconstruction (obs only, null BLOCKED) | FR 0.287 · NL 0.500 · PT 0.578 |

M1/M2 all far below 0.70 stability threshold. M3 null is BLOCKED.

### 7.2 Null families

**N1 — Temporal:** permute `observation_year` within each territory × sector column in the source
growth matrix (reuses `permute_growth_temporal` from `build_g1_l2_cogrowth.py`). Tests whether
temporal ordering of growth rates is necessary for the observed Jaccard values.

**N2 — Territory row-wise:** within each `observation_year`, permute which territory receives
which growth value (reuses `permute_growth_territory` from `build_g1_l2_cogrowth.py`). Tests
whether specific territory co-movement identities are necessary.

**N2 column permutation — DEGENERATE (documented):** Permuting entire territory columns
uniformly across all years is mathematically equivalent to graph relabeling. For M1/M2
Jaccard metrics, the null variance = 0.0 and p = 1.0 always (verified empirically for
NL and PT; null std = 0.0 to 8 decimal places). Column permutation is kept in the module
for documentation; the gate uses N2 row-wise.

### 7.3 Results

| Country | Sectors | N1+N2 FDR-sig (M2) | Country signal gate | Stability gate (M2≥0.70) |
|---------|---------|---------------------|---------------------|--------------------------|
| FR | 9 | 9/9 (all p=0.005=floor) | ✓ PASS | ✗ FAIL (max 0.064) |
| NL | 9 | 5/9 (BE,FZ,GI,LZ,MN) | ✓ PASS (55.6%≥50%) | ✗ FAIL (max 0.260) |
| PT | 8 | 0/8 | ✗ FAIL | ✗ FAIL (max 0.261) |

**Sensitivity scenario without observation year 2020 — Signal:** 2/3 countries
pass (FR+NL). DEC-024d shows that the main scenario with 2020 instead passes
with FR+PT; this result is not a COVID-robust global promotion.
**Global — Stability:** 0/3 countries pass → **G2_EDGE_STABILITY_NOT_SUPPORTED**

### 7.4 Floor-p diagnostics (FR)

FR all p=0.005 (minimum with 199 perms). Mandatory check:
- Null variance: std ~0.0013–0.0015 (NOT zero; 199 unique values per sector)
- obs_above_all_null: True for all FR sectors under N1 and N2
- No degeneracy — the floor values reflect genuine signal (FR observed M2 above all 199 nulls)

### 7.5 Sensitivities (k=3,5,10)

| k | FR M2 range | NL M2 range | PT M2 range |
|---|------------|------------|------------|
| 3 | 0.043–0.051 | 0.103–0.191 | 0.168–0.185 |
| 5 | 0.059–0.064 | 0.155–0.260 | 0.243–0.261 |
| 10 | 0.087–0.093 | 0.259–0.387 | 0.422–0.445 |

M2 increases with k (larger top-k sets share more edges). Direction consistent across k.

### 7.6 Reconciliation: G1-L2 0.78 vs G2 M2 0.06–0.26

| | G1-L2 | G2 M2 |
|-|-------|-------|
| Object | Dense Pearson of ALL region-pair correlations | Binary top-k=5 adjacency per country×sector |
| Metric | Pearson of consecutive dense upper-triangle vectors | Mean Jaccard over all year pairs |
| Sparsification | None (all pairs, including negative) | Top-k=5 only |
| Granularity | Per country (all sectors pooled) | Per country × sector |
| Values | FR 0.782 · NL 0.789 · PT 0.778 | FR 0.06 · NL 0.17 · PT 0.25 |

**Compatible finding:** Full Pearson structure is smooth and stable (0.78) while specific top-5
connections are volatile (0.06–0.26). G1-L2 measures aggregate co-movement; G2 measures
identity of extreme edges. Not a contradiction.

### 7.7 Verdict

**Scenario result without observation year 2020:** observed temporal Jaccard
exceeds both N1 and N2 nulls for FR (9/9) and NL (5/9). The COVID audit below
supersedes any unconditional interpretation: only FR retains the same country
decision in both scenarios.

**G2_EDGE_STABILITY_NOT_SUPPORTED** — M2 ranges 0.06–0.26 for all sectors across all countries,
far below the 0.70 threshold. Individual top-k connections are highly transient.

**PT:** No sector achieves significance under both N1 and N2. PT temporal signal cannot be validated
under this protocol.

**M3 null: BLOCKED.** M3 observed values (FR 0.287, NL 0.500, PT 0.578) indicate moderate LOYO
reconstruction stability, but these cannot be contrasted against a null distribution.

Language: "associação estatística temporal observada"; NOT "estrutura estável" or "causalidade".
Individual edge claims remain NOT authorised. Cross-country pooling prohibited.

### 7.9 COVID sensitivity audit (DEC-024d)

The corrected control was rerun with identical seeds and parameters in two
scenarios. The main scenario includes `observation_year=2020`; the sensitivity
scenario excludes only that observation from later rolling windows.
`available_for_forecast_year=2020` remains in both.

| Country | With 2020 | Without 2020 | Changed sectors | Classification |
|---|---:|---:|---|---|
| FR | 9/9 | 9/9 | none | COVID_ROBUST |
| NL | 4/9 | 5/9 | BE, LZ, RU | COVID_SENSITIVE |
| PT | 4/8 | 0/8 | BE, GI, JZ, LZ | COVID_SENSITIVE |

Although the global 2/3 gate passes in both scenarios, the passing countries
change from FR+PT to FR+NL. Therefore, only FR supports a COVID-robust aggregate
temporal-coherence claim. G-13 remains `PARTIALLY_SUPPORTED`, with NL and PT
reported as sensitivity results rather than general evidence.

Full audit: `reports/HERALD_G2_COVID_SENSITIVITY_AUDIT.md`.

---

### 7.8 Prior control (superseded, preserved as historical record)

**Method (INVALID, commit cc48924):** Permuted pre-computed Pearson weights (territory-pair rows
of matrix W from `g1_l2_edges.csv`), NOT source growth series. Invalid null distribution.
p=0.005, 26/26 FDR-significant — **not valid evidence; do not cite.**

---

## 8. Files Created

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
| `g2_negative_control.csv` | 26 | permutation test results per country × sector |
| `g2_negative_control_sensitivity.csv` | 52 | sensitivity: k=3,10 |
| `g2_preflight_summary.json` | — | aggregated summary with criteria and verdict |

No raw edge files included. All artefacts are compact aggregated statistics.

---

## 9. Next Steps

1. **G2 main descriptive analysis:** Density and weight variation by period; sector-country
   patterns; within-country aggregate characterisation. Language: "observed aggregate variation"
   not "structural evolution".
2. **Dashboard adaptation plan:** Document which G2 statistics could be added to the France
   dashboard in future (no HTML modification — DEC-014).
3. Bloco 3 remains blocked pending Bloco 1 and Bloco 2 completion.
