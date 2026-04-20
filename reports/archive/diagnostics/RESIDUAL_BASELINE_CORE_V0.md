# Residual Baseline Core v0

Data: 2026-04-17

## Objective

Test whether predicting corrections over persistence is more stable than predicting the full SIDE establishment-creation volume directly.

Current benchmark before this experiment:

| Model | Mean WMAPE |
| :--- | :---: |
| `ridge_lag_only` | `7.66%` |
| `persistence` | `7.68%` |
| `ridge_local_all` | `7.65%` |

## Method

The experiment predicts residual corrections over local persistence:

- Absolute residual: `y(t+1) - y(t)`
- Log residual: `log1p(y(t+1)) - log1p(y(t))`

Final prediction:

```text
prediction = persistence + lambda * residual_correction
```

Tested `lambda` values:

```text
0.0, 0.1, 0.25, 0.5, 0.75, 1.0
```

Models:

- `RidgeCV`
- `HuberRegressor`
- `ElasticNetCV`

Feature groups:

- `lag_only`
- `sitadel_only`
- `energy_only`
- `sitadel_energy`
- `local_all`
- `local_all_log`
- `engineered_target`
- `engineered_energy`
- `engineered_sitadel`
- `engineered_local`
- `engineered_all`
- `sitadel_monthly_lag_log`
- `sitadel_q1_nowcast_log` as nowcast diagnostic only

REI-backed groups are excluded from this candidate evaluation until publication-lag, vintage, and aggregation risks are resolved.

Scaling and imputation are fitted inside each train fold only.

## Best Fixed Result

Best fixed residual model by mean WMAPE:

| Model | Residual | Features | Lambda | Mean WMAPE | Max WMAPE |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `RidgeCV` | log | `engineered_target` | `0.5` | `6.62%` | `9.28%` |

Per-year WMAPE:

| Year | WMAPE |
| :---: | :---: |
| `2021` | `8.87%` |
| `2022` | `4.46%` |
| `2023` | `9.28%` |
| `2024` | `3.85%` |

This is the strongest fixed numerical result so far, but it is still treated as exploratory because the configuration is chosen after observing the full backtest table.

## Local-Source Ablation

Top fixed ablations:

| Rank | Model | Residual | Features | Lambda | Mean WMAPE | Max WMAPE |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| 1 | `RidgeCV` | log | `engineered_target` | `0.5` | `6.62%` | `9.28%` |
| 2 | `HuberRegressor` | log | `engineered_target` | `0.5` | `6.67%` | `9.48%` |
| 3 | `ElasticNetCV` | log | `engineered_target` | `0.5` | `6.71%` | `9.15%` |
| 4 | `ElasticNetCV` | log | `engineered_target` | `0.25` | `6.76%` | `11.54%` |
| 5 | `RidgeCV` | log | `engineered_target` | `0.25` | `6.85%` | `11.59%` |
| 6 | `RidgeCV` | absolute | `lag_only` | `0.5` | `6.90%` | `10.33%` |

Reading:

- The invalidated `REI` result was materially stronger than the no-REI results.
- Without `REI`, the best residual signal comes from target-history engineering, not from external local sources.
- SITADEL and energy do not currently justify promotion into a canonical residual baseline.

## Causal Selection

Naive causal selection failed:

| Selector | Mean WMAPE | Problem |
| :--- | :---: | :--- |
| naive prior-best selector | `12.21%` | selected an unstable `engineered_all` model after only one prior year |

Conservative causal selection:

- Use `ridge_level` lag-only until at least two prior test years exist.
- Then select the forecast-safe model/residual/lambda with best prior mean WMAPE.
- Exclude nowcast groups from selection.

Result:

| Year | Selected model | WMAPE |
| :---: | :--- | :---: |
| `2021` | `ridge_level / lag_only` | `6.51%` |
| `2022` | `ridge_level / lag_only` | `9.81%` |
| `2023` | `Ridge log / engineered_target / lambda=0.75` | `13.19%` |
| `2024` | `Huber absolute / lag_only / lambda=0.25` | `8.38%` |

Mean WMAPE:

```text
9.47%
```

## Decision

Residual modeling remains useful as an exploratory diagnostic, but the strong REI-backed result is not defensible yet.

Defensible claim:

```text
After excluding REI, a fixed residual correction can reduce mean WMAPE from about 7.66% to about 6.62% on the 2021-2024 rolling test window, but causal selection is unstable and degrades to about 9.47%.
```

Non-defensible claim:

```text
The final model is solved or STGNN is now required.
```

## Next Checks

- Compare residual models against older long-history baselines to ensure the improvement is not only a window artifact.
- Keep per-zone diagnostics updated for each promoted candidate.
- Keep REI banned from candidate baselines until timing/vintage and aggregation issues are resolved.
- Improve the activation/selection rule before promoting the residual model as operational.
- Keep `STGNN` postponed until residual baselines are fully audited.
