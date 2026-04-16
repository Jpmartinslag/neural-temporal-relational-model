# Project Consistency Audit v0

Data: 2026-04-16

## Objective

Close the current data/baseline phase before adding new model complexity.

This audit separates:

- canonical artifacts: safe to use as current project reference
- candidate artifacts: useful, but not accepted into the canonical tensor yet
- diagnostic artifacts: valid only for audit, explanation, or sensitivity analysis
- deprecated/proxy artifacts: retained for traceability, not current ground truth

## Current Canonical Target

Canonical target:

- `data/processed/target_side_establishments_annual_core_v0.csv`
- official SIDE establishment creations aggregated to `ZE2020`

Proxy target:

- old establishment-creation proxy remains audit-only
- it must not be described as final ground truth

## Current Canonical Baseline

Primary benchmark:

- `ridge_lag_only`: mean WMAPE `7.66%`
- `persistence`: mean WMAPE `7.68%`

Interpretation:

- temporal history is still the strongest stable linear signal
- graph and local candidate features are informative, but not yet stronger than the temporal baseline

## Current Tensor Status

Canonical experimental tensors:

- `data/processed/stgnn_tensor_package_extended_forecast_core_v1.npz`
- `data/processed/stgnn_tensor_package_extended_nowcast_q1_core_v1.npz`
- `data/processed/stgnn_tensor_package_extended_diagnostic_core_v1.npz`

Separation rule:

- `extended_forecast_core`: pure forecast-safe annual features
- `extended_nowcast_q1_core`: forecast-safe plus current-year Q1 regime signal
- `extended_diagnostic_core`: includes later current-year signals for audit only

Shape verification after correction:

| Tensor | X | Y | Geo A | Mobility A |
| :--- | :---: | :---: | :---: | :---: |
| `extended_forecast_core` | `7 x 280 x 28` | `7 x 280` | `280 x 280` | `280 x 280` |
| `extended_nowcast_q1_core` | `7 x 280 x 29` | `7 x 280` | `280 x 280` | `280 x 280` |
| `extended_diagnostic_core` | `7 x 280 x 32` | `7 x 280` | `280 x 280` | `280 x 280` |

Correction made:

- `adjacency_mobility` was previously loaded with an extra CSV index column, producing `280 x 281`.
- `src/data/build_stgnn_tensor_package_extended_v1.py` now loads mobility adjacency with `source_idx` as index and raises an error if either adjacency is not `280 x 280`.

## Candidate Local Sources

Candidate families:

- SITADEL annual and monthly non-residential construction
- REI CFE fiscal proxies
- SDES non-residential energy consumption

Decision:

- none enters the canonical forecast tensor yet
- current negative results apply only to processed forms and linear tests
- monthly SITADEL is promising but still below the temporal baseline

Best local candidate so far:

- `ridge_sitadel_monthly_q1_nowcast_log`: mean WMAPE `7.89%`
- `ridge_sitadel_monthly_lag_log`: mean WMAPE `7.93%`

These are useful but not enough to replace the baseline.

## Methodological Checks

Passed:

- official SIDE target is separated from proxy audit target
- forecast, nowcast, and diagnostic tensors are separated
- `creation_rate` remains excluded from tensors because it is target-derived
- current-year full regime signals remain diagnostic-only
- local candidates are evaluated separately before canonical inclusion
- tensor adjacency shapes are now valid

Still limited:

- rolling validation window is short: `2021-2024`
- REI historical years remain mostly unprocessed because XLSX conversion is pending
- Energy before 2018 remains pending
- no graph-temporal neural model has been accepted yet

## Decision

The project is methodologically consistent enough to commit the current data/baseline consolidation.

Do not proceed to STGNN before either:

- accepting the current baseline barrier as the benchmark to beat, or
- extending candidate data with a clearly defined new source and re-running the same causal protocol.
