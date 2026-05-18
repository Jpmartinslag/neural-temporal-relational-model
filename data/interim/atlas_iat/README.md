# data/interim/atlas_iat/

Atlas/IAT intermediate data directory.  
All files here are derived from the Atlas/IAT dump: `/home/jpdark/Downloads/project_recomm/iat.dump`

**Dump date:** 2022-01-20  
**Audit date:** 2026-05-18  
**DB restoration status:** PENDING (PostgreSQL role setup required)

---

## Files

| File | Status | Description |
|---|---|---|
| `table_inventory.csv` | COMPLETE | All tables, views, functions from dump TOC. Category, source, priority. |
| `source_mapping_draft.csv` | COMPLETE (draft) | Open source identification per data block. Confidence level: confirmed / inferred / unknown. |
| `ze2020_feature_plan.csv` | COMPLETE (draft) | 20 candidate features for ZE2020 aggregation. Use classification, leakage risk, aggregation method. |
| `dynamic_feature_plan_by_year.csv` | COMPLETE (draft) | Feature × year matrix (2021–2027). Availability status, update recipe, lag. |
| `atlas_iat_ze2020_static_features_v0.csv` | NOT YET CREATED | Requires DB restoration + ZE2020 join computation. |
| `atlas_iat_ze2020_dynamic_features_v0.csv` | NOT YET CREATED | Requires annual source data + reconstruction. |
| `atlas_iat_source_mapping_v0.csv` | ALIAS of source_mapping_draft.csv | Will be renamed to v0 once validated against live DB. |

---

## ZE2020 Join Path

```
establishment.address_id
  → address.city_id
    → city.insee_code
      → commune_to_ze2020_2026.csv (CODGEO)
        → ZE2020
```

**Key:** `city.insee_code = CODGEO` (5-digit INSEE commune code)  
**Mapping file:** `data/interim/mappings/commune_to_ze2020_2026.csv`

This aggregation is **new** — Atlas/IAT was not built for ZE2020.  
Correct language: "Atlas/IAT-derived features re-aggregated by ZE2020 for HERALD compatibility."

---

## DB Restoration

To restore the dump locally:

```bash
# Step 1: create PostgreSQL role (run as yourself in terminal)
! sudo -u postgres createuser --no-password --createdb jpdark

# Step 2: create target database
createdb iat_restore

# Step 3: install extensions in target DB
psql -d iat_restore -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -d iat_restore -c "CREATE EXTENSION IF NOT EXISTS hstore;"
psql -d iat_restore -c "CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;"

# Step 4: restore (no-owner = avoids user mapping issues)
pg_restore --no-owner --role=jpdark -d iat_restore \
  /home/jpdark/Downloads/project_recomm/iat.dump
```

Expected restore time: 20–60 minutes (819 MB compressed, PostGIS extensions).

---

## Isolation Guarantee

This directory and all files within are:
- Additions only (no modification of existing files)
- Isolated from HERALD training scripts
- Isolated from HPC outputs
- Not pushed to remote (manual push by user)
