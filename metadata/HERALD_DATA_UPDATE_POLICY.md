# Data update policy — France pipeline

Date: 2026-05-07

## Principle

The pipeline must operate against an explicit calendar. For every forecast, a forecast date is
declared and only sources published before that date are allowed.

Current example:

```text
forecast date = 2026-05-07
```

The 2026/2027 forecast produced today is therefore conditional on the data available as of that
date.

## Maintenance calendar

| Frequency | Sources | Action |
|---|---|---|
| Monthly | check for new URSSAF / SITADEL releases where integrated | download if available, rebuild fast features |
| Quarterly | quarterly URSSAF | rebuild quarterly tensors and the operational forecast |
| Annual | SIDE creations, SIDE A10, FLORES, SIDE stocks | rebuild the annual panel, splits, backtests, and dashboard |
| On a nomenclature change | ZE2020, COG, geometries | rebuild mappings, graphs, and maps |

## Target extraction pipeline

```text
download raw -> validate checksum/schema -> build interim -> build processed -> run audit -> train -> export dashboard metrics
```

## What should be automated

- downloading INSEE/URSSAF sources once a stable endpoint exists;
- a source version log;
- a check on expected columns;
- a check on available years;
- a check on coverage of the 280 employment zones;
- automatic generation of the availability calendar (see the current relation
  availability-mask summary under `data/processed/france_ze2020/` for the artifact
  that implements this today).

## What stays manual for now

- validating INSEE/URSSAF methodological changes;
- deciding whether to integrate a new exploratory source;
- economic interpretation of new graph connections;
- moving from A10 to A17/A20.

## Outputs to publish in the repository

To version:

- lightweight canonical panels;
- canonical graphs;
- aggregated metrics;
- the availability calendar;
- offline HTML dashboards.

To keep local / out of git:

- raw ZIPs;
- download logs;
- per-seed prediction CSVs;
- large internal NPZ files;
- HPC archives.
