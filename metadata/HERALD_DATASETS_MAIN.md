# Primary datasets to maintain — France pipeline

Date: 2026-05-07

This document lists the sources that actually matter for the France pipeline. Raw files can stay
on the local machine; the repository only needs to keep the trace, the scripts, and the derived
panels required for reproducibility.

## General rule

- Heavy raw datasets stay out of git.
- Clean panels, graphs, and canonical targets can be versioned if their size stays reasonable.
- Every source must have a documented update frequency and availability date.
- For a forecast, a `t-1` variable is only allowed if it was published before the forecast date.

## Canonical sources

| Source | Role in the pipeline | Current derived files | Update cadence | Action |
|---|---|---|---|---|
| SIDE establishment creations | main target and AR lags | `data/processed/target_side_establishments_annual_core_through_2025_v1.csv`; `data/processed/dynamic_stgnn_feature_panel_through_2025_v1.csv` | annual | automate the download as soon as INSEE publishes a new release |
| SIDE A10 creations | sectoral target/prior | `data/processed/side_creations_a10_ze2020_through_2025_v1.csv` | annual | update alongside SIDE creations |
| ZE2020 geography graphs | fixed spatial prior and mapping | `graph_adjacency_core_v0.csv`; `graph_edges_ze2020_core_v0.csv`; `graph_nodes_ze2020_core_v0.csv`; `graph_node_index_core_v0.csv` | rare, only on a geography change | keep stable for comparability; rebuild only if the nomenclature changes |
| Home-to-work commuting graph | prior for economic connections | `graph_adjacency_mobility_v0.csv` | slow, tied to the census / INSEE mobility release | document the vintage; rebuild if a new, reliable matrix becomes available |
| FLORES establishments / salaried employment | local productive context | `data/processed/flores_panel_ze2020_annual_v1.csv` | annual, with a delay | check availability before forecasting; mostly use `t_minus_1` |
| URSSAF quarterly employment / payroll | fast conjunctural signal | `data/raw/employment/urssaf/urssaf_emploi_ze_quarterly_raw.csv`; quarterly tensors | quarterly, end of quarter + ~80 days | priority for regular extraction; do not use Q4 if the cutoff does not allow it |
| SIDE establishment / legal-unit stocks | economic-stock context | `data/processed/side_stocks_lagged_ze2020_annual_v1.csv` | annual, but currently only through 2023 | treat as missing after 2023; do not force it as a current signal |
| Walk-forward splits | evaluation protocol | `metadata/dynamic_stgnn_walk_forward_splits_through_2025_v1.csv` | on every year extension | keep and version |

## Raw sources to keep locally only

These sources can stay on the local machine or be downloaded on demand:

- SIDE creations/establishments ZIPs, 2012-2025;
- SIDE A10 ZIP;
- SIDE stocks ZIP;
- FLORES ZIP;
- URSSAF open-data files;
- INSEE territorial files (ZE2020/COG);
- download archives and logs.

They must not be committed if they are heavy or easily re-downloadable.

## Recommended extraction frequency

| Source | Practical frequency | Use |
|---|---|---|
| URSSAF quarterly | monthly or quarterly | fast signals, operational forecasting |
| SIDE creations/A10 | annual, after the INSEE release | target, backtest, next-year forecast |
| FLORES | annual, after the release | `t-1` economic context |
| SIDE stocks | annual, if a new vintage is published | structural context |
| ZE/COG geography | annual, or on a nomenclature change | joins, maps |
| Home-to-work mobility | whenever a new reliable vintage exists | structural graph |

## To expose via API later

For an application, an access layer will be needed that keeps up to date:

- SIDE observations;
- model forecasts;
- derived indicators by zone;
- simplified geometries;
- top-k graph connections;
- source-availability metadata.

The first API must not serve raw INSEE data. It must serve clean, audited tables.
