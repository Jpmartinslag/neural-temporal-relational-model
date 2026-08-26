# Belgium — data inventory (Phase 4)

**Date:** 2026-05-28
**Status:** ✅ ingested — panels validated, HPC-ready

---

## Panels produced

| File | Rows | Zones | Years | Description |
|---------|------|-------|-------|-------------|
| `processed/belgium_births_panel.csv` | 588 | 42 | 2007–2020 | Births (first VAT registration) × arrondissement × year |
| `processed/belgium_stock_panel.csv` | 588 | 42 | 2007–2020 | Stock (active VAT-registered enterprises) × arrondissement × year |
| `processed/belgium_qtensor_jobs_panel.csv` | 5460 | 42 | 2008–2020 | ONSS employee jobs × A10 × arrondissement × year |

Zone IDs: `BE_<arrondissement>` (e.g. `BE_bruxelles`, `BE_anvers`, `BE_tournai_mouscron`).

---

## Sources

| Component | Source | Indicator | License |
|-----------|--------|-----------|---------|
| Births | Statbel — beSTAT API | First VAT registration by arrondissement | CC BY 4.0 |
| Stock | Statbel — beSTAT API | Active VAT-registered enterprises by arrondissement | CC BY 4.0 |
| Q-tensor | ONSS — local-unit archives | Jobs by place of work × NACE-BEL × arrondissement (Q4) | Open |

---

## Critical methodological notes

### Births concept
- **First VAT registration** = the first VAT registration event (a legal enterprise).
- This differs from the French SIRENE concept, which is a physical establishment
  (local unit).
- This must be documented explicitly in the paper.

### Q-tensor window
- 2007 NACE Rev.1 (40 columns) is not compatible with NACE Rev.2 (42 columns,
  A10-mappable).
- The Q-tensor starts in **2008**; 2007 is absent by design.
- Do not interpolate 2007 in the main pipeline.

### Geography
- **42 arrondissements** (not 43): Tournai and Mouscron are merged into
  `BE_tournai_mouscron` in the 2019+ ONSS files; they are separate in 2008–2018 and
  merged during ingestion.
- La Louvière (a pre-2002 arrondissement) appears in ONSS data → mapped to
  `BE_soignies`.

### 2018 methodological break
- Statbel revised the VAT series in 2018 (enterprise-group concept).
- Must be flagged in results; does not block Phase 4A.

### Effective modelling window
- Births + stock: 2007–2020 (2007 kept for the lag)
- Q-tensor: 2008–2020
- **First evaluation year: 2009** (lag-1 on 2008 births is available)

---

## Ingestion

Script: `src/data/ingest_belgium_panel.py`

- Automatically downloads ONSS archives via the `data-spreadsheet` HTML attributes
- Local cache under `raw/statbel/` and `raw/onss/`
- Preflight: `python3 src/data/phase4_preflight.py`
