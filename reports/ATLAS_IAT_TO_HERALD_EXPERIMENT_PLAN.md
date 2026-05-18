# Atlas IAT → HERALD Integration — Experiment Plan

**Date:** 2026-05-18  
**Status:** Phase 2 — Updated with verified coverage and concrete feature formulas  
**No training runs here.** This document plans; HERALD Frente A trains.

---

## 0. Methodological Framing

### What Atlas/IAT is and is not

Atlas/IAT is a **static economic intelligence system** built around:
- 1.55M French establishments (SIRENE circa 2020–2022)
- NAF/NACE activity codes → IO linkages → product space proximity
- Harvard Atlas methodology: RCA, PCI, product space density
- Maslow-based product necessity rankings
- Network efficiency/redundancy as productive resilience

It was **not built in ZE2020**. It operates at establishment / commune / department / region level. The ZE2020 aggregation is a methodological adaptation for HERALD compatibility.

**Correct language:**
- "Atlas/IAT-derived features re-aggregated by ZE2020"
- "HERALD uses a territorial layer derived from Atlas/IAT"
- **Not:** "Atlas/IAT uses ZE2020" or "Atlas/IAT predicts ZE2020 creation"

### What HERALD is and is not

HERALD is a **temporal territorial forecast model**. It predicts establishment creation (SIDE target) per ZE2020 × A10 × year. Currently: 5 features derived from SIDE only. Goal is minimal noise, maximum robustness.

Atlas/IAT enriches the **interpretation** of HERALD output and **may** add signal to HERALD training — but only if evidence supports it and leakage is controlled.

---

## 1. Controlled Growth Strategy

HERALD is in a noise-reduction phase. Any feature addition must follow this protocol:

```
Step 1: Document hypothesis
Step 2: Verify source vintage and leakage risk
Step 3: Post-model test (does it correlate with HERALD errors?)
Step 4: Small controlled training experiment
Step 5: Accept / reject based on criteria
Step 6: Dynamic reconstruction for full temporal panel
```

No "dump all features and see what happens." Each block is evaluated independently. Ablation is mandatory before any combination.

---

## 2. ZE2020 Coverage (confirmed)

From the verified database:
- **306 / 306 ZE2020 have Atlas/IAT establishment data (100% coverage)**
- 98.1% of IAT establishments are mappable to ZE2020
- Unmapped 1.9% = overseas territories (971XX–976XX) correctly excluded from HERALD panel
- Arrondissement fix applied: Paris (751XX→75056), Lyon (6938X→69123), Marseille (1320X→13055)

---

## 3. Feature Classification Summary

| Feature | Source | Train? | Dynamic? | Leakage |
|---|---|---|---|---|
| `naf4_shannon_diversity` | SIRENE stock | A — safe | Yes (T-1) | MEDIUM |
| `naf4_hhi` | SIRENE stock | A — safe | Yes (T-1) | MEDIUM |
| `avg_pci` | Harvard Atlas | A — safe | No (static) | LOW |
| `nace_io_strength` | INSEE TES | A — safe | No (static) | LOW |
| `mean_naf_proximity` | vw_naf_proximity | B — context | No (static matrix) | LOW |
| `avg_resilience` | rank_productive_resilience | B — context | No (static) | LOW |
| `export_rca_strength` | Douanes France | A — safe | Yes (T-2) | MEDIUM |
| `avg_green_score` | rank_green_production | C — post-model | Source unconfirmed | MEDIUM |
| `maslow_coverage` | rank_basic_necessities | C — post-model | No (static) | LOW |
| `recommendation_density` | recommendation table | C — post-model | No (2022 snapshot) | HIGH |
| `supplier_potential_score` | ia_potential_by_iot | C — post-model | No (2022 snapshot) | HIGH |
| `workforce_density` | SIRENE workforce_count | A — safe | Yes (T-2) | MEDIUM |
| `pci_std_within_ze` | Harvard Atlas | B — context | No (static) | LOW |

---

## 4. Experiment Sequence

### Exp 0 — HERALD SIDE5 baseline (Frente A — running)

Lock in before Exp 1:
- `wmape_overall`, `wmape_2021`, `wmape_2025`
- `wmape_by_a10` for all 10 sectors
- `seed_std` over ≥5 seeds
- Large ZE vs. small ZE WMAPE split

---

### Exp 1 — Static structural (PCI + IO, no temporal risk)

**Features:** `avg_pci`, `nace_io_strength`  
**Why these first:** Both are static structural indicators with no leakage risk for any HERALD year. If they add nothing, stop here.

**Configuration:**
```python
features = ['side_lag_1', 'side_lag_2', 'side_lag_3', 'growth_1y', 'growth_2y',
            'avg_pci',           # Harvard PCI per ZE2020 (static)
            'nace_io_strength']  # IO coefficient sum (static)
```

**Pass criterion:**
- WMAPE does not increase by > 0.3pp
- Seed std does not increase
- 2021 WMAPE does not worsen

**If pass:** proceed to Exp 2.  
**If fail:** document and skip to Exp 3 (separate test).

---

### Exp 2 — Diversity + concentration (T-1 SIRENE)

**Features:** `naf4_shannon_diversity`, `naf4_hhi`  
**Prerequisite:** Annual SIRENE stock files loaded for 2011–2024 (covers T-1 for 2012–2025 HERALD range)

**Leakage control:** For each HERALD year Y, use SIRENE stock as of December Y-1.

**Configuration:**
```python
features = baseline + ['naf4_shannon_diversity_t1', 'naf4_hhi_t1']
```

**Pass criterion:**
- Same as Exp 1
- If diversity and HHI are highly correlated with each other (r > 0.95), keep only one

---

### Exp 3 — NAF proximity (static matrix, dynamic sector presence)

**Feature:** `mean_naf_proximity_within_ze`  
**Computation:**
```sql
-- For year Y: use SIRENE stock T-1 to identify co-present NAF codes in ZE2020
-- Then compute mean proximity from static vw_naf_proximity matrix
SELECT ze2020,
  AVG(p.proximity) AS mean_naf_proximity,
  AVG(p.semantic_proximity) AS mean_semantic_proximity
FROM ze2020_naf_presence_t1 n1
JOIN ze2020_naf_presence_t1 n2 ON n1.ze2020 = n2.ze2020 AND n1.naf_id < n2.naf_id
JOIN vw_naf_proximity p ON p.naf_id = n1.naf_id AND p.naf_id_dest = n2.naf_id
GROUP BY ze2020;
```

**Pass criterion:** Same as Exp 1 + 2.

---

### Exp 4 — Product complexity + resilience

**Features:** `avg_pci` (already in Exp 1), `avg_resilience_score`

**Note:** `avg_resilience_score` is computed from `rank_productive_resilience` (network efficiency × redundancy per HS4). Methodology confirmed from schema: `resilience = efficiency × redundancy`, `resilience_norm ∈ [0,1]`.

**Pass criterion:** Improvement in 2021 WMAPE (COVID shock year, where resilient product zones may have shown different dynamics).

---

### Exp 5 — Export RCA (T-2 Douanes)

**Feature:** `export_rca_strength` = count of HS4 products with RCA > 1 at ZE2020 level, aggregated from department-level Douanes data.

**Temporal availability:**
- For HERALD year 2021: use Douanes 2019 (T-2)
- For HERALD year 2022: use Douanes 2020 (T-2)
- For HERALD year 2025: use Douanes 2023 (T-2)

**Pass criterion:** WMAPE improvement in ZEs with strong export sectors (A10-C manufacturing, A10-D energy).

---

### Exp 6 — Minimum robust combination

After Exp 1–5 evaluated, identify the minimum combination that:
1. Does not worsen WMAPE by > 0.2pp vs. Exp 0
2. Improves at least one metric meaningfully
3. Passes all leakage checks
4. Is annualisable from open sources with documented recipes

Expected candidate: `avg_pci` + `naf4_shannon_diversity_t1` + `nace_io_strength`

---

### Exp 7 — Post-model overlay (no training impact)

After any of Exp 1–6 completes, build post-model overlay:

**Input:** HERALD forecast for year Y per ZE2020 × A10  
**Enrichment from Atlas/IAT:**
```
Zone accelerating (predicted +10%+):
  → Top 3 NAF sectors by partnership potential
  → Maslow coverage: basic needs vs. luxury products
  → Green score: transition readiness
  → Supplier potential: which neighboring ZEs could supply inputs

Zone decelerating (predicted -5%):
  → HHI (is this a concentrated zone at risk?)
  → IO linkage: which sectors are most exposed?
  → PCI: is the product base sophisticated enough to pivot?
  → Closest ZE2020 with growing complementary sectors
```

This layer does not modify the WMAPE. It adds economic interpretability.

---

### Exp 8 — Ablations

For any feature that enters Exp 6 minimum combination:
- Remove one block at a time
- Measure WMAPE delta
- If removing a feature does not increase WMAPE by > 0.1pp, it is redundant → remove

---

## 5. Metrics

| Metric | Description |
|---|---|
| `wmape_overall` | Weighted MAE / weighted total, all ZE2020 × A10 × year |
| `wmape_2021` | Same, restricted to 2021 (COVID instability probe) |
| `wmape_2025` | Same, restricted to 2025 (latest year, out-of-sample) |
| `wmape_by_a10` | Per A10 sector — identify which sectors benefit or regress |
| `seed_std` | Std of wmape_overall over ≥5 seeds |
| `wmape_large_ze` | ZE2020 with n_active_estab > 3748 (above median) |
| `wmape_small_ze` | ZE2020 with n_active_estab ≤ 3748 (at/below median) |
| `n_features` | Total feature count (parsimony monitor) |

---

## 6. Pass / Fail Criteria

| Condition | Action |
|---|---|
| WMAPE increases by > 0.3pp | Reject block |
| Seed std increases by > 0.5pp | Flag instability, investigate before accepting |
| 2021 WMAPE worsens by > 0.5pp | Audit vintage — likely leakage |
| Feature corr > 0.9 with side_lag_1 | Flag as potentially redundant, test ablation |
| WMAPE improves ≥ 0.3pp, stable seeds | Accept block |
| No WMAPE improvement but clear interpretation gain | Accept as post-model layer (Cat C) only |
| Feature fails leakage check | Reject for training, keep as post-model only |

---

## 7. Prohibited Methods

- **No causal claims:** Atlas/IAT does not prove causality. HERALD predicts, Atlas explains.
- **No manual flags:** No COVID dummy, no rebound dummy, no crisis indicator.
- **No static snapshot for ≤2021 backtests** without confirmed temporal reconstruction.
- **No calling nowcast a forecast:** In-sample fit is not a forecast.
- **No language implying Atlas/IAT "is" ZE2020:** It is re-aggregated for HERALD compatibility.
- **No combining features without ablation:** Always test blocks independently first.

---

## 8. Product Vision

The final integrated product:

```
HERALD FORECAST 2026 — ZE7625 Toulouse, A10-J (Information/Communication)
Predicted growth: +14% establishment creation
Confidence: HIGH (seed std < 0.8pp)

ATLAS/IAT INTELLIGENCE LAYER:
  Productive structure (static):
    NAF diversity: 4.06 (high — 3rd quartile nationally)
    HHI: 0.048 (low concentration)
    Mean NAF proximity: 0.62 (above national mean 0.37)
    Avg PCI: 1.23 (complex productive base)
    Resilience score: 0.71 (high)

  Dynamic context (T-2 lag):
    Export RCA in A10-J products: 1.4 (above 1 → competitive)
    SIRENE growth rate 2024: +3.2% establishments in ICT
    
  Recommendation (post-model):
    Top supplier opportunity: ZE8421 Lyon (proximity 0.85, 42km)
    Green potential: moderate (3 green products in current basket)
    Maslow coverage: esteem/self-actualization tier (non-basic)
    
  Interpretation:
    Toulouse is a high-complexity, diversified, non-concentrated zone.
    Predicted A10-J growth aligns with its strong NAF proximity to tech sectors.
    Recommendation: attract logistics/support services (A10-H) to sustain ICT cluster.
```

This transforms a WMAPE number into an actionable economic recommendation, without claiming causality.
