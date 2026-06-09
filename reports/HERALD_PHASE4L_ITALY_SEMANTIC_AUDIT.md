# HERALD Phase 4L — Italy Semantic Audit

Date: 2026-06-09
Question: does the Italian target measure the **same event** as Portugal's
`enterprise_birth` (total population, demographic, Eurostat-OECD)?
Verdict: **PASS — semantically equivalent to PT** (with documented limits).

## 1. Concept (official sources)

ISTAT *Demografia d'impresa*, built on the statistical register **ASIA**
(Archivio Statistico delle Imprese Attive), updated annually by integrating
administrative and statistical sources.

| Dimension | Italy (ISTAT/ASIA) | Matches PT? |
|---|---|---|
| Indicator / source | Eurostat `bd_size_r3`, `indic_sb=V11920` (Births of enterprises in t), `sizeclas=TOTAL`; upstream = ISTAT ASIA | Same family as PT (Eurostat BD) |
| Statistical unit | **impresa** (enterprise), Reg. (EEC) 696/93 definition | ✅ enterprise (= PT) |
| Total vs employer | **TOTAL** enterprise population (`sizeclas=TOTAL`), incl. enterprises without employees | ✅ total (= PT) |
| Birth definition | "nate da zero (nate reali) senza il coinvolgimento … di scorpori e/o fusioni" — born from scratch | ✅ from scratch |
| Economic vs administrative | Demographic/economic; ASIA excludes "administrative noise"; **not** Movimprese/Infocamere registrations | ✅ economic (= PT; ≠ BE VAT) |
| Reactivation | Deaths confirmed definitive after **2 years** to exclude reactivations | ✅ Eurostat-OECD 2-yr |
| Mergers / splits / takeovers | Excluded (births "from scratch") | ✅ |
| Continuity | Eurostat-OECD continuity rules | ✅ |
| Standard | "si fa riferimento ai concetti e alle definizioni **Eurostat-OCSE** sulla demografia delle imprese" | ✅ Eurostat-OECD aligned |
| ATECO coverage | ATECO 2007 (NACE Rev.2) business economy | comparable to PT CAE→A10 (sectors not ingested here) |
| Granularity | **NUTS3 (province)** | ✅ NUTS3 (= PT) |
| Years available (this source) | **2008–2020** (`bd_size_r3`) | PT 2008–2024 → common 2008–2020 |
| 2021 methodology change | EBS NACE-scope change applies from ref. 2021; **outside** the 2008–2020 window used here | not in-window |
| Eurostat/OECD correspondence | Total enterprise births, Eurostat-OECD Manual KS-RA-07-010 | ✅ = PT mapping |

## 2. Decision

**Not `BLOCKED_SEMANTIC`.** Italy's target is the same statistical object as
Portugal: total-population demographic enterprise births, enterprise unit,
Eurostat-OECD aligned, at NUTS3. It is **not** an administrative registration
(Movimprese/Infocamere) and **not** employer-only.

## 3. Documented limits

- **Window 2008–2020** via Eurostat `bd_size_r3`; 2021–2024 would require ISTAT
  national tables (SDMX endpoint unstable at audit time) or EBS regional tables.
- **NUTS-version transition:** Sardinia NUTS3 codes change at 2019 (NUTS 2021).
  The 13 Sardinian codes (`ITG25`–`ITG2H`) are **dropped**, not merged or
  interpolated; 102 mainland+Sicily provinces with full 2008–2020 coverage are
  retained.
- **Suppressions:** kept as NaN upstream; the retained 102 provinces have 100%
  target coverage (no masked gaps), so no imputation is involved.
- **Sectors / employment:** `bd_size_r3` provides no NUTS3×A10 sector births or
  employment tensor; those columns are NaN with masks = 0 (honest gap).

## 4. Sources

- Eurostat `bd_size_r3` (Business demography by size class and NUTS 3 region,
  2008–2020), indic_sb V11920 (births) / V11910 (stock), sizeclas TOTAL:
  https://ec.europa.eu/eurostat/databrowser/view/BD_SIZE/default/table ;
  API: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/bd_size_r3
- ISTAT — *Demografia d'impresa*, nota metodologica (ASIA, definizioni
  Eurostat-OCSE): https://www.istat.it/wp-content/uploads/2025/07/Nota-metodologica.pdf ;
  tavole 2018–2023: https://www.istat.it/tavole-di-dati/demografia-dimpresa-anni-2018-2023/
- Eurostat-OECD Manual on Business Demography Statistics (KS-RA-07-010):
  https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-ra-07-010
