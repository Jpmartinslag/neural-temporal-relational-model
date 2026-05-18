# Atlas IAT — Database Audit

**Date:** 2026-05-18  
**Status:** Phase 1 — TOC audit (dump inspection without DB restoration)  
**Source file:** `/home/jpdark/Downloads/project_recomm/iat.dump`  
**File size:** 819 MB  
**Dump format:** PostgreSQL custom (pg_dump -Fc)  
**Dump creation date:** 2022-01-20 08:27:28 CET  
**Source DB version:** PostgreSQL 12.9 (Debian 12.9-1.pgdg110+1)  
**Dump tool version:** pg_dump 14.0  
**Database name:** `iat`  
**TOC entries:** 659

---

## 1. Database Restore Status

**The dump has not yet been restored to a local database.**  
The PostgreSQL installation (v14) is running locally, but the `jpdark` system user does not yet have a PostgreSQL role.

To restore, the user should run:

```bash
! sudo -u postgres createuser --no-password --createdb jpdark
createdb iat_restore
pg_restore --no-owner --role=jpdark -d iat_restore /home/jpdark/Downloads/project_recomm/iat.dump
```

> **Note:** PostGIS extensions must be pre-installed in the target database:
> ```sql
> CREATE EXTENSION IF NOT EXISTS postgis;
> CREATE EXTENSION IF NOT EXISTS hstore;
> CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
> ```

Once restored, row counts and column-level inspection can be completed. This audit documents structure from TOC inspection only.

---

## 2. Extensions and Schemas

### Extensions (in dump)

| Extension | Purpose |
|---|---|
| `postgis` | Geometric types and spatial functions |
| `postgis_raster` | Raster spatial support |
| `postgis_sfcgal` | Advanced 3D geometry |
| `postgis_tiger_geocoder` | US Tiger geocoder (likely residual from PostGIS install) |
| `postgis_topology` | Topological geometry |
| `fuzzystrmatch` | String fuzzy matching (Levenshtein etc.) |
| `hstore` | Key-value store in columns |
| `address_standardizer` | Address normalization |
| `address_standardizer_data_us` | US address data (residual) |

### Schemas

| Schema | Purpose |
|---|---|
| `public` | Main application schema — all business tables |
| `tiger` | US geocoder data (PostGIS extension artifact) |
| `tiger_data` | US geocoder data |
| `topology` | PostGIS topology schema |

Only `public` schema is relevant for this project.

---

## 3. Object Inventory

### 3.1 Core Business Tables (public schema)

| Category | Tables |
|---|---|
| **Entities** | `establishment`, `company`, `address`, `city`, `department`, `region`, `country` |
| **Territorial** | `industry_territory`, `industry_territory_dep`, `epci`, `epci_city` |
| **Nomenclature — Activity** | `nomenclature_activity`, `nomenclature_activity_section`, `nomenclature_activity_product_proximity`, `nomenclature_activity_semantic_proximity`, `nomenclature_link_activity_rome`, `macro_sector`, `macro_secteur_naf` |
| **Nomenclature — Product** | `nomenclature_product`, `nomenclature_product_chapter`, `nomenclature_product_section`, `nomenclature_product_proximity`, `nomenclature_product_relationship`, `nomenclature_product_complexity`, `nomenclature_product_resilience`, `nomenclature_product_green`, `nomenclature_product_necessity`, `nomenclature_product_competitive_advantage`, `nomenclature_product_semantic_similarity` |
| **Nomenclature — Jobs** | `nomenclature_rome`, `nomenclature_rome_main_domain`, `nomenclature_rome_professional_domain`, `nomenclature_country` |
| **Scoring / Rankings** | `rank_basic_necessities`, `rank_productive_resilience`, `rank_green_production`, `rank_economic_growth`, `partner_calc`, `partner_calc_iot`, `biom`, `parity`, `nace_proximities` |
| **Recommendations** | `recommendation`, `relation`, `ia_establishment_potential_partners`, `ia_potential_by_iot` |
| **IO Table** | `raw_iot_secteur_nace`, `iot_production_nace`, `iot_consume_nace` |
| **Jobs** | `jobs`, `jobs_link` |
| **Trade Data** | `export_by_country`, `util_export_import`, `util_export_import_dep`, `util_import_region_2019`, `util_import_2019_nc8_a732`, `util_total_exports_by_french_department_2019`, `util_region_2019_*` (7 tables) |
| **World Trade** | `util_mondial_exports_by_hs4`, `util_mondial_exports_per_country`, `util_mondial_imports_per_country`, `util_mondial_exports_per_hs4_2019`, `util_mondial_exports_per_hs4_and_country_2019`, `util_mondial_imports_per_hs4_and_country_2019`, `util_mondial_import_export_2019` |
| **NAF Hierarchies** | `util_nomenclature_naf_a10/a17/a21/a38/a64/a88/a129/a732` (8 tables) |
| **NC2020 Hierarchies** | `util_nomenclature_nc2020_section/chapter/lvl1/lvl2/lvl3` (5 tables) |
| **Crosswalks** | `util_link_a732_cpf6`, `util_link_nc2020_cpf6`, `util_link_hs4_cpf4`, `util_convert_hs2017_hs1992` |
| **Historical** | `util_histo_establishment`, `util_histo_establishment_taille`, `recup_establishment`, `forgotten_establishment`, `import_correctif_entreprise` |
| **Network Analysis** | `util_efficiency_and_redundancy_per_flows_2019` (+ 3 log variants) |
| **Geometry** | `point`, `polyline`, `polyline_point`, `polylines`, `polylines_polyline`, `region_polylines`, `epci_polylines` |
| **System** | `app_config`, `tmp_epp`, `tmp_iot` |

**Total tables: ~90**

### 3.2 Views

| Name | Type | Purpose |
|---|---|---|
| `vw_nomenclature_product_harvard` | VIEW | Harvard product nomenclature join |
| `vw_convert_hs2017_hs1992` | VIEW | HS revision crosswalk |
| `vw_world_coef` | VIEW | World denominator for RCA computation |
| `vw_proximity_123` | VIEW | Combined proximity levels 1+2+3 |

### 3.3 Materialized Views

| Name | Purpose |
|---|---|
| `vw_export_harvard_dep_hs4` | Export matrix: department × HS4 (Harvard method) |
| `vw_export_harvard_reg_hs4` | Export matrix: region × HS4 |
| `vw_export_harvard_it_hs4` | Export matrix: industry_territory × HS4 |
| `vw_import_harvard_dep_hs4` | Import matrix: department × HS4 |
| `vw_import_harvard_it_hs4` | Import matrix: industry_territory × HS4 |
| `vw_import_harvard_reg_hs4` | Import matrix: region × HS4 |
| `vw_rca_by_dep` | Revealed Comparative Advantage by department × product |
| `vw_rca_by_reg` | RCA by region × product |
| `vw_rca_by_it` | RCA by industry_territory × product |
| `vw_resilience_reg` | Productive resilience by region |
| `vw_resilience_it` | Productive resilience by industry_territory |
| `vw_hs4_by_it` | HS4 product presence by industry_territory |
| `vw_hs4_by_dep` | HS4 product presence by department |
| `vw_proximity_importation` | Import-weighted proximity |
| `vw_proximity_importation_dep` | Import-weighted proximity at department level |
| `vw_naf_proximity` | NAF activity proximity matrix (core of partner engine) |
| `vw_establishment_for_partener` | Filtered establishments eligible for partnership |
| `vw_npp_same_meta_code` | Product proximity pairs sharing meta code |
| `vw_siren` | Consolidated SIREN view |

### 3.4 Functions and Procedures

| Name | Type | Purpose |
|---|---|---|
| `func_list_partner(integer)` | FUNCTION | Returns ranked partner list for establishment_id via product space |
| `func_list_partner_iot(integer)` | FUNCTION | Returns partner list via input-output linkages |
| `func_list_partner_alt(integer)` | FUNCTION | Alternative partner scoring (experimental variant) |
| `create_ia_establishment_potential_partners(integer)` | PROCEDURE | Populates `ia_establishment_potential_partners` for one establishment |
| `update_establishment()` | PROCEDURE | Re-enriches establishment records |
| `process_product_faker()` / `(double precision)` | PROCEDURE | Synthetic product data for testing |
| `drop_any_type_of_view_if_exists(text)` | PROCEDURE | Safe DROP VIEW/MATVIEW utility |

### 3.5 Custom Types

| Name | Purpose |
|---|---|
| `recommendation_type` | Enum for recommendation categories |
| `relation_type` | Enum for relation categories (client/supplier/partner/...) |

---

## 4. Foreign Key Chain — Geography

The core path for ZE2020 aggregation is confirmed by indexed columns:

```
establishment.address_id
  → address.city_id
    → city.insee_code  [INDEX city_insee_code_idx]
      → commune_to_ze2020_2026.csv (CODGEO)
        → ZE2020
```

Additional geographic FK chain:

```
city.department_id → department.region_id → region.country_id → country
city.industry_territory_id → industry_territory
```

**Note:** `industry_territory` is a spatial unit internal to the Atlas/IAT system. It is **not** equivalent to ZE2020. The ZE2020 aggregation path must go via `city.insee_code`.

---

## 5. Key Indexes Confirmed

| Index name | Table | Column(s) | Relevance |
|---|---|---|---|
| `city_insee_code_idx` | city | insee_code | **Critical** — ZE2020 join path |
| `establishment_siret_idx` | establishment | siret | SIRENE identity |
| `company_siren_idx` | company | siren | SIRENE identity |
| `establishment_address_id_idx` | establishment | address_id | FK join performance |
| `address_city_id_idx` | address | city_id | FK join performance |
| `city_department_id_idx` | city | department_id | Geography join |
| `establishment_main_activity_id_idx` | establishment | main_activity_id | NAF lookup |
| `vw_naf_proximity_idx` | vw_naf_proximity (matview) | (activity pair) | Core recommendation |
| `vw_siren_idx` | vw_siren (matview) | siren | Active company filter |

---

## 6. Confirmed ZE2020 Aggregation Path

The path `establishment → address → city → insee_code → ZE2020` is structurally sound:

1. `establishment.address_id` → FK to `address.id` (index confirmed)
2. `address.city_id` → FK to `city.id` (index confirmed)
3. `city.insee_code` → **5-digit INSEE commune code** (index confirmed)
4. `commune_to_ze2020_2026.csv` column `CODGEO` = 5-digit INSEE commune code

**The join key is `city.insee_code = CODGEO`.**

Unknowns requiring DB restoration to quantify:
- Percentage of establishments with non-null `address_id`
- Percentage of addresses with non-null `city_id`
- Percentage of cities with non-null `insee_code`
- Coverage of French metropolitan communes vs. overseas territories
- Count of establishments mappable to ZE2020

---

## 7. Trade Data Vintage

Based on table names:

| Source | Vintage | Tables |
|---|---|---|
| French customs (Douanes) | **2018** | `util_import_export_2018_by_nc2020` |
| French customs (Douanes) | **2019** | `util_import_region_2019`, `util_import_2019_nc8_a732`, `util_region_2019_*`, `util_total_exports_by_french_department_2019` |
| World trade (COMTRADE/BACI) | **2019** | `util_mondial_exports_per_hs4_2019`, `util_mondial_exports_per_hs4_and_country_2019`, `util_mondial_imports_per_hs4_and_country_2019` |
| Efficiency/redundancy | **2019** | `util_efficiency_and_redundancy_per_flows_2019` |

**All trade data is frozen at 2018–2019 vintage.** For HERALD training involving years 2020–2025, trade-based features (RCA, export intensity, import dependency) must be updated from annual Douanes/COMTRADE publications.

---

## 8. Methodology — Partner Recommendation Engine

Based on TOC and naming analysis (to be confirmed with SQL inspection after restoration):

### Route 1: Product Space Proximity

```
establishment_A (SIRET, NAF, products declared)
  ↓
product (establishment_id → nomenclature_product_id → HS4)
  ↓
vw_rca_by_it or vw_rca_by_dep (does this IT/dep export this HS4 product?)
  ↓
nomenclature_product_proximity (proximity_score between HS4 pairs)
  +
nomenclature_activity_product_proximity (NAF → HS4 proximity)
  ↓
partner_calc (establishment_A × establishment_B → score)
  ↓
ia_establishment_potential_partners (ranked partner list)
  ↓
func_list_partner(establishment_id) → returns top partners
```

### Route 2: Input-Output Table

```
establishment_A (NAF → NACE mapping)
  ↓
raw_iot_secteur_nace (NACE × NACE → IO coefficient)
  = who produces what establishment_A consumes, and vice versa
  ↓
iot_production_nace + iot_consume_nace
  ↓
partner_calc_iot (establishment_A × establishment_B → IO-based score)
  ↓
ia_potential_by_iot
  ↓
func_list_partner_iot(establishment_id) → returns IO-linked partners
```

### Graph structure

- **Nodes:** establishments (SIRET), NAF activities, HS4 products, territories
- **Edges:**
  - establishment → product (declared exports)
  - product ↔ product (proximity score)
  - activity ↔ product (activity-product proximity)
  - activity ↔ activity (NAF proximity, semantic proximity)
  - establishment ↔ establishment (partner score, IO potential)
  - establishment → territory (via address chain)
- **Weights:** proximity scores, IO coefficients, RCA values, semantic similarity scores

---

## 9. Open Questions (requires DB restoration)

1. Row counts for `establishment`, `company`, `city`, `product`, `recommendation`, `relation`
2. Actual column names and types for `establishment` (especially: active status flag, creation date, workforce count)
3. Coverage: what % of cities have `insee_code`? What % are in mainland France?
4. SQL body of `func_list_partner`, `func_list_partner_iot` → exact scoring formula
5. What are the enum values of `recommendation_type` and `relation_type`?
6. Is `util_histo_establishment` a true time series (year column)? What years?
7. What is `biom`? What is `parity`?
8. What vintage is the IO table (`raw_iot_secteur_nace`)?
9. Does `establishment` have a `creation_date` or `cessation_date` column?
10. Are there any ZE or ZE2020 columns in any table?

---

## 10. Isolation Guarantee

This audit does not touch any HERALD training file, HPC job output, or existing model results. All new files are created under:
- `reports/ATLAS_IAT_*.md`
- `data/interim/atlas_iat/`

No HERALD source files modified.
