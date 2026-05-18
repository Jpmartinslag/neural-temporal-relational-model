# data/interim/atlas_iat/

Atlas/IAT intermediate data directory.  
All files here are derived from the Atlas/IAT dump: `/home/jpdark/Downloads/project_recomm/iat.dump`

**Dump date:** 2022-01-20  
**Audit date:** 2026-05-18  
**DB restored:** `iat_restore` (PostgreSQL 14, local)

---

## Files

| File | Status | Description |
|---|---|---|
| `table_inventory.csv` | COMPLETE | All tables, views, functions from dump TOC. Category, source, priority. |
| `source_mapping_draft.csv` | COMPLETE (draft) | Open source identification per data block. Confidence level: confirmed / inferred / unknown. |
| `ze2020_feature_plan.csv` | COMPLETE | 17 candidate features, use classification A/B/C, leakage risk, aggregation method, dynamic recipe. |
| `dynamic_feature_plan_by_year.csv` | COMPLETE | Feature × year matrix (2021–2027). Status, update recipe, lag per year. |
| `atlas_iat_feature_hypotheses.csv` | COMPLETE | 16 hypotheses H1–H8 with formula, source, leakage, acceptance criterion. |
| `atlas_iat_ze2020_static_features_v0.csv` | COMPLETE | Basic structural layer: counts, workforce, diversity, HHI. 306 rows. |
| `atlas_iat_ze2020_static_features_v1.csv` | COMPLETE | Full intelligence layer: v0 + PCI, resilience, green, Maslow, NAF proximity, IO linkage, recommendation density. 306 rows. |
| `atlas_iat_ze2020_dynamic_features_v0.csv` | NOT YET CREATED | Requires annual SIRENE/Douanes source data reconstruction (2012–2024). |

---

## Feature Layers — Status

### Layer 1 — Basic structural (v0) ✓ DONE
Columns: `n_total_estab`, `n_active_estab`, `active_share`, `total_workforce`, `avg_workforce_per_estab`, `n_distinct_naf4`, `naf4_shannon_diversity`, `naf4_hhi`

**Leakage note:** Snapshot circa 2020–2022. Not safe for backtest ≤2021 without SIRENE reconstruction.

### Layer 2 — Product intelligence (v1) ✓ DONE
Columns added: `avg_pci_naf_weighted`, `avg_resilience_naf_weighted`, `avg_green_naf_weighted`, `avg_maslow_naf_weighted`

**Method:** NAF activity → `nomenclature_activity_product_proximity` → HS4 product scores (PCI, resilience, green, Maslow). Weighted by NAF-product proximity score.  
**Coverage:** 60.1% of active establishments have NAF→product mapping (295 out of 1707 NAF codes mapped).  
**Leakage note:** PCI and resilience are static structural (safe for all years). Green source unconfirmed (post-model only).

### Layer 3 — Proximity intelligence (v1) ✓ DONE
Columns added: `mean_naf_proximity`, `mean_semantic_proximity`, `n_naf_pairs_in_ze`

**Method:** `vw_naf_proximity` (84,264 NAF pairs) × co-present NAF codes per ZE2020 → mean proximity score.

### Layer 4 — IO linkage (v1) ✓ DONE
Columns added: `nace_io_mean`, `nace_io_total`, `n_nace_pairs_in_ze`

**Method:** `nace_proximities` (2,816 IO-derived NACE pairs) × co-present NACE codes per ZE2020 → mean IO weight.  
**Note:** NACE code = `LEFT(naf_code, 5)`. IO mean ~0.80 across all zones (reflects filtered high-weight pairs only).

### Layer 5 — Recommendation density (v1, post-model) ✓ DONE
Columns added: `n_recommendations_postmodel`, `n_estab_with_recom_postmodel`, `recommendation_density_postmodel`

**Coverage:** Only 39/306 ZE2020 have any recommendations computed — engine was run for a subset only.  
**Use:** Post-model layer only. Never use for training.

### Layer 6 — Dynamic annual (NOT YET)
Requires: annual SIRENE stock files (2011–2024) + annual Douanes data (2012–2023).  
Features: `naf4_shannon_diversity_t1`, `naf4_hhi_t1`, `n_active_estab_t1`, `export_rca_t2`

---

## Key Data Quality Notes

| Finding | Impact |
|---|---|
| All `product` rows have `fake=true` — synthetically imputed by process_product_faker() | PCI/resilience/green computed via NAF→product proximity, not confirmed product declarations |
| Only 39/306 ZE2020 have recommendation data — engine ran partially | recommendation_density is a partial indicator, not national coverage |
| `rank_economic_growth` column `pci_2019` is Harvard PCI, NOT GDP growth rate | Feature name misleading — document as PCI everywhere |
| `avg_green_naf_weighted` mean = 0.004 nationally — very low for service-dominated zones | Green scores mainly discriminate industrial ZEs; weak feature for services |
| IO mean ~0.80 across all zones — low variance | IO linkage may have low discriminating power; verify with sectoral subsetting |
| util_histo_establishment covers 2006–2018 at department level only | Dynamic reconstruction before 2019 requires department→ZE2020 proxy |

---

## ZE2020 Join Path

```
establishment.address_id
  → address.city_id
    → city.insee_code  [5-digit, 100% populated]
      → commune_to_ze2020_2026.csv (CODGEO)
        → ZE2020
```

Arrondissement fix applied:
- Paris `751XX` → `75056`
- Lyon `6938X` → `69123`
- Marseille `1320X` → `13055`

Coverage after fix: **98.1%** of establishments mappable to ZE2020.  
Unmapped 1.9% = overseas territories (971XX–976XX), correctly outside HERALD metropolitan panel.

---

## Isolation Guarantee

All files here are:
- New additions only — no HERALD training files modified
- Isolated from HPC outputs
- Not pushed to remote (manual push by user)
