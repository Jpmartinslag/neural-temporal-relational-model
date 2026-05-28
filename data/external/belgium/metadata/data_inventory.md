# Belgium — Data Inventory (Phase 4 HERALD)

**Date:** 2026-05-27  
**Status:** preliminary — pending download verification

---

## 1. Enterprise Births (TARGET variable)

| Item | Detail |
|------|--------|
| Source | Statbel — Demography of enterprises in the market sector |
| URL | https://statbel.fgov.be/en/themes/enterprises/demography-enterprises/demography-enterprises-market-sector |
| Format | beSTAT API (CSV/Excel) |
| Years | **2021–2024** (new series; CC BY 4.0) |
| Pre-2021 | Older series exists but 2018 = **methodology break** (shift to group-of-enterprises concept) |
| Geographic | Belgium-wide + likely NUTS2/province — **arrondissement breakdown not confirmed** |
| Concept | Enterprise (legal entity), not establishment (physical unit) — **differs from France (établissement)** |
| Sectors | NACE-BEL → mappable to A10 |

### Critical gaps

- **Time coverage**: new series from 2021 only. Pre-2021 data has 2018 break → series not directly stackable.
  - Mitigation: download both series, document break year, use 2008-2020 from old series with explicit "methodology break" note in preflight.
  - If break too severe → only 2021-2024 available for training, which may be insufficient (minimum required: 2008+).
- **Geography**: arrondissement-level births not confirmed. Statbel main tables appear national-level only.
  - Mitigation: check if beSTAT API allows geographic disaggregation to arrondissement.
  - If no: **preflight point 2 FAILS** — suspend BE unless workaround found.
- **Concept**: enterprise ≠ establishment. France uses établissement. Document gap explicitly per preflight point 1.

### Action items

```bash
# Verify beSTAT geographic breakdown
curl "https://bestat.statbel.fgov.be/bestat/api/views/1a3f63bd-2792-4804-833d-55b02eb9b232/result/CSV"
# → check if region column present and at what level
```

---

## 2. Employment / Q-Tensor (RSZ/ONSS)

| Item | Detail |
|------|--------|
| Source | RSZ (Rijksdienst voor Sociale Zekerheid) — Statwork |
| URL | https://www.rsz.be/stats/verdeling-van-de-arbeidsplaatsen-naar-plaats-van-tewerkstelling |
| Format | Excel download (Statwork interactive + raw data ZIP) |
| Years | Quarterly 2005–2025 (detailed quarterly data back to 2005) |
| Geographic | **43 arrondissements (districts) confirmed** — NIS-code from Statbel |
| Concept | Salaried employees subject to social security (DmfA declarations) |
| Sectors | NACE-BEL (2025 NACE revision applied; retropolated to 2024) |
| Lag | Quarterly → aggregate to annual lag1 |

### Status: CONFIRMED USABLE

RSZ explicitly provides "decentralized statistics" = employees by place of employment at arrondissement × NACE level.

### Action items

```bash
# Download detailed raw data (ZIP)
# URL: https://www.rsz.be/stats/arbeidsmarktanalyse-gedetailleerde-kwartaalgegevens
# Select: arrondissement × NACE × year, download Excel/ZIP
# Verify 43 arrondissements present in data
```

---

## 3. Wage Mass (mass salariale)

| Item | Detail |
|------|--------|
| Source | RSZ — same DmfA declarations |
| URL | Same as employment above (Statwork) |
| Availability | Wage cost data available alongside employment in same downloads |
| Geographic | Arrondissement level (same as employment) |

### Status: LIKELY AVAILABLE (verify in same download as employment)

---

## 4. Geographic Units & Adjacency

| Item | Detail |
|------|--------|
| Target unit | 43 Belgian arrondissements |
| Geometries | Statbel open data — statistical sectors 2022 (can aggregate to arrondissement) |
| URL | https://statbel.fgov.be/en/open-data/statistical-sectors-2022 |
| Format | GeoJSON / Shapefile (CC BY 4.0) |
| Adjacency | Queen contiguity via geopandas.sjoin |

---

## 5. Preflight Risk Assessment

| Point | Status | Notes |
|-------|--------|-------|
| 1. TARGET | ⚠ Document | Enterprise ≠ establishment. Explicit note required. |
| 2. TERRITORY | ⚠ Verify | 43 arrondissements OK conceptually. Births at arrond. level not confirmed. |
| 3. SECTOR | ✓ | NACE-BEL → NACE Rev.2 → A10 mapping feasible. |
| 4. COVERAGE | ⚠ Risk | 2021+ births only in new series. 2008 coverage uncertain. |
| 5. Q_TENSOR | ✓ | RSZ arrondissement × NACE confirmed, 2005+. |
| 6. TIGHTNESS | ✓ | Effectifs Q4(T-1) → lag1 annual = OK temporally. |

**Decision risk:** Point 4 (time coverage) is the critical blocker. Verify pre-2021 births availability before committing.
