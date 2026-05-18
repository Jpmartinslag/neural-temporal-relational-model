# Atlas IAT — Static Layer Audit (v1)

**Date:** 2026-05-18  
**File audited:** `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v1.csv`  
**Rows:** 306 (all ZE2020)  
**Columns:** 26  
**Nulls:** 0 (full coverage for all columns across all 306 zones)  
**Source DB:** `iat_restore` (PostgreSQL 14, restored from 819 MB dump dated 2022-01-20)

---

## 0. Scope

This audit closes the static Atlas/IAT layer as a **methodological and interpretive product**. The v1 CSV is the basis for the post-model/dashboard layer (Stage A). No training experiments follow until HERALD SIDE5 baseline is locked.

**What is audited:** ranges, nulls, outliers, discriminating power, use classification.  
**What is not here:** dynamic annual reconstruction, HERALD training tests, new data downloads.

---

## 1. Column Summary by Layer

### Layer 1 — Basic structural (from SIRENE snapshot)

| Column | Min | Max | Mean | Variance | Use policy | Training status |
|---|---|---|---|---|---|---|
| `n_total_estab` | 342 | 124,757 | 4,969 | HIGH | static_context | not_safe — snapshot |
| `n_active_estab` | 329 | 86,612 | 3,748 | HIGH | static_context | not_safe — snapshot |
| `n_inactive_estab` | 13 | 38,145 | 1,220 | HIGH | static_context | not_safe — snapshot |
| `active_share` | 0.646 | 0.962 | 0.762 | MEDIUM | safe_static_context | structural ratio |
| `total_workforce` | 313 | 478,788 | 16,446 | HIGH | static_context | not_safe — 31% coverage |
| `avg_workforce_per_estab` | 0.32 | 12.45 | 3.31 | MEDIUM | safe_static_context | structural proxy |
| `n_distinct_naf4` | 55 | 356 | 166 | HIGH | safe_static_context | structural |
| `naf4_shannon_diversity` | 1.12 | 4.44 | 3.60 | HIGH | **safe_static_context_candidate** | safe — structural |
| `naf4_hhi` | 0.023 | 0.666 | 0.089 | HIGH | **safe_static_context_candidate** | safe — structural |

### Layer 2 — Product scores (NAF-proximity weighted)

| Column | Min | Max | Mean | Variance | Use policy | Training status |
|---|---|---|---|---|---|---|
| `avg_pci_naf_weighted` | −1.25 | 0.10 | −0.56 | HIGH | **safe_static_context_candidate** | safe — structural |
| `avg_resilience_naf_weighted` | 0.12 | 0.85 | 0.51 | HIGH | safe_static_context | safe — formula partially undocumented |
| `avg_green_naf_weighted` | 0.000 | 0.028 | 0.004 | VERY LOW | **post_model_only** | blocked — source unknown + near-zero variance |
| `avg_maslow_naf_weighted` | 0.004 | 0.371 | 0.044 | MEDIUM | safe_static_context | safe — narrative layer |

### Layer 3 — NAF proximity

| Column | Min | Max | Mean | Variance | Use policy | Training status |
|---|---|---|---|---|---|---|
| `mean_naf_proximity` | 0.341 | 0.465 | 0.409 | LOW | safe_static_context | low discriminating power |
| `mean_semantic_proximity` | 0.617 | 0.806 | 0.740 | MEDIUM | needs_source_validation | blocked — NLP model unknown |
| `n_naf_pairs_in_ze` | 463 | 32,342 | 7,055 | HIGH | size_proxy | not_independent |

### Layer 4 — IO linkage

| Column | Min | Max | Mean | Variance | Use policy | Training status |
|---|---|---|---|---|---|---|
| `nace_io_mean` | 0.793 | 0.815 | 0.800 | **VERY LOW** | needs_source_validation | low discriminating power |
| `nace_io_total` | 58 | 1,903 | — | HIGH | safe_static_context | safe — but driven by zone size |
| `n_nace_pairs_in_ze` | 72 | 2,378 | 532 | HIGH | size_proxy | not_independent |

### Layer 5 — Recommendation (post-model only)

| Column | Min | Max | Mean | Coverage | Use policy | Training status |
|---|---|---|---|---|---|---|
| `n_recommendations_postmodel` | 0 | 5,658 | — | 39/306 ZEs | **post_model_only** | blocked |
| `n_estab_with_recom_postmodel` | 0 | 3,509 | — | 39/306 ZEs | **post_model_only** | blocked |
| `recommendation_density_postmodel` | 0.00 | 1.076 | 0.071 | 39/306 ZEs | **post_model_only** | blocked |

---

## 2. Use Policy Classification

### safe_static_context_candidate
Features with good discriminating power, documented source, and no leakage risk as structural indicators:

- `naf4_shannon_diversity` — best basic discriminator; range [1.12, 4.44]
- `naf4_hhi` — concentration metric; Épernay (0.67) clearly outlier
- `avg_pci_naf_weighted` — product complexity; all French zones negative (below global median)
- `avg_pci_naf_weighted` should be renamed `avg_pci_2019_naf_weighted` in any downstream use

### safe_static_context (usable with documented caveats)
- `active_share` — structural ratio, interpretable
- `avg_workforce_per_estab` — structural proxy (31% SIRENE coverage caveat)
- `n_distinct_naf4` — strongly correlated with zone size; normalize before use
- `avg_resilience_naf_weighted` — structural; formula partially undocumented but [0,1] normalized
- `avg_maslow_naf_weighted` — narrative layer; non-linear distribution
- `nace_io_total` / `nace_io_total / n_nace_pairs` — IO intensity proxy; zone-size adjusted version preferred

### post_model_only
- `avg_green_naf_weighted` — near-zero variance (max 0.028 nationally); source unknown
- `recommendation_density_postmodel` — 2022 snapshot; 87% zeros; use as binary flag
- `n_recommendations_postmodel`, `n_estab_with_recom_postmodel` — same

### needs_source_validation
- `mean_semantic_proximity` — NLP model unknown; blocked until re-embedded with open model
- `nace_io_mean` — too narrow variance [0.79, 0.81]; methodology needs validation with INSEE TES

### not_safe_for_training (snapshot caveats)
- `n_total_estab`, `n_active_estab`, `n_inactive_estab`, `total_workforce` — from 2020–2022 SIRENE snapshot. Cannot be used for ≤2021 backtests without annual reconstruction.

---

## 3. Discriminating Power Summary

Ranked by useful variance for ZE2020 interpretation:

| Rank | Column | Range | Notes |
|---|---|---|---|
| 1 | `naf4_shannon_diversity` | [1.12, 4.44] | 4× range; clear story (Épernay vs Lyon) |
| 2 | `naf4_hhi` | [0.023, 0.67] | 29× range; identifies single-sector zones |
| 3 | `avg_pci_naf_weighted` | [−1.25, 0.10] | 1.37 unit range; z-score units |
| 4 | `avg_resilience_naf_weighted` | [0.12, 0.85] | 0.73 range; 7× spread |
| 5 | `avg_workforce_per_estab` | [0.32, 12.45] | 39× spread; strong size signal |
| 6 | `avg_maslow_naf_weighted` | [0.004, 0.37] | 92× spread but non-linear |
| 7 | `mean_semantic_proximity` | [0.62, 0.81] | 0.19 range; blocked |
| 8 | `nace_io_total` | [58, 1903] | 33× spread; zone-size driven |
| 9 | `mean_naf_proximity` | [0.34, 0.46] | 0.12 range; low discriminating power |
| 10 | `avg_green_naf_weighted` | [0.00, 0.028] | near-zero; not useful as continuous |
| 11 | `nace_io_mean` | [0.79, 0.81] | 0.02 range; essentially constant |

---

## 4. Notable Outliers

### Épernay (ZE4406)
| Metric | Value | National rank |
|---|---|---|
| `naf4_hhi` | 0.666 | 1st (highest concentration in metropolitan France) |
| `naf4_shannon_diversity` | 1.12 | Last (lowest diversity) |
| `avg_pci_naf_weighted` | −1.09 | Near bottom (champagne = agricultural product) |
| `avg_resilience_naf_weighted` | 0.85 | 1st (champagne = globally traded, many buyers) |
| `avg_workforce_per_estab` | 1.03 | Very low |
| `n_active_estab` | 9,449 | Medium size |

**Story:** Épernay is a textbook concentrated single-sector zone. Champagne has low product complexity but extremely resilient global trade networks. High predicted creation growth in Épernay may signal champagne expansion (seasonal, export-driven), not structural diversification.

### Paris (ZE1109)
| Metric | Value | National rank |
|---|---|---|
| `avg_pci_naf_weighted` | 0.10 | 1st (highest PCI nationally) |
| `n_active_estab` | 86,612 | 1st |
| `naf4_shannon_diversity` | 3.93 | High (not highest — Lyon wins at 4.44) |
| `naf4_hhi` | 0.036 | Very low (not most diverse) |

**Story:** Paris has the most complex productive base (highest PCI) but is not the most diverse in NAF terms (Lyon has more evenly distributed sectors). Paris is dominated by high-knowledge services (financial, professional, tech).

### Overseas territories (01XX–06XX)
- Generally lower PCI (−1.25 to −0.60): agriculture, fishing, basic services
- Lower active_share (~0.70 vs 0.76 national mean)
- Lower workforce per estab (0.32–1.22): smaller, less formal establishments
- Métropole panel should exclude 0101–0601 for HERALD metropolitan analysis

---

## 5. Key Data Quality Issues (Confirmed)

| Issue | Impact | Mitigation |
|---|---|---|
| All `product` rows fake=true | PCI/resilience/green/Maslow are NAF-proximity proxies, not confirmed product declarations | Document as "NAF-weighted structural proxy" not "declared products" |
| `rank_economic_growth` = PCI, not growth | Name misleading — risk of misinterpretation | Always rename to `avg_pci_naf_weighted` or `avg_pci_2019` in downstream code |
| `nace_io_mean` variance = 0.02 | Essentially constant; cannot discriminate ZEs | Use `nace_io_total` with normalization; or drop IO mean entirely |
| `avg_green_naf_weighted` max = 0.028 | Near-zero for 99% of zones; useless as continuous feature | Binary flag: `is_industrial_green_zone = green > 0.01` at most |
| Recommendation engine partial (39/306 ZEs) | `recommendation_density` not comparable across zones | Use as binary flag: `has_atlas_recommendation = (density > 0)` |
| Snapshot vintage 2020–2022 | Not safe for dynamic use | Static structural only; annual reconstruction separate phase |

---

## 6. Recommended Feature Set for Stage A (Post-Model Dashboard)

Features to display alongside HERALD forecast — no training, interpretation only:

```python
stage_A_dashboard_features = {
    # Structural identity
    'naf4_shannon_diversity':      'Productive diversity (NAF4 Shannon entropy)',
    'naf4_hhi':                    'Sectoral concentration (HHI)',
    'avg_pci_naf_weighted':        'Productive complexity (PCI 2019, Harvard Atlas)',
    
    # Resilience and workforce
    'avg_resilience_naf_weighted': 'Productive resilience (network structure 2019)',
    'avg_workforce_per_estab':     'Avg workforce per establishment',
    
    # Narrative context
    'avg_maslow_naf_weighted':     'Product basket tier (Maslow hierarchy)',
    
    # Partnership signal (binary)
    'has_atlas_recommendation':    'Atlas recommendation activity (binary)',
}
```

**Not in Stage A dashboard:**
- `avg_green_naf_weighted` — blocked (source unknown, near-zero)
- `mean_semantic_proximity` — blocked (NLP model unknown)
- `nace_io_mean` — near-zero variance, not interpretable
- `n_active_estab`, `n_total_estab` — snapshot; use HERALD's own SIDE data for counts

---

## 7. Stage A Usage Plan

**Trigger:** HERALD SIDE5 baseline locked (wmape_overall, wmape_2021, seed_std confirmed stable)

**Workflow:**
```
1. Load HERALD forecast: ze2020 × A10 × year → predicted_creation, predicted_growth
2. Load Atlas v1: ze2020 → 7 dashboard features
3. Join on ze2020
4. For each ZE2020 in HERALD output:
   a. Classify: accelerating / decelerating / uncertain
   b. Lookup Atlas structural profile
   c. Generate interpretation text
5. Output: ZE2020 forecast + Atlas context layer
```

**Example output format:**
```
ZE4406 Épernay — A10-A (Agriculture) — Predicted: +8% creation
Atlas context:
  Diversity: LOW (1.12 / national mean 3.60) — single-sector zone
  Concentration: EXTREME (HHI 0.67 / national mean 0.09)
  Complexity: VERY LOW (PCI −1.09 / national mean −0.56) — champagne = agricultural product
  Resilience: VERY HIGH (0.85 / national mean 0.51) — global demand diversification
  Note: Growth in A10-A here likely reflects champagne harvest cycle, not structural expansion
```

**Validation criteria for Stage A:**
- Do accelerating ZEs (HERALD) tend to have higher diversity and PCI than decelerating ZEs?
- Do 2021 HERALD errors correlate with Atlas resilience scores? (Low-resilience zones more volatile in COVID year)
- Are there ZEs where HERALD and Atlas tell different stories? (Low growth predicted + high complexity = underutilized potential?)

---

## 8. What Is NOT in This Audit

| Out of scope | When |
|---|---|
| Annual dynamic reconstruction (SIRENE Dec 2011–2024) | Future phase |
| HERALD training experiments with Atlas features | After Stage A validates coherence |
| Download of OEC PCI or INSEE TES for independent validation | After Stage A |
| Green source investigation | After Stage A |
| Semantic proximity re-embedding | After Stage A |
