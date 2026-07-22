# HERALD 47 -- France ZE2020 A10 source provenance

**Date:** 2026-07-22  
**Status:** `SOURCE_PROVENANCE_CLOSED`  
**Decision:** `DEC-076`

## 1. Question

Can the canonical France ZE2020 sector-composition panel be rebuilt directly
from an official source, without depending on the legacy processed
`side_creations_a10_ze2020_through_2025_v1.csv` intermediate?

## 2. Official source contract

The canonical builder now streams
`data/raw/business_demography/side/DS_SIDE_CREA_ETAB_COM_2025_CSV.zip`.

- member: `DS_SIDE_CREA_ETAB_COM_2025_data.csv`;
- SHA-256: `1c42a050d971932eaf9ad2d25292c9ab586d28d7ee171826586cfb53ace2ba14`;
- dimensions: `GEO_OBJECT=ZE2020`, `LEGAL_FORM=_T`,
  `SIDE_MEASURE=UNIT_LOC_BURE`, `OBS_STATUS=A`, `FREQ=A`;
- sectors: `BE/FZ/GI/JZ/KZ/LZ/MN/OQ/RU`;
- canonical scope: 280 ZE2020, 2012--2025.

The output is accepted only if every ZE-year matches the clean panel and the
nine sector counts sum exactly to canonical `establishment_creations`.

## 3. Sparse official zero

The official long file omits one canonical sector combination:
`ZE 5218 / 2016 / JZ`. The builder completes it as zero, not by statistical
imputation, but by exact partition identity: the eight reported A10 sectors
already sum to the independent official total for that ZE-year. Any completion
that breaks this identity fails closed.

The count and rule are stored in
`fr_ze2020_sector_panel_source_summary.json`.

## 4. Reconstruction audit

Final Meso smoke job `7780962` completed exit `0:0` in 20 seconds with empty stderr.
It generated 35,280 rows. The reconstructed panel and existing canonical panel
have identical schema, keys, labels, values, masks, ranks, ordering, and bytes:

`SHA-256 ff102c482c510cc961f6084a983bd00b567b72938194311b8d9440114268c933`

The reconstructed wide A10 values also match the legacy processed intermediate
exactly. The intermediate is therefore retained only as historical derived
evidence and is no longer an input to the canonical builder.

## 5. Verification

- 18/18 focused sector-builder tests pass in the Meso pandas environment;
- checksum, member, dimensions, zero completion, coverage, duplicates,
  non-negativity, reconciliation, schema, ranking, and legacy exclusions are
  tested;
- the failed first smoke (`7780950`) exposed the sparse cell before any
  canonical output was overwritten; the corrected run wrote only to an
  isolated `hpc_results` directory.

## 6. Decision

The A10 sector-composition provenance gap is closed. The observed panel is a
canonical data input, but it remains contemporaneous and must not enter a
target-year model directly. Model inputs must continue through the existing
lagged sector-feature builder.

This decision validates source provenance only. It does not validate sector
precedence, nonlinear relations, a temporal graph encoder, causality, or
recommendation. Phase 7 already estimated pooled France precedence from ZE2020
observations; it must not be rerun under a new name. The remaining gap is a
separately pre-registered test of context-conditioned relation heterogeneity
that transfers to held-out ZEs (HERALD_48/DEC-077).
