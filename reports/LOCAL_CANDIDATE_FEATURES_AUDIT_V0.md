# Local Candidate Features Audit v0

Data: 2026-04-16

## Objective

Test whether local "heat" sources improve prediction beyond the current temporal baseline.

Sources tested:

- SITADEL non-residential construction surfaces
- SITADEL monthly non-residential construction surfaces
- REI CFE fiscal/economic base proxies
- SDES non-residential electricity/gas consumption

Lagged sources are used as `T-1` candidates. SITADEL monthly `Q1` and `H1` same-year variants are treated as nowcast candidates, not pure forecast features. None is included in the canonical tensor unless it improves the baseline or has a clear later role.

## Coverage

| Source | Years | Zones | Status |
| :--- | :--- | :---: | :--- |
| SITADEL | `2013-2024` | `306` | usable as lagged construction proxy |
| SITADEL monthly | `2013-2026` | `306` | usable for lagged and nowcast construction signals |
| Energy SDES | `2018-2024` | `306` | usable as lagged non-residential activity proxy |
| REI CFE | `2023-2024` | `287` | too shallow for current rolling validation |

REI has older files, but most are XLSX-only and require controlled conversion before use.

## Rolling WMAPE

Window: `2021-2024`

| Model | Mean WMAPE | Interpretation |
| :--- | :---: | :--- |
| `ridge_lag_only` | `7.66%` | best current linear baseline |
| `ridge_rei_only` | `7.66%` | identical because usable lag coverage is effectively limited |
| `persistence` | `7.68%` | practically tied |
| `ridge_sitadel_monthly_q1_nowcast_log` | `7.89%` | best SITADEL monthly variant, but nowcast and still worse than lag-only |
| `ridge_sitadel_monthly_lag_log` | `7.93%` | best forecast-safe monthly construction variant, still worse than lag-only |
| `ridge_sitadel_monthly_h1_nowcast_log` | `7.96%` | H1 nowcast does not add enough signal linearly |
| `ridge_sitadel_only` | `8.43%` | worse than temporal baseline |
| `ridge_sitadel_monthly_lag` | `8.45%` | raw levels underperform log transform |
| `ridge_sitadel_monthly_q1_nowcast` | `8.56%` | raw nowcast levels underperform log transform |
| `ridge_energy_only` | `8.66%` | worse than temporal baseline |
| `ridge_local_all` | `8.84%` | combining local candidates increases linear noise |
| `ridge_sitadel_monthly_h1_nowcast` | `9.11%` | worst monthly variant in raw level form |

## Decision

- Do not add SITADEL, REI, or Energy to the canonical forecast tensor yet.
- Keep them as candidate feature families for non-linear/ablation experiments.
- SITADEL monthly is useful enough to keep as an experimental family, especially with `log1p`, but it has not earned canonical status.
- Priority before using REI seriously: convert historical XLSX years and retest with deeper lag coverage.
- Priority before using Energy seriously: test transformed signals, especially year-over-year changes and sector-specific/non-residential categories.

## Methodological Reading

These sources are plausible local activity proxies, but they do not improve linear prediction in the tested forms. The monthly SITADEL result is informative: `log1p` compression improves the signal substantially, suggesting scale effects and non-linear interactions. The defensible claim is not "SITADEL is useless"; it is "SITADEL monthly is promising, but not yet stronger than the temporal baseline under a linear causal protocol."
