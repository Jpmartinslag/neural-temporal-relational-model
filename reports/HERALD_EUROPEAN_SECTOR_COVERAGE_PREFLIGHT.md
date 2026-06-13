# HERALD European Sector Coverage Preflight

**Decision:** DEC-038
**Date:** 2026-06-13
**Status:** COMPLETE — eligibility classification only; no model training, no downloads

---

## Objective

Determine which European countries have data compatible with extending the HERALD Observatory
before the neural graph layer. Compatibility requires: territory × year × A10 sector enterprise
birth series; ≥6 consecutive years; NUTS3 or documented functional territorial unit; ≥8 A10
comparable sectors; n_samples ≥ 60; official geometry; concept comparability with FR/NL/PT.

**Geographic priority corridor:** PT → ES → FR → BE → NL

---

## Critical Findings

- Eurostat BD_HGNACE_R provides only 2021-2023 (3 years) for all countries except Finland.
- K_L combined in BD_HGNACE_R: KZ (financial) and LZ (real estate) cannot be separated for any country.
- OQ partial: BD_HGNACE_R P_Q excludes O (public administration); affects OQ comparability.
- Finland (FI): only European country with NUTS3 sector births ≥6 years from Eurostat. 19 stable NUTS3, 2013-2021. Status: ELIGIBLE_WITH_MAPPING (K_L documented).
- Belgium definitively blocked: vat_first_registration concept incompatible with enterprise_birth baseline used in FR/NL/PT.
- Spain, Italy, Germany, Sweden, Poland, Romania: insufficient years from Eurostat BD_HGNACE_R but national sources with 6+ year sector NUTS3 series exist (ELIGIBLE_WITH_DOWNLOAD).

---

## Coverage Matrix

| Country | Name | Territories | Years | Consec. | Sectors | Status |
|---------|------|-------------|-------|---------|---------|--------|
| BE |  | 42 | 2007–2024 | 18 | 0 | BLOCKED_SEMANTICS |
| AT | Austria | 35 | 2007–2022 | 16 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| CZ | Czech Republic | 14 | 2005–2023 | 19 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| DE | Germany | 401 | 2008–2022 | 15 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| DK | Denmark | 12 | 2007–2023 | 17 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| ES | Spain | 50 | 2007–2023 | 17 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| IT | Italy | 107 | 2010–2022 | 13 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| PL | Poland | 380 | 2003–2023 | 21 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| RO | Romania | 42 | 2005–2023 | 19 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| SE | Sweden | 21 | 2007–2023 | 17 | 8 | ELIGIBLE_WITH_DOWNLOAD |
| FI | Eurostat_BD_HGNACE_R | 19 | 2013–2021 | 9 | 8 | ELIGIBLE_WITH_MAPPING |
| FR | Eurostat_BD_HGNACE_R | 280 | 2013–2022 | 10 | 9 | IN_OBSERVATORY |
| NL | Eurostat_BD_HGNACE_R | 40 | 2007–2022 | 16 | 9 | IN_OBSERVATORY |
| PT | Eurostat_BD_HGNACE_R | 25 | 2008–2022 | 15 | 8 | IN_OBSERVATORY |
| BG | Eurostat_BD_HGNACE_R | 28 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| CY | Eurostat_BD_HGNACE_R | 1 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| EE | Eurostat_BD_HGNACE_R | 5 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| EL | Eurostat_BD_HGNACE_R | 52 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| HR | Eurostat_BD_HGNACE_R | 21 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| HU | Eurostat_BD_HGNACE_R | 20 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| IE | Eurostat_BD_HGNACE_R | 9 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| LT | Eurostat_BD_HGNACE_R | 10 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| LU | Eurostat_BD_HGNACE_R | 1 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| LV | Eurostat_BD_HGNACE_R | 9 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| MT | Eurostat_BD_HGNACE_R | 2 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| SI | Eurostat_BD_HGNACE_R | 12 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |
| SK | Eurostat_BD_HGNACE_R | 9 | 2021–2023 | 3 | 8 | PARTIAL_DESCRIPTIVE_ONLY |

---

## Status Distribution

BLOCKED_SEMANTICS: 1; ELIGIBLE_WITH_DOWNLOAD: 9; ELIGIBLE_WITH_MAPPING: 1; IN_OBSERVATORY: 3; PARTIAL_DESCRIPTIVE_ONLY: 13

---

## Panel Proposals

### CORE_CONTIGUOUS (geographically connected eligible)
**Countries:** AT, ES, FR, IT, NL, PT
BE blocks the direct PT→ES→FR→BE→NL corridor (VAT concept). Sub-corridors: PT-ES-FR-NL via France; FR-IT-AT contiguous.

### EU_EXTENDED (all technically eligible)
**Countries:** AT, CZ, DE, DK, ES, FI, FR, IT, NL, PL, PT, RO, SE
Includes FI (Nordic, ELIGIBLE_WITH_MAPPING) and all ELIGIBLE_WITH_DOWNLOAD countries. DE requires semantic concept verification before integration.

### DESCRIPTIVE_ONLY (total births only, no sector breakdown)
**Countries:** BG, CY, EE, EL, HR, HU, IE, LT, LU, LV, MT, SI, SK

### BLOCKED
**Countries:** BE

---

## Eurostat BD_HGNACE_R Limitations

The Eurostat BD_HGNACE_R dataset (ENT_BRTH_NR at NUTS3) covers 26 EU countries but with
critical temporal and semantic constraints:

1. **Temporal**: Only Finland (FI) has data before 2021. All other countries: 2021-2023 only
   (3 years — insufficient for Phase 7 which requires ≥6 consecutive years).

2. **K_L combined**: Financial services (K) and real estate (L) are merged as K_L in all
   countries. The Observatory uses separate KZ and LZ sectors. Phase 7 relations involving
   KZ or LZ individually cannot be tested from Eurostat BD_HGNACE_R.

3. **OQ partial**: BD_HGNACE_R provides P_Q but not O (public administration NACE O).
   The Observatory OQ sector (O+P+Q) is not fully reproduced.

4. **Effective sectors from BD_HGNACE_R**: BE, FZ, GI (G+H+I), JZ, KL_combined, MN,
   OQ_partial, RU_approx = 8 sectors. Comparable to Observatory A10 with documented caveats.

---

## Finland (FI) — ELIGIBLE_WITH_MAPPING

Finland is the only country outside the current Observatory with ≥6 years of NUTS3-level
sector enterprise births in Eurostat BD_HGNACE_R.

- **Territories**: 19 stable NUTS3 regions (100% complete 2013-2021)
- **Years**: 2013-2021 (9 consecutive years)
- **Sectors**: 10 NACE codes → 8 effective A10 sectors (K_L combined, OQ partial)
- **n_samples**: 19 × 9 = 171
- **Concept**: enterprise_birth (Eurostat BD standard) ✓
- **Geometry**: available in nuts3_2021_eurostat.geojson ✓

**Mapping required before integration:**
- Document KL_combined as single sector (KZ+LZ aggregate); suppress KZ/LZ precedence tests
- Document OQ_partial (P_Q): note undercount; O sector excluded
- Decide whether 8 sectors meets "≥8 A10 comparable" criterion (borderline)

**Limitation**: FI is geographically outside the PT-ES-FR-BE-NL corridor (Nordic).

---

## Belgium (BE) — BLOCKED_SEMANTICS

Belgium is definitively blocked:

1. **Primary**: `flag_target_concept = vat_first_registration`. TVA primo-assujetissements
   measures VAT threshold crossings, not enterprise births. Incompatible with FR/NL/PT baseline.

2. **Secondary**: `mask_sector_a10 = 0` in all local sources. Even if concept were acceptable,
   sector-level birth data is not available. ONSS provides employment jobs per sector, not births.

No reclassification possible without a fundamentally different national data source.

---

## ELIGIBLE_WITH_DOWNLOAD Countries

The following countries could meet Phase 7 criteria if national sector birth data is downloaded
and verified. All require ≥6 consecutive years from national statistical agencies (Eurostat
BD_HGNACE_R provides only 2021-2023 for these countries).

| Country | National Source | Expected Territories | Expected Years | Semantic Risk |
|---------|----------------|---------------------|----------------|---------------|
| ES | INE DIRCE | 50 (provinces) | 2007-2023 | None |
| IT | ISTAT ASIA | 107 (province) | 2010-2022 | None |
| DE | Destatis Unternehmensregister | 401 (Kreise) | 2008-2022 | Concept verification required |
| SE | Statistics Sweden SCB | 21 (län) | 2007-2023 | None |
| PL | GUS BDL | 380 (powiats) | 2003-2023 | None |
| RO | INS TEMPO | 42 (județe) | 2005-2023 | None |
| CZ | Czech Statistical Office | 14 (kraje) | 2005-2023 | None (borderline n=14) |
| DK | Statistics Denmark DST | 12 (landsdele) | 2007-2023 | None (borderline n=12) |
| AT | Statistics Austria | 35 (NUTS3) | 2007-2022 | None |

**Notes:**
- DE: Gewerbemeldungen concept may differ from Eurostat enterprise_birth; cross-check against
  BD_HGNACE_R 2021-2023 values required before integration.
- CZ (n=14): n_samples = 14 × 6 = 84 ≥ 60, but marginal. Acceptable if all years complete.
- DK (n=12): n_samples = 12 × 6 = 72 ≥ 60, marginal. Dependent on complete coverage.

---

## Phase 7 Compatibility Summary

Phase 7 requires: source(t-1), target(t), target(t-1) observable; LOTO cross-validation;
two-way demean (territory + year FE). The minimum viable configuration is:

```
n_territories × consecutive_years ≥ 60
consecutive_years ≥ 6
n_a10_comparable_sectors ≥ 8
concept = enterprise_birth (or documented equivalent)
```

| Criterion | FR | NL | PT | FI | ES* | IT* | DE* | Others* |
|-----------|----|----|----|----|-----|-----|-----|---------|
| Consecutive years ≥6 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| n_territories ≥10 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | varies |
| n_samples ≥60 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| Sectors ≥8 A10 | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |
| Enterprise birth | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ?* | ✓* |
| Geometry | ✓ | ✓ | ✓ | ✓ | ✓* | ✓* | ✓* | ✓* |

\* = expected but requires download and verification

---

## Geometry Compatibility

Official NUTS3 2021 geometry is available in `data/external/nuts3_2021_eurostat.geojson`
for all EU member states. This file covers: AT, BE, BG, CY, CZ, DE, DK, EE, EL, ES, FI,
FR, HR, HU, IE, IT, LT, LU, LV, MT, NL, PL, PT, RO, SE, SI, SK (plus non-EU: CH, IS, NO, etc.).

All countries evaluated in this preflight have geometry available. No additional download needed
for geometry.

---

## Decision Log Entry

**DEC-038 summary**: European sector coverage preflight complete. No country outside current
Observatory can be integrated immediately without either: (a) a documented NACE-to-A10 mapping
decision (FI), or (b) downloading national sector birth data (ES, IT, DE, SE, PL, RO, CZ, DK, AT).
Belgium is definitively blocked by semantic concept incompatibility. Finland is the only country
eligible from existing Eurostat data (ELIGIBLE_WITH_MAPPING). All ELIGIBLE_WITH_DOWNLOAD countries
require explicit download and integration tasks before Phase 7 extension.

**CORE_CONTIGUOUS corridor note**: The direct PT→ES→FR→BE→NL corridor is broken by Belgium.
The viable sub-corridor for geographic contiguity is PT–ES–FR–NL (via France) plus contiguous
IT and AT if national sources are downloaded.

---

*Generated by `src/data/european_panel/audit_european_sector_coverage.py`*
