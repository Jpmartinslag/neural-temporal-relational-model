# Phase 4 — Data Status & Open Issues

**Date:** 2026-05-27  
**Purpose:** Cross-country data readiness summary before pipeline build.

---

## Consolidated Status Table

| Component | Belgium | Netherlands | Portugal |
|-----------|---------|-------------|---------|
| Enterprise births | ⚠ 2021+ only (new series) | ⚠ No COROP births → ΔStock proxy | ✓ Municipal, 2008+, CC BY 4.0 |
| Territory | ⚠ Births at arrond. not confirmed | ✓ 40 COROP (functional) | ⚠ 308 vs 23 zones: choose |
| Sector | ✓ NACE-BEL → A10 | ✓ SBI 2008 → NACE → A10 | ✓ CAE Rev.3 → NACE → A10 |
| Time coverage | ⚠ 2008-2020 old series (break) | ✓ 2007+ | ✓ 1990+ |
| Q-tensor source | ✓ RSZ arrond × NACE (2005+) | ⚠ Verify COROP × sector | ⚠ GEP recent yrs: access TBD |
| Geometries | ✓ Statbel CC BY 4.0 | ✓ CBS open data | ✓ INE CAOP |

---

## Open Questions (must resolve before pipeline build)

### Belgium

1. **Births geography**: Does Statbel beSTAT API provide births at arrondissement level?
   - Test: `curl "https://bestat.statbel.fgov.be/bestat/api/views/1a3f63bd-2792-4804-833d-55b02eb9b232/result/CSV"`
   - If national only: major blocker → document, consider workaround from CBR/administrative data

2. **Births history**: Is pre-2021 series (old methodology) downloadable? How severe is the 2018 break?
   - Action: Navigate beSTAT, check "Demography of employers" series for older data

3. **RSZ detailed quarters**: Confirm the Excel download contains arrondissement × NACE cross-tab (not just regional aggregate).

### Netherlands

4. **Q-tensor sector breakdown**: Does CBS 85481NED include sector (SBI) breakdown at COROP level?
   - If not: fall back to 81644NED (size class proxy) or Q1_zero for NL.
   - Action: Check CBS StatLine 85481NED column list.

5. **ΔStock validation**: Compare 83631NED province births vs ΔStock from 81578NED province level to validate proxy quality (should correlate r > 0.9).

### Portugal

6. **Territory choice**: Confirm whether INE zonas de emprego (23) exist as named geographic units with shapefile.
   - If yes: use 23 zones (preferred, comparable scale).
   - If no: use 308 municípios (larger graph, confirmed available).

7. **GEP access**: Verify what years of Quadros de Pessoal are freely downloadable.
   - URL: https://www.gep.mtsss.gov.pt/quadros-de-pessoal
   - If 2022+ needs formal request: document, use through 2021 for q_tensor.

---

## Data Files to Download (prioritized)

### Step 1 (before preflight scripts)

```bash
# Belgium — births
curl "https://bestat.statbel.fgov.be/bestat/api/views/1a3f63bd-2792-4804-833d-55b02eb9b232/result/CSV" \
  > data/external/belgium/raw/statbel_enterprise_births_2021plus.csv

# Netherlands — COROP stock (target proxy)
# Via CBS OData API:
# https://opendata.cbs.nl/ODataApi/odata/81578NED/TypedDataSet
# Select: BedrijfstakkenBranchesSBI2008, RegioS (filter COROP), Perioden → CSV

# Netherlands — births at province (validation)
# https://opendata.cbs.nl/ODataApi/odata/83631NED/TypedDataSet

# Portugal — INE empresa data
# https://dados.gov.pt/en/datasets/numero-de-empresas/
```

### Step 2 (q_tensor sources)

```bash
# Belgium — RSZ detailed quarterly data
# https://www.rsz.be/stats/arbeidsmarktanalyse-gedetailleerde-kwartaalgegevens
# Download ZIP for available quarters → extract arrond × NACE sheet

# Netherlands — CBS 85481NED
# https://opendata.cbs.nl/ODataApi/odata/85481NED/TypedDataSet

# Portugal — GEP Quadros de Pessoal
# https://www.gep.mtsss.gov.pt/quadros-de-pessoal
```

---

## Preflight Decision Matrix

Based on current investigation:

| Country | Launch Decision | Condition |
|---------|----------------|-----------|
| **Portugal** | LIKELY LAUNCH | After confirming GEP access + territory choice |
| **Netherlands** | LAUNCH with caveat | ΔStock proxy documented in preflight point 1 |
| **Belgium** | SUSPEND pending | Births geography + time coverage must be confirmed first |
