# Atlas IAT — Annual Reconstruction Standby

**Date:** 2026-05-18  
**Purpose:** Single reference document for what is ready, what is blocked, and what to do next.

---

## 1. What Is Already Done

| Deliverable | File | Status |
|---|---|---|
| DB restored locally | `iat_restore` (PostgreSQL 14) | ✓ |
| Full table inventory | `data/interim/atlas_iat/table_inventory.csv` | ✓ |
| Source identification | `data/interim/atlas_iat/source_mapping_draft.csv` | ✓ |
| Basic ZE2020 features (v0) | `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v0.csv` | ✓ 306 rows |
| Full intelligence layer (v1) | `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v1.csv` | ✓ 306 rows × 26 cols |
| Feature hypotheses H1–H8 | `data/interim/atlas_iat/atlas_iat_feature_hypotheses.csv` | ✓ 16 hypotheses |
| Source reproducibility matrix | `data/interim/atlas_iat/source_reproducibility_matrix.csv` | ✓ 18 features × 23 cols |
| Download plan per source | `data/interim/atlas_iat/annual_source_download_plan.csv` | ✓ 9 sources |
| Reconstruction plan per year | `data/interim/atlas_iat/annual_feature_reconstruction_plan.csv` | ✓ 14 features × 2021–2027 |
| Source reproducibility audit | `reports/ATLAS_IAT_SOURCE_REPRODUCIBILITY_AUDIT.md` | ✓ |
| Database audit (with row counts) | `reports/ATLAS_IAT_DATABASE_AUDIT.md` | ✓ |
| Dynamic intelligence plan | `reports/ATLAS_IAT_DYNAMIC_INTELLIGENCE_PLAN.md` | ✓ |
| HERALD experiment plan | `reports/ATLAS_IAT_TO_HERALD_EXPERIMENT_PLAN.md` | ✓ Stage A–D defined |

---

## 2. Feature Classification (Final)

### Group 1 — annual_reconstructible (can update every year from open data)

| Feature | Source | Lag | Safe for training |
|---|---|---|---|
| `n_total_estab` | SIRENE base SIRET | T-1 (1 month) | YES |
| `n_active_estab` | SIRENE base SIRET | T-1 | YES |
| `active_share` | SIRENE base SIRET | T-1 | YES |
| `naf4_shannon_diversity` | SIRENE + NAF Rev2 | T-1 | YES |
| `naf4_hhi` | SIRENE + NAF Rev2 | T-1 | YES |

**What to download:** SIRENE stock Dec(Y-1) for each HERALD year Y  
**URL:** https://www.data.gouv.fr/fr/datasets/base-siret/  
**Effort:** Medium — bulk file processing, ZE2020 join via commune code

---

### Group 2 — static_structural_candidate (single vintage, safe for all years)

| Feature | Source | Update trigger | Safe for training |
|---|---|---|---|
| `avg_pci_naf_weighted` | Harvard OEC PCI 2019 | New Harvard Atlas release | YES — static structural |
| `nace_io_mean` | INSEE TES 2019 | New TES benchmark | YES — static structural |
| `nace_io_total` | INSEE TES 2019 | New TES benchmark | YES — static structural |
| `mean_naf_proximity` | vw_naf_proximity (static matrix) | New RCA data | static_context — matrix static; sector presence T-1 |
| `avg_maslow_naf_weighted` | Internal Maslow mapping | Never (proprietary) | static_context |

**What to download:** Nothing needed now — static values already in v1 CSV  
**PCI update:** Download from https://oec.world/en/resources/data when new vintage released (not urgent)  
**IO update:** Download INSEE TES 2020 when published (~2025) from https://www.insee.fr/fr/statistiques/2022724

---

### Group 3 — promising_needs_confirmation (usable but action required)

| Feature | Blocker | Action | Priority |
|---|---|---|---|
| `total_workforce` | 31% SIRENE coverage; CLAP better but requires separate download | Download CLAP emploi localisé par ZE2020 | MEDIUM |
| `avg_workforce_per_estab` | Same as above | Same — CLAP | MEDIUM |
| `avg_resilience_naf_weighted` | Formula undocumented (efficiency × redundancy → internal) | Investigate formula in restored DB; compare with util_efficiency_and_redundancy_per_flows_2019 | LOW (use static as-is for now) |

**Resilience static use:** `avg_resilience_naf_weighted` can be used as a **static context feature** without confirming the formula — it is a static [0,1] indicator per ZE2020 from v1. Only blocked from annual reconstruction.

---

### Group 4 — post_model_only (dashboard/recommendation, never training)

| Feature | Reason | Use case |
|---|---|---|
| `recommendation_density_postmodel` | 2022 static snapshot, partial coverage (39/306 ZEs), internal engine | After HERALD prediction: highlight ZEs with high predicted growth + high Atlas partnership activity |
| `avg_green_naf_weighted` (until confirmed) | Source unknown | After HERALD prediction: green transition dashboard layer |
| `avg_maslow_naf_weighted` | Context/narrative only | Post-forecast narrative: "this zone produces basic goods vs. professional services" |

---

### Group 5 — blocked_for_training (do not use until unblocked)

| Feature | Blocking issue | Path to unblock |
|---|---|---|
| `avg_green_naf_weighted` | Source of `rank_green_production.green_norm` unknown | Investigate EU Taxonomy → HS4 crosswalk; rebuild if confirmed |
| `mean_semantic_proximity` | NLP embedding model unknown | Re-embed `nomenclature_activity.name_ref2` with sentence-transformers; validate against existing scores |
| Any v1 feature as static value for ≤2021 backtests | IAT snapshot circa 2020–2022 | Reconstruct from SIRENE annual stocks (Group 1 features); static structural (Group 2) are exempt from this rule |

---

## 3. What Is Static vs. Dynamic

| Dimension | Static (same value all years) | Dynamic (varies year to year) |
|---|---|---|
| PCI | ✓ Harvard 2019 — structural | — |
| IO coefficients | ✓ INSEE TES 2019 — structural | — |
| NAF proximity matrix | ✓ vw_naf_proximity — structural | — |
| Maslow score | ✓ Internal mapping — structural | — |
| Resilience score | ✓ 2019 trade network — structural | — |
| Establishment counts | — | ✓ SIRENE Dec(Y-1) |
| NAF diversity / HHI | — | ✓ SIRENE Dec(Y-1) |
| Workforce | — | ✓ CLAP T-2 |
| Green score | — | blocked |
| Recommendation density | — | blocked (2022 snapshot only) |

**Rule:** Static structural features have the same value for 2012, 2015, 2021, and 2025. This is methodologically correct — they describe the long-run productive structure, not current conditions. They complement the SIDE dynamics, not replace them.

---

## 4. What Is Blocked and Why

| Feature | Block reason | Severity |
|---|---|---|
| `avg_green_naf_weighted` | Source of green_norm not documented in DB. Cannot confirm vintage. Risk of unknown leakage. | HIGH — do not use for training |
| `mean_semantic_proximity` | NLP embedding model identity unknown. Not reproducible. | MEDIUM — can approximate with open model |
| `recommendation_density_postmodel` | Partial engine coverage (39/306 ZEs). 2022 snapshot contaminates any backtest. | HIGH — post-model only |
| All v1 features as is for 2021 backtest | IAT snapshot circa 2020-2022. `n_active_estab` from 2022 to predict 2021 = forward leakage. | HIGH — reconstruct from SIRENE |

**Exception to block:** Static structural features (`avg_pci_naf_weighted`, `nace_io_mean`, `mean_naf_proximity`, `avg_resilience_naf_weighted`) are exempt from the snapshot rule because they describe long-run structure, not current conditions.

---

## 5. Which Sources to Download First

Priority order for annual reconstruction:

### Priority 1 — SIRENE base SIRET (unblocks 5 features)

**Download:** SIRENE stock Dec(Y) for Y = 2011–2024  
**URL:** https://www.data.gouv.fr/fr/datasets/base-siret/  
**Files needed:** 14 annual stock files (~1.5 GB each = ~21 GB total)  
**Unblocks:** `n_active_estab`, `active_share`, `naf4_shannon_diversity`, `naf4_hhi`, `n_distinct_naf4`  
**Script:** filter by `etat_administratif='A'` → join `code_commune_etablissement` to ZE2020 → aggregate

### Priority 2 — OEC Harvard PCI (completes static structural layer)

**Download:** PCI by HS4 for 2019 (or 2021) — single file  
**URL:** https://oec.world/en/resources/data  
**Files needed:** 1 CSV (~200 KB)  
**Unblocks:** Validates `avg_pci_naf_weighted` independently of IAT DB  
**Note:** The `pci_2019` column already in IAT is usable as-is. Download only to verify and update.

### Priority 3 — INSEE TES 2019 IO table (validates IO features)

**Download:** Symmetrical IO table at NACE A64 level  
**URL:** https://www.insee.fr/fr/statistiques/2022724  
**Files needed:** 1 Excel (~500 KB)  
**Unblocks:** Independent verification of `nace_io_mean` methodology  
**Script:** Extract NACE×NACE coefficients, threshold at 0.75, rebuild `nace_proximities`

### Priority 4 — CLAP emploi localisé (improves workforce features)

**Download:** Employment by ZE2020 and NAF sector — annual CSV  
**URL:** https://www.insee.fr/fr/statistiques/2021201  
**Files needed:** Varies by year (~1–5 MB each)  
**Unblocks:** `total_workforce` and `avg_workforce_per_estab` with full coverage

---

## 6. Features Most Likely to Help HERALD

Ordered by expected signal-to-noise, based on hypotheses H1–H8:

| Rank | Feature | Hypothesis | Why it might help |
|---|---|---|---|
| 1 | `naf4_shannon_diversity` (T-1) | H1 — Diversity | Diversified zones may show more stable creation dynamics; less sector-specific shock exposure |
| 2 | `naf4_hhi` (T-1) | H2 — Concentration | Concentrated zones may be more volatile; useful interaction with A10 sector features |
| 3 | `avg_pci_naf_weighted` (static) | H5 — Complexity | Complex zones may have different growth ceilings; differentiates high-knowledge vs. basic-goods ZEs |
| 4 | `mean_naf_proximity` (static + T-1 presence) | H3 — Proximity | Complementary sector mix may support sustained growth; captured by product-space logic |
| 5 | `nace_io_mean` (static) | H4 — IO linkage | Supply chain interconnection may buffer demand shocks |
| 6 | `avg_resilience_naf_weighted` (static) | H6 — Resilience | Post-2020 test: did high-resilience zones show less COVID degradation in 2021? |
| 7 | `active_share` (T-1) | H8 — Workforce structure | Declining active_share may signal structural weakening before observable in SIDE |

**Features likely to stay in dashboard only (not improve WMAPE):**
- `avg_maslow_naf_weighted` — structural narrative, low predictive variance
- `avg_green_naf_weighted` — mostly zero for services; discriminates industry ZEs only
- `recommendation_density_postmodel` — partial coverage, 2022 snapshot

---

## 7. Features That Should Stay in Dashboard/Recommendation Only

These features enrich the **interpretation** of HERALD predictions but should not enter training:

| Feature | Dashboard role |
|---|---|
| `recommendation_density_postmodel` | "Zone X has high predicted growth AND high Atlas recommendation activity → priority for targeted partnerships" |
| `avg_green_naf_weighted` | "Zone X is growing → which of its products have green transition potential?" |
| `avg_maslow_naf_weighted` | "Zone X produces [basic/luxury/professional] goods → frame policy narrative appropriately" |
| `avg_resilience_naf_weighted` | "Zone X's product basket is structurally [resilient/exposed] to supply chain shocks" |
| `nace_io_mean` | "Zone X's sectors are tightly linked → growth in one sector may cascade" |

**Rule:** A feature in the dashboard layer is used **after** HERALD predicts. It explains the prediction, it does not generate it.

---

## 8. Methodological Risks

| Risk | Description | Mitigation |
|---|---|---|
| **Snapshot leakage** | IAT is a 2020–2022 snapshot. Using it directly for 2021 backtests introduces forward information. | Reconstruct annual features from SIRENE; use only static structural features as-is |
| **All products fake** | 100% of `product` table rows have `fake=true` (imputed by process_product_faker). PCI/resilience/green are computed from NAF-product proximity, not confirmed product declarations. | Document clearly; scores are proxy indicators, not confirmed export baskets |
| **Misleading table name** | `rank_economic_growth` contains PCI (product complexity), not GDP growth rate. | Always reference as "PCI" in code and documents; never as "economic growth indicator" |
| **Partial recommendation coverage** | Recommendation engine ran for 39/306 ZEs (13%). Indicator is biased toward zones where engine was tested. | Post-model use only; never aggregate as ZE-level indicator for training |
| **Green source unknown** | `rank_green_production.green_norm` has no documented source. Cannot confirm if it introduces future-information leakage. | Blocked for training until confirmed |
| **IO low variance** | `nace_io_mean` ≈ 0.80 nationally with very low variance. Limited discriminating power as-is. | Use `nace_io_total` (unnormalized sum) or normalize by n_nace_pairs; test with ablation |
| **NAF coverage** | Only 295/1707 NAF codes (17.3%) have product proximity mapping. 39.9% of active establishments are excluded from PCI/resilience/green computation. | Document; treat scores as partial proxies for ZE productive complexity |

---

## 9. Next Recommended Actions

Ordered by impact and effort:

| Priority | Action | Effort | Unblocks |
|---|---|---|---|
| 1 | **Download SIRENE stock Dec 2011–2024** and compute annual SIRENE features (diversity, HHI, n_active) for all ZE2020 × year. | 2–3 days | Annual reconstruction for Stage C experiments |
| 2 | **Lock HERALD SIDE5 baseline** (Frente A): wmape_overall, wmape_2021, wmape_by_a10, seed_std. Required before any Atlas integration test. | Depends on HPC results | Stage A post-model overlay; Stage B static test |
| 3 | **Run Stage A** (post-model overlay): after HERALD baseline, apply Atlas v1 static features as interpretation layer. No training. Document 3–5 case studies. | 1 day | Validates Atlas coherence with HERALD signal |
| 4 | **Download OEC PCI** (single CSV) and verify `avg_pci_naf_weighted` independently of IAT DB. | 1 hour | Confirms static PCI feature independence |
| 5 | **Investigate green_norm source**: query `nomenclature_product_green` column definitions in restored DB; compare against EU Taxonomy HS4 annexes. | 2–4 hours | May unblock green for post-model use |
| 6 | **Run Stage B** (static structural training test): add avg_pci + nace_io_mean + mean_naf_proximity to HERALD after baseline locked. | Depends on HPC | First Atlas training evidence |
| 7 | **Download INSEE TES 2019** and independently rebuild `nace_proximities`. Validates IO methodology. | 4–8 hours | Independent IO verification |
| 8 | **Re-embed NAF descriptions** with sentence-transformers to reproduce `mean_semantic_proximity` approximately. | 2–4 hours | Unblocks semantic proximity for static context use |

---

## 10. What Must Never Happen

1. Using IAT `n_active_estab` from the 2022 snapshot to predict any year ≤ 2021 — **this is forward leakage**.
2. Using `recommendation_density_postmodel` as a training feature — **this is a 2022 static indicator**.
3. Calling `rank_economic_growth` a "growth indicator" — **it is PCI (product complexity)**.
4. Using `avg_green_naf_weighted` for training before confirming the source — **source unknown**.
5. Claiming Atlas/IAT "predicts" territorial dynamics — **HERALD predicts; Atlas interprets**.
6. Adding Atlas features without first locking the HERALD SIDE5 baseline — **no baseline = no valid comparison**.
