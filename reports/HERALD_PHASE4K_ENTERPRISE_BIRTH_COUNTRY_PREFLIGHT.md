# HERALD Phase 4K — `enterprise_birth` Comparable-Country Preflight

Date: 2026-06-09
Scope: metadata-only preflight of ES, DE, IT for a target **semantically equal to
Portugal**: `enterprise_birth`, **total** enterprise population (incl. without
employees), demographic (economic) births — **not** employer-only, **not**
administrative/fiscal registrations.
No panel built, no model trained, no HPC.

## Reference concept (Portugal, the anchor)

INE Demografia das Empresas: enterprise unit, economic (not administrative)
births, Eurostat-OECD Manual aligned (KS-RA-07-010), **total** enterprise
population, NUTS3, 2-year reactivation rule, births "from scratch" (excludes
mergers/splits/takeovers). Eurostat mapping: **total enterprise births**
(`bd_size_r3` / `bd_hgnace2_r3` family — NOT the `bd_e*_r3` employer family).

## Eurostat regional availability (decisive constraint)

The harmonized **NUTS3** business-demography tables currently cover **2008–2017**:

| Eurostat table | Population | Coverage |
|---|---|---|
| `bd_size_r3` | **total** (by size class, NUTS3) | 2008–2017 |
| `bd_hgnace2_r3` | **total** (NACE + NUTS3) | 2008–2017 |
| `bd_esize_r3` | employer (avoid) | 2008–2017 |
| `bd_enace2_r3` | employer (avoid) | 2008–2017 |

EU Regulation 2019/2152 (EBS) mandates regional business demography from
**reference year 2021**, but the consolidated NUTS3 series is not yet contiguous
with the 2008–2017 block — there is a **2018–2020 gap** in the harmonized NUTS3
tables. A continuous 2015–2024 series therefore requires **national sources**,
not the Eurostat NUTS3 tables alone.

Sources: Eurostat Business demography database
(https://ec.europa.eu/eurostat/web/business-demography/database);
`bd_size_r3` (https://ec.europa.eu/eurostat/databrowser/view/BD_SIZE/default/table);
NUTS3 table availability guide
(https://github.com/sumtxt/regionaldata-guide-eu).

## Country table (ES / DE / IT)

| Criterion | **Spain (ES)** | **Germany (DE)** | **Italy (IT)** |
|---|---|---|---|
| National source | INE *Demografía Armonizada de Empresas* (DAE) | Destatis (statistical business register) | ISTAT *Demografia d'impresa* (register **ASIA**) |
| Concept = `enterprise_birth` total | **Yes** (harmonized, total enterprises) | Yes via register; but national public series often administrative (Gewerbeanzeigen) — must use statistical register only | **Yes** (ASIA, demographic, excludes "administrative noise") |
| Statistical unit = enterprise | Yes | Yes | Yes |
| Total population (incl. no-employee) | Yes | Yes (register) | Yes |
| Economic birth, not administrative | Yes | Register: yes / Gewerbeanzeigen: **no (avoid)** | Yes |
| Reactivation (2-yr) | Eurostat-OECD | Eurostat-OECD | Eurostat-OECD |
| Mergers/splits/takeovers excluded | Yes | Yes | Yes |
| **NUTS3 available** | **No at national source** — DAE published at **NUTS2** (19 CCAA); Eurostat NUTS3 only 2008–2017 | Eurostat NUTS3 only 2008–2017; recent Kreise data sparse + **confidentiality suppression** | **Yes** — ISTAT province (NUTS3, 107) |
| Years ~2015–2024 | NUTS2: yes (DAE to 2023); NUTS3: **no recent** | **No** usable recent NUTS3 | **Yes** (ISTAT tables 2015–2020 … 2018–2023) |
| NACE/A10 coverage | CNAE 2009 → A10 | WZ 2008 → A10 | ATECO 2007 → A10 |
| Enterprise stock | Yes (DAE) | Yes | Yes (ASIA) |
| Employment NUTS3 × A10 | Eurostat `nama_10r_3empers` | Eurostat `nama_10r_3empers` | Eurostat `nama_10r_3empers` |
| NUTS geometry | provincias (52) at NUTS3 / 19 CCAA at NUTS2 | Kreise (~400) | province (107) |
| 2021 break | EBS NACE-scope change (common) | EBS + register revisions | EBS NACE-scope change (common) |
| Causal lags reconstructible | Yes (if a continuous series is assembled) | Only if recent NUTS3 obtained | **Yes** |
| Regions × years (usable) | 19 × ~9 (NUTS2) or 52 × partial (NUTS3) | ~400 × (2008–2017 only) | **107 × ~9** |
| Reproducible source | Yes (INE) | Partially | **Yes (ISTAT)** |
| Evidence URL | https://www.ine.es/metodologia/t37/t373020423.pdf | https://www.destatis.de/Europa/EN/Methods/Classifications/OverviewClassification_NUTS.html | https://www.istat.it/tavole-di-dati/demografia-dimpresa-anni-2018-2023/ |

## Eligibility gate (no model performance used)

| Criterion | ES | DE | IT |
|---|:--:|:--:|:--:|
| 1. Same `enterprise_birth` total concept as PT | ✅ | ⚠️ (register only; avoid Gewerbeanzeigen) | ✅ |
| 2. ≥7 usable years (2015–2024) | NUTS2 ✅ / NUTS3 ❌ | ❌ | ✅ |
| 3. ≥20 territories | NUTS2 19 ❌ / NUTS3 52 ✅ but no recent years | NUTS3 ~400 ✅ but no recent years | ✅ (107) |
| 4. Complete territorial target | ✅ (NUTS2) | ❌ (suppression) | ✅ |
| 5. Causal t-1 lags reconstructible | ⚠️ | ❌ | ✅ |
| 6. No untreatable break | ⚠️ (NUTS2↔NUTS3 mismatch) | ❌ | ✅ |
| 7. Documented geometry | ✅ | ✅ | ✅ |
| 8. Reproducible source | ✅ | ⚠️ | ✅ |
| **Verdict** | **ELIGIBLE_WITH_LIMITATIONS** (concept perfect, but national granularity is NUTS2/19 — NUTS3 only to 2017) | **BLOCKED** (no usable recent NUTS3 births; confidentiality; administrative-source risk) | **ELIGIBLE** |

## Part D — Scientific decision

- **At least two new countries semantically equivalent to PT?** Concept-wise
  **yes** (ES and IT both harmonized total enterprise births). Operationally only
  **IT** is clean at NUTS3 for 2015–2024; ES is equivalent in concept but its
  usable granularity is NUTS2.
- **Can we form an `enterprise_birth` subpanel with ≥3 countries?** **Yes, with
  one caveat.** PT (NUTS3, 25) + IT (NUTS3, 107) are two clean NUTS3 legs. ES is a
  valid third **only** at NUTS2 (19) — adding it reintroduces a geometry/MAUP
  heterogeneity. A clean ≥3-country NUTS3 subpanel needs ES NUTS3 births (Eurostat
  2008–2017 + EBS 2021+ stitch) or a fourth country.
- **Which country first?** **Italy.** ISTAT ASIA, demographic total enterprise
  births, NUTS3 (107 province), 2015–2023, reproducible — the only candidate
  passing all eight criteria.
- **Does the subpanel allow a semantically valid LOCO?** **Yes for the concept.**
  A {PT, IT} (and optionally ES) subpanel holds `enterprise_birth` **constant**,
  so LOCO would finally separate the *country effect* from the *concept effect* —
  the exact confound the heterogeneous 4-country panel cannot resolve. **Caveat:**
  geometry still varies (PT 25, IT 107, ES 19), so MAUP remains a separate
  confound; concept is controlled, scale is not.
- **What data is still missing manually?** IT: download ISTAT ASIA births ×
  province × year (and CAE→A10), confirm Eurostat **total** (not employer)
  mapping. ES: decide NUTS2 vs a NUTS3 stitch; obtain provincial births if NUTS3
  is required. DE: drop unless recent Kreise demographic births become available.
  All: confirm 2021 EBS break handling and stock/employment alignment.
- **Path M vs partial Path H?** **Both, scoped.** Keep **Path M** for the full
  FR/NL/BE/PT heterogeneous panel (claims restricted to heterogeneous-task
  transfer). In parallel, a **partial Path H** is now viable as a **confirmatory
  enterprise-birth subpanel {PT, IT (+ES)}** — one concept, enabling the first
  semantically valid LOCO. This is the scoped Path H recommended in the semantic
  audit, now backed by a concrete eligible country (IT).

## Eligible countries

- **IT — ELIGIBLE** (integrate first).
- **ES — ELIGIBLE_WITH_LIMITATIONS** (concept ✅; granularity NUTS2/19, NUTS3 only
  to 2017).
- **DE — BLOCKED** (no usable recent NUTS3 demographic births).

## Verified sources

- Eurostat — Business demography database & regional tables (`bd_size_r3`,
  `bd_hgnace2_r3` total; `bd_esize_r3`, `bd_enace2_r3` employer), NUTS3 2008–2017:
  https://ec.europa.eu/eurostat/web/business-demography/database ;
  https://ec.europa.eu/eurostat/databrowser/view/BD_SIZE/default/table
- Eurostat — Business demography statistics (Statistics Explained), EBS Reg.
  2019/2152 regional from 2021:
  https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Business_demography_statistics
- Eurostat-OECD Manual on Business Demography Statistics (KS-RA-07-010):
  https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-ra-07-010
- Spain — INE *Demografía Armonizada de Empresas*, metodología:
  https://www.ine.es/metodologia/t37/t373020423.pdf ;
  operación: https://www.ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736161927
- Italy — ISTAT *Demografia d'impresa* (ASIA), tavole 2018–2023:
  https://www.istat.it/tavole-di-dati/demografia-dimpresa-anni-2018-2023/
- Germany — Destatis NUTS classification:
  https://www.destatis.de/Europa/EN/Methods/Classifications/OverviewClassification_NUTS.html
- NUTS3 table availability guide (community):
  https://github.com/sumtxt/regionaldata-guide-eu

## Constraints honoured

Geographic proximity was **not** used as a compatibility argument. Employer births
were **not** treated as equal to total births. Fiscal/administrative registrations
(BE VAT, DE Gewerbeanzeigen, IT Movimprese/Infocamere) were **excluded** from the
demographic concept. No training, no model change, no HPC, no massive downloads.
