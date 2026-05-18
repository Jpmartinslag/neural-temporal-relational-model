# Atlas IAT — Dynamic Intelligence Plan for HERALD

**Date:** 2026-05-18  
**Status:** Phase 2 — Updated with verified DB data and coverage analysis  
**Restore DB:** `iat_restore` (PostgreSQL 14, local)

---

## 0. Controlled Growth Strategy

HERALD is currently in a noise-reduction phase: one dataset (SIDE), five features, no external data, no manual flags. The objective is to establish a robust, stable baseline before adding any external layer.

Atlas/IAT will **not** be dumped into HERALD. The integration follows a staged protocol:

```
Stage 0: HERALD SIDE5 baseline (current — Frente A)
Stage 1: Atlas/IAT post-model interpretation only (no training impact)
Stage 2: Static structural features tested in isolation (PCI, IO, proximity)
Stage 3: Dynamic annual features with leakage control
Stage 4: Full integration only if Stage 2-3 pass criteria met
```

Each Atlas/IAT feature requires:
1. A documented hypothesis (H1–H8)
2. A source with confirmed vintage
3. A leakage-free aggregation path
4. A measurable acceptance criterion

No feature enters training without passing all four conditions.

---

## 1. Coverage Analysis (verified)

### Path: establishment → address → city → insee_code → ZE2020

| Step | Count | % of total |
|---|---|---|
| Total establishments | 1,550,453 | 100% |
| With `address_id` | 1,550,453 | 100.0% |
| With city (via address) | 1,528,680 | 98.6% |
| With `insee_code` | 1,528,680 | 98.6% (all cities have insee_code) |
| Mappable to ZE2020 (after arrondissement fix) | **1,520,612** | **98.1%** |
| Active & mappable | 1,094,478 | 93.1% of active |

### ZE2020 zone coverage

| Metric | Value |
|---|---|
| Total ZE2020 in mapping | 306 |
| ZE2020 with at least 1 establishment | **306 / 306 (100%)** |
| Min active establishments per ZE2020 | 329 |
| Max active establishments per ZE2020 | 86,612 (Paris) |
| Mean active establishments per ZE2020 | 3,748 |

**Coverage is excellent.** All 306 ZE2020 zones have IAT establishment data. No blind spots.

### Arrondissement fix

Paris (751XX), Lyon (6938X), and Marseille (1320X) use arrondissement codes in the IAT database but city-level codes in `commune_to_ze2020_2026.csv`. The fix maps:
- `751XX` → `75056` (Paris)
- `6938X` → `69123` (Lyon)  
- `1320X` → `13055` (Marseille)

Without fix: 92.9% coverage. After fix: **98.1%** coverage.

### Unmapped establishments (1.9%)

Remaining unmapped (~29,841 establishments) are:
- Overseas territories not in ZE2020 panel (Martinique, Guadeloupe, Réunion, Guyane: 97XXX codes)
- A small number of communes with COG code changes between IAT vintage (2020) and ZE2020 mapping (2026)
- These are correctly excluded from the HERALD panel (which covers metropolitan France only)

---

## 2. Static Feature Prototype (v0)

**File:** `data/interim/atlas_iat/atlas_iat_ze2020_static_features_v0.csv`  
**Generated:** 2026-05-18  
**Rows:** 306 (one per ZE2020)  
**Vintage note:** Snapshot of SIRENE data circa 2020-2022. **Not safe for backtest ≤2021 without temporal reconstruction.**

### Columns in v0

| Column | Type | Description |
|---|---|---|
| `ze2020` | string | ZE2020 code |
| `libze2020` | string | ZE2020 name |
| `n_total_estab` | int | All establishments mapped to ZE2020 |
| `n_active_estab` | int | Active establishments (administrative_status = true) |
| `n_inactive_estab` | int | Ceased/inactive establishments |
| `active_share` | float | n_active / n_total |
| `total_workforce` | int | Sum of workforce_count across all establishments |
| `avg_workforce_per_estab` | float | Mean workforce per establishment |
| `n_distinct_naf4` | int | Count of distinct NAF4 codes in ZE2020 |
| `n_estab_with_workforce` | int | Establishments with workforce_count > 0 |
| `naf4_shannon_diversity` | float | Shannon entropy of NAF4 distribution [-Σ p ln(p)] |
| `naf4_hhi` | float | Herfindahl-Hirschman Index of NAF4 [Σ p²] |

### Top 5 ZE2020 by active establishments

| ZE2020 | Name | n_active | diversity | HHI |
|---|---|---|---|---|
| 1109 | Paris | 86,612 | 3.93 | 0.036 |
| 8421 | Lyon | 20,933 | 4.44 | 0.025 |
| 7625 | Toulouse | 14,744 | 4.06 | 0.048 |
| 7505 | Bordeaux | 13,551 | 4.16 | 0.042 |
| 7616 | Montpellier | 13,426 | 3.61 | 0.098 |

---

## 3. Hypotheses by Block

See `data/interim/atlas_iat/atlas_iat_feature_hypotheses.csv` for full details.

### H1 — Productive Diversity

**Claim:** ZEs with higher NAF4 diversity (Shannon entropy) may show more stable establishment creation patterns — shocks in one sector are buffered by other sectors.

**Formula:** `diversity = -Σ_i p_i × ln(p_i)`, where `p_i = n_estab_in_naf4_i / total_estab`  
**Feature:** `naf4_shannon_diversity` (computed in v0 CSV)  
**Leakage:** MEDIUM — static 2022 snapshot. For backtest ≤2021: reconstruct from SIRENE stock T-1.  
**Expected signal:** Negative correlation between diversity and WMAPE variance across seeds.

### H2 — Sectoral Concentration

**Claim:** ZEs with high HHI are more exposed to sector-specific shocks, increasing forecast uncertainty.

**Formula:** `HHI = Σ_i p_i²`  
**Feature:** `naf4_hhi` (computed in v0 CSV)  
**Leakage:** MEDIUM — same reconstruction required.  
**Expected signal:** Positive correlation between HHI and WMAPE instability, especially in 2021.

### H3 — Productive Proximity

**Claim:** ZEs where co-present sectors have high NAF proximity scores may show more sustained growth — complementary sectors reinforce each other.

**Formula:** `mean_naf_proximity = mean(proximity(naf_i, naf_j)) for all (i,j) pairs present in ZE2020`  
**Source table:** `vw_naf_proximity` (84,264 pairs, range [0, 2.76])  
**Leakage:** LOW — proximity matrix is static structural data.  
**Expected signal:** Positive correlation between mean_naf_proximity and smoother A10 growth trajectories.

### H4 — Input-Output Linkages

**Claim:** Sectors with strong IO linkages within a ZE (i.e., they buy from / sell to each other) may show more resilient creation dynamics.

**Formula:** `io_strength = Σ_{(i,j) both in ZE} io_coeff(i,j)` using `iot_production_nace` and `iot_consume_nace`  
**Source:** IO table (NACE level) — static, 2015 or 2019 vintage  
**Leakage:** LOW — IO coefficients are structural, not time-sensitive.  
**Expected signal:** Higher IO strength → lower WMAPE in A10-C (industry) and A10-G (trade).

### H5 — Product Complexity

**Claim:** ZEs with more complex productive bases (higher mean PCI) may show different growth dynamics, potentially more sustained or less volatile.

**Formula:** `avg_pci = weighted_mean(pci_2019_of_products_declared_by_establishments_in_ZE)`  
**Source:** `rank_economic_growth` (column `pci_2019`) — Harvard Atlas vintage 2019  
**Leakage:** LOW — PCI is a long-run structural indicator. Use for all HERALD years.  
**Note:** `rank_economic_growth` is **not a growth rate** — it is PCI. Name is misleading.  
**Expected signal:** PCI quartile analysis. High-PCI ZEs may show different creation patterns in A10-C.

### H6 — Green Production / Resilience

**Claim:** Green production score and productive resilience (network efficiency × redundancy) may explain cross-sectional variation in establishment creation stability.

**Source:** `rank_green_production` (green_norm), `rank_productive_resilience` (resilience_norm = efficiency × redundancy)  
**Leakage:** LOW — both are static structural indicators.  
**Restriction:** Green source not confirmed → **post-model only** until validated.  
**Resilience:** Source is network analysis on 2019 trade flows → **safe as static context feature**.

### H7 — Post-Model Recommendation Layer

**Claim:** Atlas/IAT partnership recommendations, aggregated by ZE2020, can enrich HERALD output with economic intelligence even without improving WMAPE.

**Features:** `recommendation_density`, `mean_partner_score`  
**Source:** `recommendation`, `ia_establishment_potential_partners`  
**Leakage:** HIGH — 2022 static snapshot. **Post-model only, never in training.**  
**Use:** After HERALD predicts "Zone X is accelerating in sector G", Atlas layer adds: "Zone X has 847 active recommendations targeting sector G, with 43 supplier partnerships in neighboring zones."

### H8 — Workforce Structure

**Claim:** Workforce density and composition (avg_workforce_per_estab) may signal agglomeration economies that influence creation dynamics.

**Formula:** `workforce_density = sum(workforce_count) / n_active_estab`  
**Source:** `establishment.workforce_count` (SIRENE tranche effectifs)  
**Leakage:** MEDIUM — SIRENE workforce data available T+18 months. Use T-2 lag.

---

## 4. Annual Update Recipes

### 4.1 Establishment stock + diversity/HHI

**Source:** INSEE SIRENE base SIRET (full stock file, annual)  
**URL:** https://www.data.gouv.fr/fr/datasets/base-siret/  
**Lag:** T+1 to T+12 months (monthly updates available)  
**Formula for year Y:**
```python
# Filter SIRENE stock: active establishments at Dec 31 of year Y-1
sirene_Y = sirene_stock[sirene_stock['etat_administratif_etablissement'] == 'A']
sirene_Y = sirene_Y[sirene_Y['date_fermeture'].isna() | (sirene_Y['date_fermeture'] > f'{Y-1}-12-31')]
# Join to ZE2020 via code_commune_etablissement → CODGEO
sirene_Y = sirene_Y.merge(ze2020_map, left_on='code_commune_etablissement', right_on='CODGEO')
# Compute diversity and HHI per ZE2020 × A10
```

### 4.2 Export RCA per ZE2020

**Source:** Douanes France (DGDDI)  
**URL:** https://www.douane.gouv.fr/fiche/statistiques-du-commerce-exterieur  
**Lag:** T+18 months  
**Formula (Balassa):**
```
RCA(dep, hs4, t) = (X_dep_hs4_t / X_dep_t) / (X_FR_hs4_t / X_FR_t)
```
**ZE2020 proxy:** aggregate department-level RCA to ZE2020 via commune→department→ZE2020 population weighting.

### 4.3 Product complexity (PCI)

**Static.** Use Harvard Atlas 2019 PCI for all HERALD training years.  
No annual update needed unless OEC publishes a new release.

### 4.4 IO linkage strength

**Static.** INSEE TES 2015 or 2019 benchmark.  
Update when 2020 French TES is published (~2023–2024).

---

## 5. Availability Matrix

| Feature | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2027 | Classification |
|---|---|---|---|---|---|---|---|---|
| `naf4_shannon_diversity` (T-1 SIRENE) | not_safe | lagged | lagged | lagged | lagged | lagged | lagged | safe_for_training |
| `naf4_hhi` (T-1 SIRENE) | not_safe | lagged | lagged | lagged | lagged | lagged | lagged | safe_for_training |
| `avg_pci` (static Harvard) | observed | observed | observed | observed | observed | observed | observed | safe_for_training |
| `nace_io_strength` (static TES) | observed | observed | observed | observed | observed | observed | observed | safe_for_training |
| `mean_naf_proximity` (static matrix) | not_safe* | observed | observed | observed | observed | observed | observed | static_context |
| `avg_resilience` (static 2019 flows) | observed | observed | observed | observed | observed | observed | observed | static_context |
| `export_rca` (Douanes T-2) | not_safe | lagged | lagged | lagged | lagged | lagged | lagged | safe_for_training |
| `avg_green_score` (source unconfirmed) | unknown | unknown | unknown | unknown | unknown | unknown | unknown | post_model_only |
| `recommendation_density` (2022 static) | not_safe | not_safe | not_safe | not_safe | not_safe | not_safe | not_safe | post_model_only |
| `supplier_potential_score` (2022 static) | not_safe | not_safe | not_safe | not_safe | not_safe | not_safe | not_safe | post_model_only |

*`mean_naf_proximity` for 2021: proximity matrix is static, but sector presence needs T-1 SIRENE → reconstruct from 2020 SIRENE stock.

---

## 6. Leakage Control Rules

1. **No future data:** A feature for year Y uses only data published before Y begins.
2. **No 2022 snapshot for ≤2021 backtests:** The Atlas/IAT dump is circa 2020–2022. Not safe for 2021 without SIRENE reconstruction.
3. **No cross-period normalization:** HHI and diversity must be computed per year, not normalized across all years simultaneously.
4. **Mark vintage explicitly:** Every feature in training must have `_static`, `_t1`, or `_t2` suffix documenting temporal origin.
5. **IO and PCI are structural exceptions:** IO coefficients and PCI are long-run structural measures — safe for all years without annual update.

---

## 7. Open Source Data Calendar

| Source | URL | Frequency | Lag |
|---|---|---|---|
| INSEE SIRENE (base SIRET) | https://www.data.gouv.fr/fr/datasets/base-siret/ | Monthly | 1 month |
| INSEE CLAP (emploi localisé) | https://www.insee.fr/fr/statistiques/2021201 | Annual | 18 months |
| DGDDI Douanes exports/imports | https://www.douane.gouv.fr/ | Annual | 18 months |
| CEPII BACI world trade | https://www.cepii.fr/ | Annual | 18 months |
| Harvard OEC complexity | https://oec.world/en/resources/data | Every 2–3 years | Variable |
| INSEE TES (IO table) | https://www.insee.fr/fr/statistiques/2022724 | Every 5 years | 3 years |
| France Travail ROME | https://www.pole-emploi.org/opendata/ | As revised | Variable |
| INSEE COG | https://www.insee.fr/fr/information/2666684 | Annual | 3 months |
