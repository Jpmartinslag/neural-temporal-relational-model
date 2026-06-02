# HERALD Phase 4E — Missing-Data Search & Integration Report

**Date:** 2026-06-01
**Scope:** Fill missing data of the Phase 4E European Panel (FR / NL / BE / PT)
**Constraint:** model core untouched; only data layer (`src/data/european_panel/`).

This report documents every source searched, what was integrated, and exactly
what must be downloaded manually where automation was not possible.

**Update 2026-06-02:** NL sector births, BE ONSS tensor 2021–2024, ECB BLS
SME credit standards, and PT sector employment 2024 were integrated. PT 2024
uses ARDECO SNETZ (`Employment by industry`, NUTS3, A10) as a JRC/DG REGIO
continuation of the Eurostat regional-account employment signal. PT target
births/stock were also extended to 2024 via the INE NUTS-2024 indicators
`0014098`, `0014099`, and `0014061`, mapped back to the 25-zone HERALD panel.

---

## 0. Methodological rules enforced

1. No year-`t` data is used to predict `t`. Every signal enters as **lag-1**:
   feature on panel target year `t` uses the *closed reference year* `t-1`.
2. Monthly/quarterly series are aggregated to a **full calendar-year mean**
   (ESI: ≥10 of 12 months required) **before** lagging — so every month used is
   closed before year `t` begins.
3. No manual COVID/rebound flag created (existing `flag_is_covid_year` /
   `flag_is_rebound_year` are already in `NON_PREDICTIVE_FIELDS`).
4. Missing values stay **NaN**, never imputed as 0.
5. `mask_eu_signals` = fraction of the 7 canonical `eu_*` fields observed per row.
6. National-coverage signals are repeated across a country's regions and
   **documented here as national-level** (the `eu_*` fields are national by
   design in the schema; regional NUTS2 variants noted as future upgrades).
7. Different concepts are not mixed without provenance: each signal carries its
   source dataset in `data/raw/european_panel/eu_signals_annual.csv`.

---

## 1. EU common signals — INTEGRATED (Priority 2)

Loaders: `src/data/european_panel/eu_signals/` →
`eurostat_client.py`, `eurostat_gdp.py`, `eurostat_lfs.py`, `ec_bcs.py`,
`assemble.py`, `fetch_all.py`.
Raw cache: `data/raw/european_panel/eurostat/*.json`
Tidy provenance: `data/raw/european_panel/eu_signals_annual.csv` (by reference year).

| schema field | source | dataset | API | temporal cov. | regional cov. | concept | pub. lag | schema-compatible | status |
|---|---|---|---|---|---|---|---|---|---|
| `eu_gdp_growth_lag1` | Eurostat | `nama_10_gdp` (B1GQ, CLV_PCH_PRE) | REST JSON-stat, no key | FR 1975–2025, NL/BE/PT 1996–2025 | national | real GDP volume growth % | t-1 final ~Sep of t (flash ~Feb) | yes | **usable** |
| `eu_unemployment_rate_lag1` | Eurostat | `une_rt_a` (Y15-74, PC_ACT, T) | REST JSON-stat | FR 2003–2025, NL/BE/PT 2009–2025 | national | unemployment rate % | ~6 months | yes | **usable** |
| `eu_employment_rate_lag1` | Eurostat | `lfsi_emp_a` (EMP_LFS, PC_POP, Y20-64, T) | REST JSON-stat | FR 2003–2025, NL/BE/PT 2009–2025 | national | employment rate 20-64 % | ~6 months | yes | **usable** |
| `eu_esi_lag1` | Eurostat / EC DG ECFIN | `ei_bssi_m_r2` (BS-ESI-I, SA) | REST JSON-stat | all 2004–2025 | national | Economic Sentiment Indicator (annual mean) | monthly, ~end of month | yes | **usable** |
| `eu_sts_turnover_lag1` | Eurostat | `sts_trtu_a` | REST JSON-stat | — | national | turnover index | monthly | **partial — not used** | **blocked** |
| `eu_eei_lag1` | EC DG ECFIN | (BCS EEI) | — | — | national | Employment Expectations Indicator | monthly | no clean per-country annual series | **blocked** |
| `eu_credit_standards_lag1` | ECB | BLS `BLS.Q.{country}.ALL.BC.E.SME.B3.ST.S.DINX` | local ECB CSV cache | 2008–2025 | FR/NL/BE/PT | diffusion index for SME credit standards | quarterly | annual mean, lag-1 safe | **usable** |

**Result:** 5 of 7 EU signals filled for **all four countries**, lag-1 safe.
`mask_eu_signals` mean after rebuild: FR 71.4%, NL 71.4%, BE 65.1%, PT 66.7%
(>0 everywhere in covered years). Success criterion (≥3 EU signals; mask>0 for
all) **met**.

**Verification (no lookahead):** FR panel year 2021 carries `eu_gdp_growth_lag1
= -7.4` (= GDP growth of reference year 2020), 2022 → +6.9 (= 2021). Confirmed
against `nama_10_gdp` raw.

### Not-used signals — why blocked

- **`eu_sts_turnover_lag1`** — `sts_trtu_a` covers **wholesale/retail trade only**
  (G), not B–N. Concept is sector-inconsistent with a cross-sector births target;
  using it would violate rule 9 (concept mixing). Left NaN + mask. Future:
  `sts_inpr_a` (industry production) or a properly scoped turnover index.
- **`eu_eei_lag1`** — EEI is published by DG ECFIN but not exposed as a clean
  per-country annual series in `ei_bssi_m_r2`. Left NaN. Future: DG ECFIN BCS
  time-series download (`main_indicators_sa_nace2.zip`).
The ECB BLS pending item above was resolved on 2026-06-02. The selected series is
the per-country SME credit standards diffusion index, quarterly→annual mean,
then lagged by one target year.

---

## 2. Belgium births extension 2021–2024 (Priority 1)

**Current panel:** 2007–2020, 42 arrondissements. Target concept
`enterprise_birth` = StatBel **TVA primo-assujettissements** by arrondissement,
sourced originally from the **be.STAT crosstable** (manual export →
`data/external/belgium/raw/export (1).csv`, Région/Province/Arrondissement/Année/Mois,
2006–2020).

### What was found

| source | file | API/download | temporal | regional | concept | status |
|---|---|---|---|---|---|---|
| StatBel "Évolution mensuelle … NACE 2008" | `Ent_nace_2008_45_fr.xls` | direct .xls download (automated ✓) | 01/2021–12/2025 | **national, by NACE only** | primo-assujettissements | **partial** |
| StatBel "Évolution mensuelle … NACE 2025" | `Ent_nace_2025_45_fr.xlsx` | direct download | 01/2025–03/2026 | national by NACE | primo-assujettissements | partial (new NACE break) |
| be.STAT crosstable (arrondissement) | interactive cube `bestat.economie.fgov.be` | manual crosstab export | 2006–2024 after local extension | **arrondissement** ✓ | primo-assujettissements | **integrated** |

Downloaded national files cached at `data/raw/european_panel/statbel/` for provenance.

### Decision after manual-compatible export: BE adapter modified

The initial automated continuation (`Ent_nace_2008_45_fr.xls`) was national
NACE-level only and was correctly rejected. The later be.STAT arrondissement
export (`data/external/belgium/raw/export_2021_2024.csv`) is compatible with
the 42-zone panel. The BE adapter now combines legacy 2007–2020 with the
2021–2024 StatBel extension.

The ONSS Q4 spreadsheets for 2021–2024 were also downloaded and parsed from
`tableau 8-17`, extending `belgium_qtensor_jobs_panel.csv` to 2008–2024.

### Methodological breaks to document in the paper

- **2018**: StatBel revised the VAT series (enterprise-group concept). Already
  noted in `data/external/belgium/metadata/data_inventory.md`.
- **2025**: switch from NACE 2008 to **NACE 2025** classification — a second
  break; the 2021–2024 extension must use the NACE-2008 file, not NACE-2025.

### BE 2021–2024 source now integrated

- **Dataset:** Assujettissements à la TVA — mouvements démographiques par
  arrondissement (primo-assujettissements & cessations), monthly.
- **Site:** be.STAT — `https://bestat.statbel.fgov.be/bestat/`
  (theme *Entreprises assujetties à la TVA → évolution mensuelle/annuelle*).
- **Filter:** dimensions = Région × Province × **Arrondissement** × Année × Mois;
  measures = *Primo-assujettissements*, *Cessations*, *Entreprises actives*;
  years = **2021, 2022, 2023, 2024** (NACE 2008 / NACE-BEL Rev.2).
- **Format expected:** CSV, same columns as existing
  `data/external/belgium/raw/export (1).csv`
  (`Région, Province, Arrondissement, Année, Mois, Entreprises Act. Fin T-1,
  Primo-assujetissements, Ré-assujetissements, Cessations, Immigration,
  Emigration, Entreprises Act. Fin T`).
- **Raw:** `data/external/belgium/raw/export_2021_2024.csv`
- **Processed target/stock:** `data/external/belgium/processed/belgium_births_stock_extension_2021_2024_42zones.csv`
- **Processed tensor:** `data/external/belgium/processed/belgium_qtensor_jobs_panel.csv`
- **Coverage after rebuild:** 42 zones, target/stock 2007–2024, ONSS tensor
  2008–2024.

---

## 3. Netherlands — sector births A10 by COROP/NUTS3 (Priority 3)

**Current panel after 2026-06-02 update:** 2015–2025, 40 COROP, target
`enterprise_birth` (CBS), `mask_sector_a10 = 1.0`.

| source | dataset | API | temporal | regional | concept | status |
|---|---|---|---|---|---|---|
| CBS StatLine | **83631NED** "Oprichtingen van vestigingen, SBI 2008, regio" | CBS OpenData OData (`opendata.cbs.nl`) | 2007–2025 | COROP | enterprise establishments (oprichtingen) by SBI aggregate | **integrated** |
| CBS StatLine | **81588NED** "Bedrijven; oprichtingen/opheffingen, bedrijfstak/branche SBI 2008" | CBS OData | quarterly | national | births by SBI | partial (national) |
| Eurostat BD | `bd_9bd_sz_cl_r2` / `bd_hgnace2_r3` | REST | varies | NUTS3 partial | enterprise births by NACE | candidate (coverage gaps) |

**Integrated source:** CBS **83631NED**. The builder
`src/data/european_panel/build_nl_cbs_sector_births.py` maps CBS SBI aggregates
to the 9-column HERALD sector contract. CBS section A and O-Q are folded into
`OQ`, consistent with the existing France-compatible sector contract.

- **Raw:** `data/raw/european_panel/cbs/83631NED_TypedDataSet_2007_2025.csv`
- **Processed:** `data/external/netherlands/processed/netherlands_sector_births_cbs_83631NED_corop_a10.csv`
- **Validation:** 760 rows, 40 COROP, 2007–2025. Sector total vs all-sector
  target differs by max 20 establishments at region-year level, consistent with
  CBS disclosure rounding.

---

## 4. Portugal — employment tensor by NUTS3 × CAE/NACE × year (Priority 4)

**Goal:** replace the births-proxy tensor (`flag_has_national_employment = 0`)
with a genuine employment tensor.

| source | dataset | API | temporal | regional | concept | status |
|---|---|---|---|---|---|---|
| Eurostat | **`nama_10r_3empers`** persons employed by NUTS3 (A10 branches `nace_r2`) | REST CSV | 2000–2023 sector breakdown | **NUTS3 × A10** | total employment (jobs) by branch | **integrated through 2023** |
| ARDECO | **SNETZ** employment by industry | REST parquet | 2024 | **NUTS3 × A10** | total employment (jobs) by branch | **integrated for 2024** |
| Eurostat | `lfst_r_lfe2en2` employment by NUTS2 × NACE | REST | annual | NUTS2 only | employment | partial (NUTS2) |
| INE Portugal | Quadros de Pessoal / GEP (employees by NUTS3 × CAE) | INE API / GEP files | annual | NUTS3 × CAE | employees | candidate (employees only, not self-employed) |
| PORDATA | regional employment | manual | annual | NUTS3 | employment total | weak (total only) |

**Integrated source:** **`nama_10r_3empers`** (Eurostat regional accounts,
persons employed by NUTS3 × A10), completed with **ARDECO SNETZ 2024**. The builder
`src/data/european_panel/build_pt_eurostat_employment_tensor.py` maps current
Eurostat NUTS codes back to the 25-region HERALD Portugal panel and writes
`data/external/portugal/processed/portugal_qtensor_employment_eurostat_nuts3.csv`.
Use lag-1 policy (`q_lag[t] = employment[t-1]`).

**PT target extension:** resolved through 2024. The legacy INE NUTS-2013
indicators `0009702`, `0009703`, and `0009819` stop at 2022, but the NUTS-2024
successors `0014098`, `0014099`, and `0014061` expose 2023–2024. The ingestion
maps the NUTS-2024 prefixes back to the 25-region HERALD Portugal panel, with
Grande Lisboa and Península de Setúbal summed into the legacy `PT_170` zone.

- **API:** `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_3empers?geo=PT11&...`
- If only national CAE or only NUTS3 total employment is available → document as
  **not sufficient for a regional tensor** (do not force).
- **Save raw to:** `data/raw/european_panel/eurostat/nama_10r_3empers_PT*.json`

---

## 5. Status summary

| item | status | next step |
|---|---|---|
| EU GDP growth lag1 | ✅ usable, integrated | — |
| EU unemployment lag1 | ✅ usable, integrated | — |
| EU employment rate lag1 | ✅ usable, integrated | — |
| EU ESI lag1 | ✅ usable, integrated | — |
| EU STS turnover lag1 | ⛔ blocked | scope a B–N turnover index |
| EU EEI lag1 | ⛔ blocked | DG ECFIN BCS time-series zip |
| EU credit standards lag1 | ✅ integrated | ECB BLS SME diffusion index |
| BE births 2021–2024 | ✅ integrated | StatBel 42-zone extension |
| BE ONSS tensor 2021–2024 | ✅ integrated | ONSS Q4 `tableau 8-17` |
| NL sector A10 births | ✅ integrated | CBS 83631NED (§3) |
| PT employment tensor | ✅ integrated through 2024 | Eurostat 2000–2023 + ARDECO SNETZ 2024 |
| PT births/stock target | ✅ integrated through 2024 | INE 2008–2022 + INE NUTS-2024 2023–2024 |

**Success criteria check**
- ≥3 EU signals for FR/NL/BE/PT → **5 signals, met.**
- `mask_eu_signals > 0` for all countries in covered years → **met.**
- No `NON_PREDICTIVE_FIELD` used as feature → unchanged (still flagged in schema).
- No temporal lookahead → **verified** (lag-1 mapping + validation layer passes).
- BE extended to 2024 with official compatible regional source → **met**
  (StatBel target/stock + ONSS tensor).
