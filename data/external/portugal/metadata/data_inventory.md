# Portugal — data inventory (Phase 4)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready (tensor framing ⚠️ see below)

---

## Panels produced

| File | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/portugal_births_panel_nuts3.csv` | 375 | 25 | 2008–2022 | Births (INE 0009702), reaggregated to NUTS3 |
| `processed/portugal_stock_panel_nuts3.csv` | 375 | 25 | 2008–2022 | Stock (INE 0009819), direct at NUTS3 |
| `processed/portugal_qtensor_births_cae_nuts3.csv` | 3750 | 25 | 2008–2022 | Sector births × CAE→A10 × NUTS3 (**⚠️ NOT an employment tensor**) |

Zone IDs: `PT_111`, `PT_112`, ..., `PT_300` (25 NUTS3 zones, mainland Portugal + islands).

---

## Sources

| Component | Source | INE indicator | License |
|-----------|--------|---------------|---------|
| Births | INE — enterprise demography | 0009702 (× legal form × municipality) | CC BY 4.0 |
| Births by sector | INE — enterprise demography | 0009703 (× CAE section × municipality) | CC BY 4.0 |
| Stock | INE — SCIE | 0009819 (× NUTS3 × size class, "Total") | CC BY 4.0 |

API: `https://www.ine.pt/ine/json_indicador/pindica.jsp?op=2&varcd={indicator}&Dim1=S7A{year}&lang=PT`

---

## ⚠️ Tensor framing — critical

`portugal_qtensor_births_cae_nuts3.csv` is a **`sector_births_tensor`**, NOT an
employment tensor.

| | France's employment tensor | Portugal's tensor |
|--|-----------|----------------|
| Concept | Salaried-employment stock (URSSAF headcount) | Enterprise births by CAE sector |
| Signal | Labor-supply stock | Entrepreneurial-activity flow |
| Equivalence | — | ⚠️ Proxy only |

**Rules:**
- Never call it an employment tensor, a labor tensor, or `qtensor_jobs` for Portugal.
- Use the label `sector_births_tensor` or `sector_births_lag1` in every HPC config.
- Treat it as a **separate variant** vs. NL/BE (which have real employment data).
- `KZ = 0` everywhere: expected (the financial sector does not appear in INE
  enterprise-birth data).

### Employment-equivalent tensor for Portugal

Requires GEP **`Quadros de Pessoal`** (staff on payroll × CAE × municipality, source
MTSSS).
- Historical series are available via GEP, but access for recent years may require a
  formal request.
- **Not ingested yet** — pending for Phase 4B if a direct comparison requires it.

---

## Methodological notes

### Reaggregating municipalities → NUTS3
- INE municipality codes: 7 chars (e.g. `1111601`). NUTS3 = `geocod[:3]` (e.g. `111`
  = Alto Minho).
- 308 municipalities → 25 NUTS3 (summed reaggregation).
- Mapping tested: zero municipalities lost, zero NUTS3 missing.

### Effective modelling window
- Births + stock + tensor: 2008–2022
- **First evaluation year: 2009** (lag-1 on 2008 is available)

### Ingestion
Script: `src/data/ingest_portugal_panel_nuts3.py`
- Reuses raw `0009702_*.json` and `0009703_*.json` files already present in `raw/ine/`
- Downloads `0009819_*.json` directly at the NUTS3 level
