# SIDE 2021 and BPE 2023 Integration V0

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Date: 2026-04-11

## Scope

This integration closes two temporal-depth gaps for the annual core panel:

- `SIDE 2021` commune-level establishment and legal-unit stocks.
- `BPE 2023` equipment counts from a validated `BPE23` file.

`BPE 2020` remains open because the local candidates inspected so far do not provide a valid national 2020 file.

## Inputs

- `data/raw/temporal_depth/side/DS_SIDE_STOCKS_ET_COM_2023_CSV_FR.zip`
- `data/raw/temporal_depth/side/DS_SIDE_STOCKS_UL_COM_2023_CSV_FR.zip`
- `data/raw/temporal_depth/bpe/BPE23.zip`

The `SIDE` files are multi-year files covering `2014-2023`; the integration keeps only:

- `TIME_PERIOD = 2021`
- `GEO_OBJECT = COM`
- `ACTIVITY = _T`

The `BPE23` file contains `AN = 2023` and is treated as the reliable `BPE 2023` source.

## Outputs

- `data/interim/tables/side_stocks_commune_2021.csv`
- `data/interim/tables/bpe_commune_2023.csv`
- `reports/side_2021_bpe_2023_integration_quality_v0.json`

The integration also updates:

- `data/processed/zones_master_annual_v0.csv`
- `data/processed/panel_zones_v0.csv`
- `data/processed/zones_master_annual_core_v0.csv`
- `data/processed/panel_zones_core_v0.csv`
- `data/processed/pre_stgnn_dataset_core_v0.csv`
- `data/processed/baseline_annual_dataset_core_v0.csv`
- `data/processed/graph_model_feature_panel_core_v0.csv`

## Quality Summary

- `SIDE ET 2021`: 34,868 commune rows selected.
- `SIDE UL 2021`: 34,868 commune rows selected.
- `BPE 2023`: 2,577,716 mapped equipment rows selected.
- `SIDE ET 2021` coverage: 306 ZE2020 zones.
- `SIDE UL 2021` coverage: 306 ZE2020 zones.
- `BPE 2023` coverage: 306 ZE2020 zones.
- `core_v0` coverage: 280/280 zones for all three new fields.

## Panel Impact

In `core_v0`, the mean observed feature count became:

- `2020`: 2.0
- `2021`: 14.0
- `2022`: 7.0
- `2023`: 5.0
- `2024`: 4.0

This materially strengthens `2021` and `2023`, but the panel is still shallow for a strong annual Graph WaveNet experiment.

## Remaining Gap

`BPE 2020` is still not closed.

Rejected local candidates:

- `bpe20_ensemble_csv.zip`: HTML error page, not a readable ZIP.
- `bpe19_bfc.zip`: `BPE 2019` shapefile for `BFC`, not national `BPE 2020`.
- `bpe-ensemble.csv`: multi-year table containing `2011` and `2012`, not `2020`.

The required target remains a national `BPE 2020 Ensemble` equivalent with commune-level equipment counts.
