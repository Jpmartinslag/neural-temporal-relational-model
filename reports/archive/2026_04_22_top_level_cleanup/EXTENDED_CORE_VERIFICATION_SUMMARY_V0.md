# Extended Core Verification Report v8

> Methodological precedence note: use [METHODOLOGICAL_POSITIONING_V0.md](/home/jpdark/Downloads/project_recomm/dataset/reports/METHODOLOGICAL_POSITIONING_V0.md) as the current canonical framing. If this report conflicts with it, the methodological positioning document prevails.


Data: 2026-04-15

## Executive Summary

The `extended core` is now split into three explicit packages:

- `extended_forecast_core`: forecast-safe annual features only.
- `extended_nowcast_q1_core`: forecast-safe features plus current-year Q1 regime signal.
- `extended_diagnostic_core`: includes later current-year regime signals for audit only.

The current benchmark remains conservative: simple temporal history is still the strongest observed linear signal.

## Data Scope

- Years: `2018-2024`
- Nodes: `280` ZE2020 core zones
- Target: official SIDE establishment creations aggregated to ZE2020
- Mobility graph source: Census RP mobility file for `2021`
- SITADEL surfaces: used only as `T-1` lagged local construction pressure

## Benchmarks

Rolling backtest window: `2021-2024`

All Ridge models use per-fold scaling and mean-imputation fitted only on years before each test year.

| Model | Mean WMAPE | Notes |
| :--- | :---: | :--- |
| `ridge_lag_only` | `7.66%` | Best observed linear baseline so far. |
| `persistence` | `7.68%` | Practically tied with Ridge lag. |
| `ridge_spatial_lag_mobility` | `7.70%` | Mobility graph beats geo slightly, but not the temporal baseline. |
| `ridge_spatial_lag_geo` | `7.74%` | Geographic graph baseline. |
| `ridge_sitadel_lag` | `8.43%` | Lagged construction signal not useful linearly yet. |
| `ridge_forecast` | `9.99%` | Rich forecast-safe linear combination is unstable. |
| `ridge_nowcast_q1` | `11.10%` | Q1 regime signal is not robust in this linear specification. |
| `ridge_stock_lag` | `12.64%` | Stock lag hurts when added directly to target lag. |

## Methodological Status

Resolved:

- `year_profile` is excluded from panel features and tensors.
- `creation_rate` is excluded from tensors because it is target-derived.
- `regime_signal_jan_dec`, `jan_sep`, and `jan_jun` are diagnostic-only.
- Forecast and Q1 nowcast tensors are separated.
- SITADEL is integrated only through lagged features.
- Scaling and imputation in the rolling baseline are fitted inside each fold.

Remaining caution:

- The rolling window is short (`2021-2024`), so results are directional rather than final.
- Mobility improves over geographic adjacency only marginally in a linear model.
- Richer linear models remain unstable; this justifies an exploratory non-linear benchmark, not a claim that STGNN is necessary.

## Next Step

Before any graph-temporal benchmark, commit the current data/baseline consolidation.

If continuing data enrichment first, follow the current priority queue:

- extend Energy to `2008-2017`
- convert REI historical `2018-2022`
- keep SITADEL monthly as experimental until it beats the temporal baseline

If moving to model exploration, benchmark strictly against `ridge_lag_only = 7.66%` and `persistence = 7.68%`.
