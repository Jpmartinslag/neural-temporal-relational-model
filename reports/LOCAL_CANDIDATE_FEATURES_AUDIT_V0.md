# Local Candidate Features Audit v0

Data: 2026-04-16

## Objective

Test whether local "heat" sources improve prediction beyond the current temporal baseline.

Sources tested:

- SITADEL non-residential construction surfaces
- SITADEL monthly non-residential construction surfaces
- REI CFE fiscal/economic base proxies
- SDES non-residential electricity/gas/heat-cold consumption

Lagged sources are used as `T-1` candidates. SITADEL monthly `Q1` and `H1` same-year variants are treated as nowcast candidates, not pure forecast features. None is included in the canonical tensor unless it improves the baseline or has a clear later role.

## Coverage

| Source | Years | Zones | Status |
| :--- | :--- | :---: | :--- |
| SITADEL | `2013-2024` | `306` | usable as lagged construction proxy |
| SITADEL monthly | `2013-2026` | `306` | usable for lagged and nowcast construction signals |
| Energy SDES | `2008-2024` | `306` | historical electricity/gas/heat-cold integrated; early years sparse |
| REI CFE | `2018-2024` | `306` | quarantine: timing/vintage risk and 2024 aggregate/component bug fixed in code |

REI `2018-2022` was converted from XLSX to intermediate CSV with `python-calamine`, then aggregated to ZE2020. The converted CSVs are local reproducible intermediates and are not canonical artifacts.

REI is currently under methodological quarantine for candidate baselines. The extraction code was corrected to avoid double-counting 2024 EPCI aggregate columns (`P31`, `P33`, `P34`) with their subcomponents, but publication-lag and vintage safety remain unresolved.

## Rolling WMAPE

Window: `2021-2024`

| Model | Mean WMAPE | Interpretation |
| :--- | :---: | :--- |
| `ridge_local_all` | `7.65%` | first candidate combination marginally below lag-only, but unstable by year |
| `ridge_lag_only` | `7.66%` | best current simple linear baseline |
| `persistence` | `7.68%` | practically tied |
| `ridge_rei_only` | `7.77%` | REI helps some years but does not beat lag-only on average |
| `ridge_sitadel_monthly_q1_nowcast_log` | `7.89%` | best SITADEL monthly variant, but nowcast and still worse than lag-only |
| `ridge_sitadel_monthly_lag_log` | `7.93%` | best forecast-safe monthly construction variant, still worse than lag-only |
| `ridge_sitadel_monthly_h1_nowcast_log` | `7.96%` | H1 nowcast does not add enough signal linearly |
| `ridge_engineered_sitadel` | `7.97%` | rolling/volatility construction features improve raw SITADEL, but not enough |
| `ridge_energy_log` | `7.99%` | transformed energy improves raw energy slightly but still below lag-only |
| `ridge_energy_only` | `8.01%` | deeper energy helps but is not sufficient alone |
| `ridge_engineered_energy` | `8.04%` | log-diff/share/volatility energy features remain below lag-only |
| `ridge_sitadel_only` | `8.43%` | worse than temporal baseline |
| `ridge_sitadel_monthly_lag` | `8.45%` | raw levels underperform log transform |
| `ridge_sitadel_monthly_q1_nowcast` | `8.56%` | raw nowcast levels underperform log transform |
| `ridge_engineered_target` | `8.77%` | autoregressive momentum features are unstable in Ridge |
| `ridge_local_all_log` | `8.84%` | log-transforming all local families increases linear noise |
| `ridge_rei_log` | `9.05%` | log REI transform is unstable |
| `ridge_sitadel_monthly_h1_nowcast` | `9.11%` | worst monthly variant in raw level form |
| `ridge_engineered_local` | `15.04%` | combined engineered local set is unstable |
| `ridge_engineered_rei` | `15.35%` | REI log-diff/volatility features are unstable |
| `ridge_engineered_all` | `16.89%` | engineered full set overfits/overreacts linearly |

## Decision

- Do not add SITADEL, REI, or Energy to the canonical forecast tensor yet.
- Keep them as candidate feature families for non-linear/ablation experiments.
- SITADEL monthly is useful enough to keep as an experimental family, especially with `log1p`, but it has not earned canonical status.
- REI historical coverage is sufficient for diagnostic testing, but it is temporarily banned from candidate residual baselines until publication-lag and vintage safety are resolved.
- Energy historical coverage is now sufficient for testing; it improves the combined local model but not as a standalone linear predictor.
- Engineered forecast-safe transformations were tested: target momentum, energy log-diff/share/volatility, REI log-diff/volatility, and SITADEL rolling/volatility.
- The engineered transformations did not improve the current best result; the best engineered family is SITADEL at `7.97%`.
- Next methodological step: test stability-oriented local models instead of immediately promoting `ridge_local_all`.
- A strict causal model-selection check fails (`10.44%` WMAPE), so the current local gain cannot yet be chosen reliably from past validation years alone.

## Methodological Reading

These sources are plausible local activity proxies. After extending Energy to `2008-2024`, the combined raw local model becomes marginally better than `ridge_lag_only` on mean WMAPE (`7.646%` vs `7.664%`), but this reading included REI before the quarantine decision. The first engineered feature pass did not solve the instability; most engineered families underperform, especially REI log-diff features. A causal selector using only prior test years chooses poorly (`10.44%` WMAPE), confirming that the gain is not operationally stable yet. The defensible claim is: local sources may contain regime-sensitive information, but REI must not be used for candidate model promotion until its timing and vintage risks are resolved.
