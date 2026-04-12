# BPE Evolution 2019-2024 Integration v0

## Decision

Use the official INSEE BPE evolution file as the comparable temporal BPE layer for now.
Do not treat it as a raw BPE 2020 replacement.

## Source

- Source ZIP: `data/raw/temporal_depth/bpe/ds_bpe_evolution_com_2019_2024_geo_2025.zip`
- Data member: `ds_bpe_evolution_com_2019_2024_geo_2025.csv`
- Official semantics: commune/arrondissement presence of equipment types, `OBS_VALUE=1`.
- Geography: 1 January 2025.
- Years currently present locally: `2019`, `2024`.

## Outputs

- Commune interim: `data/interim/tables/bpe_evolution_commune_2019_2024_geo2025.csv`
- ZE2020 core panel: `data/processed/bpe_evolution_ze2020_core_v0.csv`
- Quality JSON: `reports/bpe_evolution_2019_2024_quality_v0.json`

## Method

- `bpe_evolution_presence_type_count`: number of distinct equipment types present in a commune-year.
- `bpe_evolution_commune_type_presence_total`: sum of commune-type presences inside a ZE2020-year.
- This is not a physical equipment count and should not be compared directly with raw BPE facility counts.

## Forward Compatibility

INSEE indicated a planned July 2026 release with count and presence tables for 2015-2025.
This pipeline keeps the BPE evolution layer separate so the future 2015-2025 table can replace or extend the current 2019/2024 layer without changing the model interface.

## Quality Snapshot

- Total source rows: `1235060`
- Retained core rows: `1210550`
- Unmatched GEO count: `0`
