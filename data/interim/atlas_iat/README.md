# data/interim/atlas_iat/

Atlas/IAT intermediate data directory.  
All files here are derived from an external Atlas/IAT database dump (`iat.dump`, not
part of this repository — kept locally by whoever runs the restore).

**Dump date:** 2022-01-20  
**Audit date:** 2026-05-18  
**DB restored:** `iat_restore` (PostgreSQL 14, local)

---

## Files

### Current Phase — Static layer (closed, ready for post-model use)

| File | Status | Description |
|---|---|---|
| `atlas_iat_ze2020_static_features_v0.csv` | COMPLETE | **Basic layer:** counts, workforce, diversity, HHI. 306 rows × 12 cols. |
| `atlas_iat_ze2020_static_features_v1.csv` | **COMPLETE — ACTIVE** | **Full static intelligence layer:** v0 + PCI, resilience, green, Maslow, NAF proximity, IO linkage, recommendation density. 306 rows × 26 cols. Zero nulls. Audited. |
| `static_feature_use_policy.csv` | COMPLETE | Use policy per column: safe_static_context / post_model_only / blocked / needs_validation. |

### Reference and planning

| File | Status | Description |
|---|---|---|
| `table_inventory.csv` | COMPLETE | All 90+ tables, views, functions from dump TOC. |
| `source_mapping_draft.csv` | COMPLETE | Open source identification per data block. |
| `source_reproducibility_matrix.csv` | COMPLETE | 18 features × 23 cols: source, API, lag, year-by-year status. |
| `atlas_iat_feature_hypotheses.csv` | COMPLETE | 16 hypotheses H1–H8 with formula, source, leakage, acceptance criterion. |
| `ze2020_feature_plan.csv` | COMPLETE | 17 candidate features, use classification, leakage risk. |

### Future phase — Annual dynamic reconstruction (NOT STARTED)

| File | Status | Description |
|---|---|---|
| `annual_source_download_plan.csv` | PLANNED | 9 sources with URLs, lag, format — ready when dynamic phase starts. |
| `annual_feature_reconstruction_plan.csv` | PLANNED | Feature × 2021–2027 reconstruction recipes — ready when dynamic phase starts. |
| `dynamic_feature_plan_by_year.csv` | PLANNED | Full year × feature availability matrix. |
| `atlas_iat_ze2020_dynamic_features_v0.csv` | **NOT STARTED** | Requires SIRENE Dec 2011–2024 + Douanes annual data. **Do not create until Stage A (post-model overlay) is validated.** |

---

## Phase Status

```
Phase 1 (DONE): DB restored, TOC audited, ZE2020 coverage confirmed (98.1%, 306/306 zones)
Phase 2 (DONE): static_features_v0 + v1 generated, audited, use policy defined
Phase 3 (CURRENT): Post-model/dashboard overlay — use v1 as interpretation layer for the model's output
Phase 4 (FUTURE): Annual dynamic reconstruction — SIRENE Dec 2011-2024, Douanes, CLAP
Phase 5 (FUTURE): Controlled training experiments with Atlas features
```

**Current priority:** Close static layer. Use v1 as Stage A post-model overlay. Do not start Phase 4 until Stage A validation is complete.

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
Unmapped 1.9% = overseas territories (971XX–976XX), correctly outside the metropolitan panel.

---

## Source Reproducibility Summary

The full prose audit was consolidated into the repository's documentation history
before this delivery branch existed and is not part of the current file tree; it
remains recoverable from git history
(`git log --all -- reports/ATLAS_IAT_SOURCE_REPRODUCIBILITY_AUDIT.md`). The table
below and the machine-readable matrix are the operative summary.  
See machine-readable matrix: `source_reproducibility_matrix.csv`

| Feature block | Source status | Reconstructible annually | Training safe |
|---|---|---|---|
| Establishment counts (n_total, n_active, active_share) | confirmed — INSEE SIRENE | YES (T-1 lag) | YES |
| Workforce (total, avg per estab) | confirmed — SIRENE / CLAP | PARTIAL (31% coverage in IAT; full coverage via CLAP T-2) | YES |
| NAF diversity + HHI | confirmed — SIRENE + NAF Rev2 | YES (T-1 lag) | YES |
| PCI (`avg_pci_naf_weighted`) | inferred — Harvard Atlas OEC | YES (static, update on new release) | YES |
| Resilience (`avg_resilience`) | proprietary — formula undocumented | NO — static use only | static context |
| Green score (`avg_green`) | **unknown** | NO — source unconfirmed | post-model only |
| Maslow coverage | proprietary — internal mapping | NO — static use only | static context |
| NAF proximity (product-space) | inferred — Harvard product space adapted | PARTIAL — can recompute with new data | static context |
| Semantic proximity | inferred — NLP embeddings (model unknown) | PARTIAL — can re-embed with open model | static context |
| IO linkage (NACE) | inferred — INSEE TES / Eurostat SUTS | YES (new TES vintage) | YES |
| Recommendation density | proprietary — engine ran partially | NO — post-model only | post-model only |

---

## Isolation Guarantee

All files here are:
- New additions only — no training files modified
- Isolated from HPC outputs
- Not pushed to remote (manual push by user)
