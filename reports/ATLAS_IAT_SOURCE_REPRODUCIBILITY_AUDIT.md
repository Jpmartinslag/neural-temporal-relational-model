# Atlas IAT — Source Reproducibility Audit

**Date:** 2026-05-18  
**Status:** Complete  
**Purpose:** Close the traceability of every feature in `atlas_iat_ze2020_static_features_v1.csv` — what it comes from, whether it can be updated annually, and whether it is safe for HERALD training.

---

## Summary

| Category | Features | Count |
|---|---|---|
| `source_confirmed` | n_total_estab, n_active_estab, n_inactive_estab, active_share, total_workforce, avg_workforce_per_estab, n_distinct_naf4, naf4_shannon_diversity, naf4_hhi | 9 |
| `source_inferred` | avg_pci_naf_weighted, mean_naf_proximity, mean_semantic_proximity, nace_io_mean, nace_io_total | 5 |
| `proprietary_or_internal` | avg_resilience_naf_weighted, avg_maslow_naf_weighted, recommendation_density_postmodel | 3 |
| `source_unknown` | avg_green_naf_weighted | 1 |

| Training status | Features |
|---|---|
| `safe_for_training` (confirmed reproducible, ex-ante possible) | n_total_estab, n_active_estab, active_share, total_workforce, avg_workforce_per_estab, naf4_shannon_diversity, naf4_hhi, avg_pci_naf_weighted, nace_io_mean, nace_io_total |
| `static_context` (structural, safe but not dynamic) | n_distinct_naf4, avg_maslow_naf_weighted, avg_resilience_naf_weighted, mean_naf_proximity, mean_semantic_proximity |
| `post_model_only` | avg_green_naf_weighted, recommendation_density_postmodel |

---

## 1. Establishment Stock Features (SIRENE-based)

### Features: `n_total_estab`, `n_active_estab`, `n_inactive_estab`, `active_share`

**Atlas source:** `establishment` table, joined via `address → city → insee_code → ZE2020`  
**External source:** `source_confirmed` — INSEE SIRENE, Base SIRET  
**URL:** https://www.data.gouv.fr/fr/datasets/base-siret/  
**API:** INSEE SIRENE API v3 — https://api.insee.fr/  

**Annual update recipe:**
```python
# 1. Download SIRENE stock (full file ~1.5 GB, available monthly)
# 2. Filter: etat_administratif_etablissement == 'A' for active
# 3. Filter: date_fermeture is null or > Dec 31 of year Y-1
# 4. Join to ZE2020 via: code_commune_etablissement → CODGEO in commune_to_ze2020_2026.csv
# 5. Aggregate: COUNT(*) per ZE2020 for each year
```

**Availability:**
- 2021: SIRENE Dec 2020 stock → YES (lagged T-1)
- 2022–2025: YES (lagged T-1)
- 2026–2027: YES (lagged T-1, current year requires waiting for Dec stock)

**Training safe:** YES with T-1 lag  
**Risk:** MEDIUM — IAT snapshot frozen at 2020–2022; reconstruct annually from open data

---

### Features: `total_workforce`, `avg_workforce_per_estab`

**Atlas source:** `establishment.workforce_count` — maps to SIRENE field `trancheEffectifsEtablissement`  
**External source:** `source_confirmed` — same SIRENE API/files  
**Coverage limitation:** Only 31% of IAT establishments have `workforce_count > 0`

**Better reconstruction source for full employment:**
- **CLAP** (Connaissance Locale de l'Appareil Productif): employment by ZE2020 and sector — https://www.insee.fr/fr/statistiques/2021201
- **ESANE** (Elaboration des Statistiques Annuelles d'Entreprises): employment by NAF × territory
- **DSN** (Déclaration Sociale Nominative, URSSAF): most complete employment data, available via DARES

**Availability:** Annual, T+18 months for CLAP/ESANE  
**Training safe:** YES with T-2 lag  

---

### Features: `n_distinct_naf4`, `naf4_shannon_diversity`, `naf4_hhi`

**Atlas source:** `establishment.main_activity_id` → `nomenclature_activity.code` (NAF code)  
**External source:** `source_confirmed` — SIRENE field `activitePrincipaleEtablissement` + NAF Rev2 nomenclature  
**NAF Rev2 nomenclature URL:** https://www.insee.fr/fr/information/2120875  
**NAF Rev2 CSV:** https://www.insee.fr/fr/information/2491454  

**Key point:** NAF Rev2 is stable since 2008. No nomenclature update expected until possible NAF Rev3 (announced for 2025+). Any NAF Rev3 transition would require a crosswalk.

**Annual update recipe:**
```python
# Same as establishment stock, add group-by NAF code:
sirene_Y = load_sirene_stock(year=Y-1)
ze_naf = sirene_Y.groupby(['ze2020', 'activitePrincipaleEtablissement']).size().reset_index()
diversity = ze_naf.groupby('ze2020').apply(shannon_entropy)
hhi = ze_naf.groupby('ze2020').apply(hhi_index)
```

**Training safe:** YES with T-1 lag  

---

## 2. Product Complexity (PCI)

### Feature: `avg_pci_naf_weighted`

**Atlas source:** `rank_economic_growth` (columns: `hs4`, `pci_2019`, `pci_norm`) × `nomenclature_activity_product_proximity`

> ⚠️ **WARNING:** The table `rank_economic_growth` does **NOT** contain GDP growth rates. It contains the Harvard Atlas **Product Complexity Index (PCI)** for 2019. The name is misleading. Always refer to this feature as PCI in documentation and code.

**External source:** `source_inferred` — Harvard Atlas of Economic Complexity / Observatory of Economic Complexity (OEC)  
**Harvard Atlas URL:** https://atlas.cid.harvard.edu/  
**OEC data download:** https://oec.world/en/resources/data  
**Harvard Dataverse:** https://dataverse.harvard.edu/dataverse/atlas  

**PCI definition:** PCI measures the productive knowledge required to make a product, inferred from the diversity and ubiquity of countries that export it (Hidalgo & Hausmann, 2009).

**Available vintages:**
| Year | Status |
|---|---|
| 2012 | Available on OEC |
| 2015 | Available on OEC |
| 2017 | Available on OEC |
| 2019 | In Atlas/IAT as `pci_2019` |
| 2021 | Available on OEC |
| 2023 | Available on OEC |

**Methodology for ZE2020 aggregation:**  
PCI is a product-level indicator. Aggregation to ZE2020 uses `nomenclature_activity_product_proximity` as weights:
```
avg_pci(ZE2020) = SUM_naf [n_estab(naf, ZE2020) × SUM_hs4 [proximity(naf, hs4) × pci(hs4)] / SUM_hs4[proximity(naf, hs4)] ] / SUM_naf [n_estab(naf, ZE2020)]
```

**Coverage:** 295/1707 NAF codes have product proximity mapping → 60.1% of active establishments contribute  

**Annual update:** Not needed — PCI is structural. Update only when a new Harvard Atlas release is available (~every 2 years).  
**Training safe:** YES — static structural, safe for all HERALD years (2012–2027)  

---

## 3. Productive Resilience

### Feature: `avg_resilience_naf_weighted`

**Atlas source:** `rank_productive_resilience` (columns: `hs4`, `efficiency`, `redundancy`, `alpha`, `resilience`, `resilience_norm`)  
**Source status:** `proprietary_or_internal`

**What we know from DB inspection:**
- Computed from `util_efficiency_and_redundancy_per_flows_2019` (3.5M rows of HS4 × country pair × trade flow network metrics)
- Columns in source: `hs4`, `i` (country), `j` (country), `t_i_j` (bilateral flow), `efficiency_i_j`, `redundancy_i_j`
- The `resilience` value (~0.1597) is nearly constant across products, while `resilience_norm` provides discriminating [0,1] range
- The `alpha` parameter (~0.367) is also nearly constant — suggests global network property

**Likely methodology:** Network resilience framework based on information theory — efficiency = how directly goods flow, redundancy = number of alternative trade routes. Possibly inspired by:
- Jiang & Lorente (2018) ecosystem resilience framework
- Hidalgo complexity fitness metrics
- Moulaert & Sekia complexity of local production systems

**Reproducibility:** NOT directly reproducible without the exact formula. The source trade flow data (world exports by HS4 × country 2019) is available from BACI/COMTRADE, but the resilience computation formula is undocumented in the DB.

**Use recommendation:** Use `avg_resilience_naf_weighted` as a **static structural context feature** only. Do not treat it as a "current" indicator. Its value reflects the resilience of France's product basket in 2019 trade conditions.

**Training safe:** B_static_context — safe as structural feature, cannot be updated annually  

---

## 4. Green Production Score

### Feature: `avg_green_naf_weighted`

**Atlas source:** `rank_green_production` (columns: `hs4`, `green_norm`)  
**Source status:** `source_unknown`

**What we know:**
- `green_norm ∈ [0,1]` per HS4 product
- National mean for ZE2020 = 0.004 (extremely low)
- High values concentrated in industrial/energy products (HS4 84XX: machines/turbines, 85XX: electrical equipment)
- Services NAF codes have near-zero green scores

**Candidate sources (not confirmed):**
1. **EU Taxonomy Regulation** (2021): defines sustainable activities at NACE level → could be mapped to HS4 — https://finance.ec.europa.eu/sustainable-finance/tools-and-standards/eu-taxonomy-sustainable-activities_en
2. **OECD ENV-LINKAGES**: green growth indicators by trade/sector — https://www.oecd.org/env/
3. **IEA Clean Energy Technology** classification: defines clean energy products by HS code
4. **OECD/WTO Green Goods List**: environmental goods by HS code

**Decision rule:** Do **not** use `avg_green_naf_weighted` for HERALD training until:
- Source is confirmed
- Methodology is documented
- Vintage is established (risk of future-knowledge if source post-dates training years)

**Use:** Post-model interpretation only — "which ZEs produce more green products" as a dashboard layer after HERALD forecast.

---

## 5. Maslow Basic Necessity Score

### Feature: `avg_maslow_naf_weighted`

**Atlas source:** `rank_basic_necessities` (columns: `hs4`, `maslow_cat`, `maslow_norm`)  
**Source status:** `proprietary_or_internal`

**What we know:**
- Maslow hierarchy applied to HS4 products: physiological → safety → social → esteem → self-actualization
- `maslow_cat` (float) = Maslow tier
- `maslow_norm ∈ [0,1]` = normalized position within tier
- Paris: mean = 0.37 (services, higher tiers)
- Rural/industrial: mean < 0.10 (basic goods production)

**Reproducibility:** The product-to-Maslow mapping table is internal to the Atlas system. No standard external crosswalk known. Could potentially be reconstructed with expert knowledge (food HS4 → physiological, medical HS4 → safety, etc.) but would not be identical.

**Use recommendation:** Treat as **static structural context** for post-model interpretation. Low leakage risk (no temporal information). Useful for framing which ZEs produce "necessity goods" vs. "luxury goods."

**Training safe:** B_static_context — can be tested as structural feature, cannot be updated  

---

## 6. NAF Proximity (Product-Space and Semantic)

### Features: `mean_naf_proximity`, `mean_semantic_proximity`

**Atlas source:** `vw_naf_proximity` materialized view (84,264 NAF × NAF pairs)  
**Source status:** `source_inferred`

#### Proximity column (product-space)
**Methodology (inferred):** Based on Harvard Atlas product space methodology adapted to NAF activities:
1. For each NAF activity, identify associated HS4 products (via `nomenclature_activity_product_proximity`)
2. Compute proximity between two NAF activities = cosine similarity of their HS4 product baskets weighted by RCA
3. Produces `proximity` column in `vw_naf_proximity`

This is analogous to Hidalgo's product space density but applied to NAF sectors.

**Reproducibility:** Can be recomputed from:
- `nomenclature_activity_product_proximity` (NAF→HS4 proximity) — present in DB
- Annual RCA data from Douanes France

#### Semantic column (NLP)
**Methodology (inferred):** NLP embeddings on NAF activity name descriptions (`nomenclature_activity.name_ref2` hstore field, French + English):
- `nomenclature_activity_semantic_proximity` confirms NLP-based similarity (float NACE codes, similarity 0.79–0.95)
- Embedding model: **unknown** — likely sentence-transformers or word2vec trained on activity descriptions

**Reproducibility:** Can be re-embedded with open-source models:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# Embed all NAF descriptions, compute cosine similarity
```
Results would be similar but not identical to original.

**Training safe:** B_static_context — matrix is static, annual update = recompute sector presence from SIRENE T-1  

---

## 7. IO Linkage (NACE Input-Output)

### Features: `nace_io_mean`, `nace_io_total`

**Atlas source:** `nace_proximities` (235 NACE codes, 2,816 pairs, weight ∈ [0.75, 1.0])  
**Derived from:** `raw_iot_secteur_nace` (IO matrix, wide format, NACE × NACE)  
**Source status:** `source_inferred` — INSEE TES or Eurostat Supply-Use Tables

**Likely source:**
- **INSEE Tableaux Entrées-Sorties (TES)** — French IO table at NACE level: https://www.insee.fr/fr/statistiques/2022724
- **Eurostat Supply-Use Tables (SUTS)** — annual provisional, NACE A64 level: https://ec.europa.eu/eurostat/web/esa-supply-use-input-tables

**Key observation:** `nace_proximities` weights are filtered to range [0.75, 1.0], meaning only high-weight IO linkages are included. This is likely a threshold filter on the original IO coefficients. The `nace_io_mean` is ~0.80 nationally with low variance — **limited discriminating power** for ZE2020 differentiation.

**Available vintages:**
| Source | Years available |
|---|---|
| INSEE TES symmetric | 2010, 2014–2015, 2019 |
| Eurostat SUTS | 2010–2020 (provisional) |

**Annual update recipe:**
```python
# 1. Download INSEE TES 2019 (symmetrical IO table, NACE A64 or A38)
# 2. Compute IO proximity: io_coeff(i,j) = z_ij / x_j (Leontief coefficient)
# 3. Filter: keep pairs where io_coeff > threshold (0.75 in Atlas)
# 4. Join to ZE2020 via co-present NACE codes (from SIRENE T-1)
# 5. Aggregate: mean IO weight per ZE2020
```

**Training safe:** YES — static structural, update only when new TES vintage available  

---

## 8. Recommendation Density (Post-Model Only)

### Feature: `recommendation_density_postmodel`

**Atlas source:** `recommendation` table (117,644 rows), types: CUSTOMER / SUPPLIER / PRODUCT / PARTNERSHIP / PRODUCTION_UNIT  
**Source status:** `proprietary_or_internal` — computed by `func_list_partner()` and `create_ia_establishment_potential_partners()`

**Coverage issue:** Only **39/306 ZE2020** have any recommendations. The engine was run for a subset of establishments only, creating a partial and potentially biased indicator.

**Reproducibility:** NOT reproducible — requires running the full Atlas recommendation engine on all 1.55M establishments, which:
1. Takes significant compute time
2. Requires the full IAT DB to be available
3. Results may differ if re-run (stochastic elements)

**Training safe:** NO — post-model layer only  
**Safe for dashboard:** YES — after HERALD prediction, can show which high-growth ZEs also have high Atlas recommendation activity  

---

## 9. Annual Reconstruction Roadmap

### What can be reconstructed today (open data available)

| Feature group | Source to download | Priority |
|---|---|---|
| Establishment stock, NAF diversity, HHI | SIRENE base SIRET (monthly) | HIGH |
| Workforce proxy | CLAP emploi localisé par ZE | MEDIUM |
| PCI | OEC Harvard Atlas data (CSV) | HIGH |
| IO linkage | INSEE TES 2019 symmetrical (CSV) | MEDIUM |
| NAF sector presence for proximity | Derived from SIRENE | HIGH |

### What requires additional work

| Feature group | Blocker | Recommendation |
|---|---|---|
| Resilience | Formula unknown | Use as static context only; do not update |
| Green score | Source unknown | Investigate EU Taxonomy → HS4 crosswalk; post-model only until confirmed |
| Maslow coverage | Mapping internal | Use as static context; acceptable without update |
| Semantic proximity | Model unknown | Re-embed with sentence-transformers; mark as approximate |
| Recommendation density | Engine partial, internal | Post-model only; do not update |

### What is NOT needed for HERALD training

The following are valuable for the recommendation layer but not required for HERALD model training:
- `recommendation_density_postmodel`
- `avg_green_naf_weighted` (until confirmed)
- `avg_maslow_naf_weighted` (context only)
- `mean_semantic_proximity` (structural context)

---

## 10. API and Download Reference

| Source | URL | API? | Notes |
|---|---|---|---|
| INSEE SIRENE base SIRET | https://www.data.gouv.fr/fr/datasets/base-siret/ | YES (SIRENE API v3) | Full stock CSV ~1.5GB monthly |
| INSEE SIRENE API v3 | https://api.insee.fr/ | YES | Token required, rate-limited |
| INSEE NAF Rev2 | https://www.insee.fr/fr/information/2491454 | NO | Static CSV, stable since 2008 |
| INSEE CLAP emploi | https://www.insee.fr/fr/statistiques/2021201 | NO | Annual CSV download |
| INSEE TES IO table | https://www.insee.fr/fr/statistiques/2022724 | NO | Excel/CSV download |
| Harvard Atlas PCI | https://atlas.cid.harvard.edu/ | PARTIAL | OEC API limited free tier |
| OEC product data | https://oec.world/en/resources/data | PARTIAL | CSV download by year |
| Harvard Dataverse | https://dataverse.harvard.edu/dataverse/atlas | NO | Direct download |
| Eurostat SUTS | https://ec.europa.eu/eurostat/web/esa-supply-use-input-tables | YES (Eurostat API) | JSON/TSV via eurostat package |
| DGDDI Douanes | https://www.douane.gouv.fr/fiche/statistiques-du-commerce-exterieur | NO | Manual download annually |
| CEPII BACI | https://www.cepii.fr/CEPII/fr/bdd_modele/bdd_modele_item.asp?id=37 | NO | Registration + CSV download |
| EU Taxonomy | https://finance.ec.europa.eu/sustainable-finance/tools-and-standards/eu-taxonomy-sustainable-activities_en | NO | PDF + Excel annexes |
