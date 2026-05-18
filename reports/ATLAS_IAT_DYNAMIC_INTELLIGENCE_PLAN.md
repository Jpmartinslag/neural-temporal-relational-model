# Atlas IAT — Dynamic Intelligence Plan for HERALD

**Date:** 2026-05-18  
**Status:** Draft — awaiting DB restoration for validation  
**Purpose:** Transform the static Atlas/IAT snapshot (2022) into an annually updatable intelligence layer compatible with HERALD (ZE2020, A10, 2012–2025).

---

## 1. Core Problem: Atlas/IAT is Static

The Atlas/IAT database is a snapshot created on 2022-01-20. Its trade data is frozen at 2018–2019. Its establishment data reflects SIRENE circa 2022. Its recommendation engine produces scores for a single point in time.

**A static layer used in HERALD training would introduce data leakage for any backtest year < 2022.**

The solution is to:
1. Classify each indicator by its temporal risk (see Section 3).
2. For high-leakage indicators: use only as post-model interpretation layer.
3. For updatable indicators: define an annual computation recipe from open sources.
4. Reconstruct a temporal panel where possible.

---

## 2. Indicator Categories

### Category A — Train candidate (ex-ante safe)

These indicators can enter HERALD training, provided their source data is **available before the year being predicted** and uses no information posterior to the target year.

Condition: `source_year(indicator) ≤ target_year - 1` (minimum T-1 lag).

Examples:
- Product complexity (PCI): static, pre-2018 vintage → safe for all HERALD years
- NACE IO coefficients: static benchmark → safe for all years
- Sector diversity / HHI: reconstructible from SIRENE stock T-1
- Export RCA (T-2): safe if Douanes data T-2 is used

### Category B — Interpretation layer

Computed from the HERALD output, or describes structural features not suitable for training:
- `mean_naf_proximity` within ZE2020 (structural, changes slowly)
- Economic growth rank (depends on Atlas vintage)
- Sector specialization profiles

### Category C — Recommendation layer

Generated after HERALD prediction, using the forecast to enrich recommendations:
- `supplier_potential_score` (static 2022 snapshot → post-model only)
- `customer_potential_score` (same)
- `recommendation_density`
- Green potential, basic need coverage

### Category D — Not safe / do not use

- Any feature derived from the 2022 snapshot that would contaminate backtests for years 2012–2021
- Features with unknown source or vintage
- Any feature that uses data posterior to the target year

---

## 3. Annual Update Recipes

### 3.1 Establishment stock by sector per ZE2020

**Source:** INSEE SIRENE (base SIRET), annual stock  
**URL:** https://www.data.gouv.fr/fr/datasets/base-siret/  
**Frequency:** Annual (full file, ~1.5 GB)  
**Publication lag:** ~12 months (T+12 for year T)  
**Formula:**
```sql
-- For year Y:
SELECT ze2020, naf_a10, COUNT(*) AS n_establishments
FROM sirene_stock_Y
JOIN commune_to_ze2020 ON commune_code = code_commune_etablissement
JOIN naf_a10_mapping ON activite_principale_registre = naf_code
WHERE etat_administratif_etablissement = 'A'  -- active
GROUP BY ze2020, naf_a10;
```
**Backtest availability:**
- 2021: use 2020 stock (available since ~2021-12)
- 2022: use 2021 stock
- 2023+: use T-1 stock

**Temporal reconstruction:** INSEE publishes annual snapshots. Historical SIRENE stocks (2010–2023) available via data.gouv.fr or DARES/CLAP.

---

### 3.2 Sector diversity and HHI per ZE2020

**Source:** Same as 3.1 (derived from establishment stock)  
**Formula:**
```python
# For each ZE2020 × year:
shares = n_estab_by_A10 / total_estab
diversity = -np.sum(shares * np.log(shares + 1e-10))  # Shannon entropy
hhi = np.sum(shares ** 2)
```
**Availability:** Same as 3.1 (T-1 lag minimum).

---

### 3.3 Export RCA per ZE2020 (via department proxy)

**Source:** Direction Générale des Douanes (DGDDI)  
**URL:** https://www.douane.gouv.fr/fiche/statistiques-du-commerce-exterieur  
**Frequency:** Annual  
**Publication lag:** ~18 months (T+18 for year T)  
**Formula (Balassa RCA):**
```
RCA(dep, hs4, t) = (X_dep_hs4_t / X_dep_t) / (X_FR_hs4_t / X_FR_t)
```
Where X = export value.

**ZE2020 proxy:** Department → ZE2020 via commune population weighting or dominant ZE per department.

**Backtest availability:**
- 2021 HERALD prediction: use 2019 Douanes (T-2 lag) — safe
- 2025 HERALD prediction: use 2023 Douanes (T-2 lag) — check publication calendar

---

### 3.4 World trade denominators for RCA

**Source:** UN COMTRADE or CEPII BACI  
**URL:** https://www.cepii.fr/CEPII/fr/bdd_modele/bdd_modele_item.asp?id=37  
**Frequency:** Annual (BACI published ~18 months after reference year)  
**Use:** World-level denominator for Balassa RCA formula.  
**Dynamic update:** Download annual BACI HS4 file, compute `X_world_hs4_t / X_world_t`.

---

### 3.5 Product Complexity Index (PCI)

**Source:** Harvard Atlas of Economic Complexity / OEC  
**URL:** https://atlas.cid.harvard.edu/  
**Frequency:** Multi-year (updated every 2–3 years in Harvard releases)  
**Status for HERALD:** **Treat as static.** PCI is a long-run structural measure. Using PCI vintage ≤ 2018 for all HERALD years (2012–2025) is methodologically defensible.  
**Dynamic update:** If a new Harvard release is available (OEC publishes updates), can refresh PCI table. No annual need.

---

### 3.6 Input-Output (NACE) coefficients

**Source:** INSEE Tableaux Entrées-Sorties (TES) or Eurostat Supply-Use Tables  
**URL (INSEE):** https://www.insee.fr/fr/statistiques/2022724  
**URL (Eurostat):** https://ec.europa.eu/eurostat/web/esa-supply-use-input-tables  
**Frequency:** Benchmark every 5 years; provisional annually  
**Status for HERALD:** **Treat as static structural feature.** The 2015 or 2019 IO table is appropriate for all HERALD years.  
**Update trigger:** When 2020 French TES is published (~2023–2024), consider updating for forecasts from 2022 onward.

---

### 3.7 Establishment creation counts (SIDE target)

**Already used by HERALD as target variable.**  
Do not double-use as feature and target. If used as lag feature (`side_lag_1` etc.), HERALD already handles this.  
Atlas/IAT adds sectoral and complexity enrichment **on top of** the SIDE signal.

---

### 3.8 Productive resilience

**Current source in Atlas/IAT:** Likely derived from product space density and diversity (Harvard Atlas methodology). Source not confirmed.

**Open-source reconstruction:**
```
resilience(ZE2020, t) = product_space_density × sector_diversity × (1 - HHI)
```
Where product_space_density is computed from RCA(t-2) and Harvard proximity matrix.

**Availability:** Once RCA is reconstructed annually (Section 3.3), resilience is reconstructible.

---

### 3.9 Green production score

**Current source in Atlas/IAT:** Not confirmed. Possible bases:
- EU Taxonomy Regulation (2021) mapped to HS4/NACE
- OECD Green Growth Indicators
- IEA clean energy trade flows

**Recommendation:** Do not use for training until source is confirmed. Retain as post-model recommendation layer.

**Open-source alternative:**
- EC JRC publication: "EU Taxonomy for sustainable activities" crosswalk to NACE/HS4
- OECD ENV-LINKAGES: https://www.oecd.org/env/

---

### 3.10 Basic necessity ranking

**Current source in Atlas/IAT:** Likely derived from a UN/SDG product classification.

**Open-source alternative:**
- FAO food commodity classifications mapped to HS4
- WHO essential medicines list
- UN SDG indicator framework

**Recommendation:** Post-model layer only until confirmed.

---

## 4. Temporal Availability Matrix (Summary)

See `data/interim/atlas_iat/dynamic_feature_plan_by_year.csv` for the full feature × year matrix.

Key summary:

| Feature block | 2021 | 2022 | 2023 | 2024 | 2025 | 2026+ |
|---|---|---|---|---|---|---|
| PCI (static) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| IO coefficients (static) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SIRENE stock (T-1 lag) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Douanes RCA (T-2 lag) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| World RCA denominator (T-2) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Atlas static scores | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Recommendation scores | post-model only |||||| 

Legend: ✓ = observed_available or lagged_available, ✗ = not_safe

---

## 5. Data Leakage Control Rules

### Rule 1 — No future data
A feature used to predict year Y must be computable **exclusively from data published before the start of year Y** (or at most T-1 published data, with documented lag).

### Rule 2 — No static snapshot for past years
The 2022 Atlas/IAT snapshot must **not** be used as a feature for backtests ≤ 2021 without temporal reconstruction.

Exception: Purely structural features (PCI, IO coefficients, proximity matrix) whose methodology clearly uses pre-2018 data can be used for all years.

### Rule 3 — No normalization across time
If a feature requires computing a ratio (e.g., share of sector within ZE2020), the denominator must also be from the same temporal window.

### Rule 4 — Document vintage for every feature
Every Atlas-derived feature included in HERALD training must carry a documented vintage label:
- `pci_vintage: harvard_2018`
- `rca_vintage: douanes_2019`
- `io_vintage: insee_tes_2015`

### Rule 5 — Separate static from dynamic
Static features (PCI, IO, proximity) → column name suffix `_static`  
Dynamic features (RCA, SIRENE stock, diversity) → column name suffix `_t1` or `_t2` (lag indicator)

---

## 6. Open Source Data Calendar

| Source | URL | Annual release | Typical lag |
|---|---|---|---|
| INSEE SIRENE (base SIRET) | https://www.data.gouv.fr/fr/datasets/base-siret/ | Monthly stock | 1 month |
| INSEE CLAP (emploi localisé) | https://www.insee.fr/fr/statistiques/2021201 | Annual | 18 months |
| DGDDI Douanes exports/imports | https://www.douane.gouv.fr/ | Annual | 18 months |
| CEPII BACI world trade | https://www.cepii.fr/ | Annual | 18 months |
| Harvard OEC complexity | https://oec.world/en/resources/data | Every 2–3 years | Variable |
| INSEE TES (IO table) | https://www.insee.fr/fr/statistiques/2022724 | Every 5 years (benchmark) | 3 years |
| Eurostat SUTS | https://ec.europa.eu/eurostat/web/esa-supply-use-input-tables | Annual (provisional) | 24 months |
| France Travail ROME | https://www.pole-emploi.org/opendata/ | As revised | Variable |
| INSEE COG | https://www.insee.fr/fr/information/2666684 | Annual | 3 months |
| INSEE NAF rev2 | https://www.insee.fr/fr/information/2120875 | Stable (since 2008) | n/a |
