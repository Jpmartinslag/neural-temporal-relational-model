# Phase 4 — data status (updated 2026-05-28)

**Purpose:** per-country data-readiness summary before the Phase 4A HPC pipeline.
**Status:** All main panels validated by the preflight check. Ready for HPC preparation.

---

## Consolidated status table

| Component | Belgium | Netherlands | Portugal |
|------------|---------|-------------|----------|
| Enterprise births | ✅ Arrondissements, first VAT registrations (`primo-assujettissements TVA`), 2007–2020 | ✅ COROP local-unit openings (`oprichtingen vestigingen`, CBS 83631NED), 2015–2025 | ✅ NUTS3 enterprise births (INE 0009702), 2008–2022 |
| Territory | ✅ 42 arrondissements | ✅ 40 COROP (CR01–CR40; CR98/CR99 excluded) | ✅ 25 NUTS3 |
| Sector tensor | ✅ ONSS jobs × NACE-A10, 2008–2020 | ✅ CBS jobs × SBI-A10, 2010–2024 | ⚠️ `sector_births` × CAE-A10 (NOT employment) |
| Stock | ✅ Statbel TVA, 2007–2020 | ✅ CBS 81578NED, 2015–2025 | ✅ INE 0009819, 2008–2022 |
| Geometries | ✅ Statbel CC BY 4.0 | ✅ CBS open data | ✅ INE CAOP |

---

## Modelling windows

| Country | Births | Stock | Tensor | First evaluation year |
|------|--------|-------|--------|-------------------|
| **NL** | 2015–2025 | 2015–2025 | 2010–2024 (employment) | 2016 |
| **BE** | 2007–2020 | 2007–2020 | 2008–2020 (employment) | 2009 |
| **PT** | 2008–2022 | 2008–2022 | 2008–2022 (`sector_births`) | 2009 |

---

## Preflight status (2026-05-28)

```
NL: PASS ✅  |  BE: PASS ✅  |  PT: PASS ✅
Run: python3 src/data/phase4_preflight.py
```

---

## Critical methodological notes

### Netherlands
- **Births**: CBS 83631NED `oprichtingen vestigingen` — **identical to the French SIRENE
  concept** ✅
- **Stock**: CBS 81578NED, clipped to 2015–2025. Years 2007–2014 are NaN (CBS does not
  publish COROP totals before 2015).
- **Q-tensor**: CBS 83582NED, 2010–2024. Year 2025 is **not available and not proxied**
  in the main pipeline. For lag-1 models, the 2025 target uses the 2024 q-tensor — no
  proxy is needed.
- **Suppressed NaN in the q-tensor**: 48 cells (0.8%) suppressed by CBS (statistical
  disclosure control). Policy: `jobs_suppressed=1`, filled with 0, documented in the
  `jobs_suppressed` flag column.
- ~~NL uses only a ΔStock proxy~~ — **obsolete**. NL has real COROP births for 2015–2025.

### Belgium
- **Main window**: 2008–2020 (the q-tensor starts in 2008 — 2007 NACE Rev.1 is not
  compatible with A10).
- **2006 stock removed**: Statbel has data from 2006, but it is excluded from the main
  window.
- **2007 q-tensor absent**: correct by design (NACE Rev.1). Do NOT carry 2008 forward
  to 2007 in the main pipeline. Only use that as a documented sensitivity check.
- **Births concept**: first VAT registration (`primo-assujettissements TVA`) — a legal
  enterprise, not a physical establishment. This difference is documented.
- **2018 methodological break**: must be flagged in modelling.

### Portugal
- **Tensor framing**: `portugal_qtensor_births_cae_nuts3.csv` is a **`sector_births_tensor`**,
  NOT the France-style employment tensor.
  - France's employment tensor = URSSAF headcount stock × sector × employment zone.
  - Portugal's tensor = enterprise births × CAE→A10 × NUTS3.
  - **Never call it an employment tensor or a labor tensor, in any context.**
  - Use the label `sector_births_tensor` or `sector_births_lag1` in every config.
- **KZ = 0**: expected (the financial sector does not appear in INE enterprise-birth
  data).
- **Employment-equivalent tensor**: requires GEP `Quadros de Pessoal` — **not ingested
  yet**.

---

## Resolved questions

| # | Original question | Status |
|---|-----------------|--------|
| NL-4 | Confirm whether CBS has a sector × COROP breakdown | ✅ Resolved — CBS 83582NED confirmed |
| NL-5 | Validate the ΔStock proxy | ✅ Obsolete — real births are now available |
| BE-1 | Confirm births by arrondissement | ✅ Resolved — first-VAT-registration series confirmed |
| BE-2 | Availability of a pre-2021 series | ✅ Resolved — 2007–2020 VAT series available |
| BE-3 | ONSS cross-tab, arrondissement × NACE | ✅ Resolved — ONSS local-unit data confirmed |
| PT-6 | Territory choice, 308 vs. 23 units | ✅ Decided — 25 NUTS3 (aggregated from municipalities) |
| PT-7 | Access to GEP `Quadros de Pessoal` | ⚠️ Pending — needed for the PT employment-equivalent tensor |

---

## Remaining blockers before HPC

| Country | Blocker | Impact |
|------|-----------|---------|
| PT | GEP `Quadros de Pessoal` not ingested | PT only has `sector_births_tensor`, not an employment-equivalent tensor. Models using the employment signal are not comparable across FR/NL/BE/PT. |
| BE | 2018 VAT methodological break | Must be flagged in results — does not block modelling but affects interpretation. |

**No blocker prevents launching Phase 4A with births + stock + `sector_births_tensor` (PT)
or `qtensor_jobs` (NL/BE).**
