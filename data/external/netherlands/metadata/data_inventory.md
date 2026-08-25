# Netherlands — data inventory (Phase 4)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready

---

## Panels produced

| File | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/netherlands_births_panel.csv` | 440 | 40 | 2015–2025 | Births (CBS 83631NED `oprichtingen`) × COROP × year |
| `processed/netherlands_stock_panel.csv` | 440 | 40 | 2015–2025 | Stock (CBS 81578NED `vestigingen`) × COROP × year |
| `processed/netherlands_qtensor_jobs_panel.csv` | 6000 | 40 | 2010–2024 | CBS 83582NED employee jobs × SBI-A10 × COROP × year |

Zone IDs: `CR01`–`CR40` (COROP zones). CR98/CR99 (aggregates) excluded.

---

## Sources

| Component | Source | CBS table | License |
|-----------|--------|-----------|---------|
| Births | CBS StatLine | 83631NED — `oprichtingen vestigingen` × SBI × region | CBS open data |
| Stock | CBS StatLine | 81578NED — `vestigingen` × SBI × region | CBS open data |
| Q-tensor | CBS StatLine | 83582NED — `banen werknemers` × SBI-A10 × COROP | CBS open data |

API: `https://opendata.cbs.nl/ODataFeed/odata/{table}/TypedDataSet?$filter=startswith(RegioS,'CR')`

---

## Critical methodological notes

### Windows
- Births and stock: CBS has published COROP totals (T001081) only since **2015**.
  Before 2015: NaN by design (no proxy).
- Q-tensor: available since **2010** (SBI-A10 aggregates at COROP level).
- **Effective modelling window: 2016–2024** (intersection of births/stock/q-tensor
  with the lag-1 requirement).

### Suppressed NaN in the Q-tensor
- **48 cells (0.8%)** suppressed by CBS (statistical disclosure control).
- Policy: `jobs_suppressed=1`, value filled with 0. The `jobs_suppressed` flag column
  is present in the file.
- These cells concentrate on sectors that are rare in small COROP zones.

### Births concept
- CBS 83631NED = **`oprichtingen vestigingen`** (new local units = establishments).
- Identical concept to the French SIRENE definition (physical establishment) ✅.

### Ingestion
Script: `src/data/ingest_netherlands_panel.py`
