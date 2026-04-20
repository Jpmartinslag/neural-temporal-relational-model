# Forward-looking Signal Audit v1 (Robust)

## Methodology
- **Signals:** Multi-horizon national shocks projected via zone sectoral profile (FLORES A17).
- **Target:** Annual growth of SIDE business creations (local).
- **Demeaning:** Within-year correlation removes the national trend to see if the signal captures territorial variance.

## Summary Results

| Signal | Type | Correlation | N |
| :--- | :--- | :---: | :---: |
| regime_signal_jan_mar | Pooled | 0.7106 | 1960 |
| regime_signal_jan_jun | Pooled | 0.6433 | 1960 |
| regime_signal_jan_sep | Pooled | 0.6865 | 1960 |
| regime_signal_jan_dec | Pooled | 0.7037 | 1960 |
| regime_signal_lag_1 | Pooled | -0.2432 | 1680 |
| regime_signal_jan_mar | Within-Year (Demeaned) | 0.0094 | 1960 |
| regime_signal_jan_jun | Within-Year (Demeaned) | 0.0346 | 1960 |
| regime_signal_jan_sep | Within-Year (Demeaned) | 0.0185 | 1960 |
| regime_signal_jan_dec | Within-Year (Demeaned) | 0.0017 | 1960 |
| regime_signal_lag_1 | Within-Year (Demeaned) | 0.0285 | 1680 |

## Per-Year Detail

| Year | Signal | Correlation | N |
| :--- | :--- | :---: | :---: |
| 2018 | regime_signal_jan_dec | 0.2952 | 280 |
| 2018 | regime_signal_jan_jun | 0.2802 | 280 |
| 2018 | regime_signal_jan_mar | 0.2949 | 280 |
| 2018 | regime_signal_jan_sep | 0.2875 | 280 |
| 2019 | regime_signal_jan_dec | 0.0498 | 280 |
| 2019 | regime_signal_jan_jun | -0.0031 | 280 |
| 2019 | regime_signal_jan_mar | -0.0254 | 280 |
| 2019 | regime_signal_jan_sep | 0.0223 | 280 |
| 2019 | regime_signal_lag_1 | -0.0032 | 280 |
| 2020 | regime_signal_jan_dec | -0.1689 | 280 |
| 2020 | regime_signal_jan_jun | 0.0803 | 280 |
| 2020 | regime_signal_jan_mar | -0.0665 | 280 |
| 2020 | regime_signal_jan_sep | -0.1193 | 280 |
| 2020 | regime_signal_lag_1 | 0.0343 | 280 |
| 2021 | regime_signal_jan_dec | -0.1504 | 280 |
| 2021 | regime_signal_jan_jun | -0.0170 | 280 |
| 2021 | regime_signal_jan_mar | 0.0090 | 280 |
| 2021 | regime_signal_jan_sep | -0.1087 | 280 |
| 2021 | regime_signal_lag_1 | 0.0783 | 280 |
| 2022 | regime_signal_jan_dec | -0.0580 | 280 |
| 2022 | regime_signal_jan_jun | -0.0510 | 280 |
| 2022 | regime_signal_jan_mar | -0.0537 | 280 |
| 2022 | regime_signal_jan_sep | -0.0537 | 280 |
| 2022 | regime_signal_lag_1 | 0.0394 | 280 |
| 2023 | regime_signal_jan_dec | -0.1580 | 280 |
| 2023 | regime_signal_jan_jun | -0.1873 | 280 |
| 2023 | regime_signal_jan_mar | -0.1973 | 280 |
| 2023 | regime_signal_jan_sep | -0.1751 | 280 |
| 2023 | regime_signal_lag_1 | -0.0286 | 280 |
| 2024 | regime_signal_jan_dec | 0.1540 | 280 |
| 2024 | regime_signal_jan_jun | 0.1864 | 280 |
| 2024 | regime_signal_jan_mar | 0.1887 | 280 |
| 2024 | regime_signal_jan_sep | 0.1842 | 280 |
| 2024 | regime_signal_lag_1 | 0.0724 | 280 |

## Interpretation
- **National Trend Dominance:** High pooled correlation but low within-year correlation indicates the signal mostly captures the common national trend (the tide), not local specificities (the waves).